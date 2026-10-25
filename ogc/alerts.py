"""Alertas personales por Telegram: "avísame cuando X baje de $Y" y "avísame cuando salga X".

Cómo funciona (sin servidor): en cada ejecución (cada 4 horas) el bot lee los mensajes privados que le
escribieron con la API oficial (getUpdates), responde, y revisa si alguna oferta o estreno cumple una alerta.

Privacidad: el repositorio es público, así que las suscripciones (que llevan el número de chat de cada
persona) se guardan CIFRADAS en data/alertas.enc con una clave derivada del secreto TELEGRAM_BOT_TOKEN.
Sin ese secreto nadie puede leerlas. No se guardan nombres ni usuarios. Nunca se imprime nada de eso.
"""

import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sys
import unicodedata
import urllib.parse
import urllib.request

from .channels import CO_TZ, price_line

API = "https://api.telegram.org/bot{token}/{method}"
MAX_PER_CHAT = 10
MAX_SENDS = 120  # avisos por ejecución, para no saturar
HELP = ("🎮 <b>Alertas de Ofertas Gamer CO</b>\n\n"
        "• <code>/alerta elden ring</code>: te aviso cuando haya una oferta de ese juego.\n"
        "• <code>/alerta elden ring 50000</code>: solo si cuesta menos de $50.000 COP.\n"
        "• <code>/estreno gta vi</code>: te aviso el día que salga.\n"
        "• <code>/misalertas</code>: ver tus alertas.\n"
        "• <code>/borrar 2</code> o <code>/borrar todo</code>: quitar alertas.\n\n"
        "Reviso cada 4 horas, así que la respuesta puede tardar un poco. Máximo 10 alertas por persona.")


# ---------- cifrado (HMAC-SHA256 en modo contador + etiqueta de autenticidad) ----------
def _keys(secret):
    base = hmac.new(secret.encode(), b"ogc-alertas-v1", hashlib.sha256).digest()
    return (hmac.new(base, b"cifrar", hashlib.sha256).digest(), hmac.new(base, b"autenticar", hashlib.sha256).digest())


def _stream(key, nonce, size):
    out, counter = b"", 0
    while len(out) < size:
        out += hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        counter += 1
    return out[:size]


def encrypt(data, secret):
    enc, mac = _keys(secret)
    nonce = secrets.token_bytes(16)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    body = bytes(a ^ b for a, b in zip(raw, _stream(enc, nonce, len(raw))))
    tag = hmac.new(mac, nonce + body, hashlib.sha256).digest()
    return base64.b64encode(nonce + body + tag).decode()


def decrypt(text, secret):
    enc, mac = _keys(secret)
    blob = base64.b64decode(text)
    nonce, body, tag = blob[:16], blob[16:-32], blob[-32:]
    if not hmac.compare_digest(tag, hmac.new(mac, nonce + body, hashlib.sha256).digest()):
        raise ValueError("archivo de alertas alterado o clave distinta")
    return json.loads(bytes(a ^ b for a, b in zip(body, _stream(enc, nonce, len(body)))))


# ---------- texto ----------
def norm(text):
    text = unicodedata.normalize("NFKD", (text or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def matches(query, title):
    words, name = norm(query).split(), set(norm(title).split())
    return bool(words) and all(w in name for w in words)  # palabras completas: "ring" no coincide con "Ringo"


def parse_alert(arg):
    """'elden ring 50.000' -> ('elden ring', 50000). El precio al final es opcional."""
    m = re.match(r"^(.*?)(?:\s+\$?\s*([\d.]{3,}))?\s*$", arg.strip())
    query = (m.group(1) if m else arg).strip()[:60]
    price = int(m.group(2).replace(".", "")) if m and m.group(2) else None
    return query, price


def cop(offer):
    if offer.get("currentPrice") == 0:
        return 0
    return offer.get("copApproximation") if offer.get("currency") == "USD" else offer.get("currentPrice")


# ---------- Telegram ----------
def call(token, method, payload, opener=urllib.request.urlopen):
    req = urllib.request.Request(API.format(token=token, method=method), data=urllib.parse.urlencode(payload).encode(), method="POST")
    with opener(req, timeout=40) as resp:
        return json.loads(resp.read())


class Alerts:
    def __init__(self, store, token, offers, games, link_for, now, api=None):
        self.store, self.token = store, token  # store = {"offset": int, "subs": {chat_id: [alerta, ...]}}
        self.offers, self.games, self.link_for, self.now = offers, games, link_for, now
        self.api = api or (lambda method, payload: call(token, method, payload))
        self.sent = 0
        self.on_poll = None

    def say(self, chat, text):
        if self.sent >= MAX_SENDS:
            return False
        try:
            self.api("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "false"})
            self.sent += 1
            return True
        except Exception as exc:  # sin el número de chat en el registro
            print(f"Alertas: no se pudo enviar un mensaje ({type(exc).__name__})", file=sys.stderr)
            return False

    # -- comandos --
    def handle(self, chat, text):
        subs = self.store["subs"].setdefault(str(chat), [])
        cmd, _, arg = text.strip().partition(" ")
        cmd = cmd.split("@")[0].lower()
        if cmd == "/start" and arg.startswith(("o_", "j_")):
            return self.deep_link(chat, subs, arg)
        if cmd in ("/start", "/ayuda", "/help"):
            return self.say(chat, HELP)
        if cmd in ("/alerta", "/estreno"):
            if len(subs) >= MAX_PER_CHAT:
                return self.say(chat, "Ya tienes 10 alertas. Borra alguna con /borrar.")
            query, price = parse_alert(arg) if cmd == "/alerta" else (arg.strip()[:60], None)
            if len(norm(query)) < 2:
                return self.say(chat, "Escribe el nombre del juego. Ejemplo: <code>/alerta hollow knight 20000</code>")
            kind = "oferta" if cmd == "/alerta" else "estreno"
            subs.append({"tipo": kind, "q": query, "max": price, "avisados": []})
            extra = f" por menos de ${price:,.0f} COP".replace(",", ".") if price else ""
            what = f"una oferta de <b>{html.escape(query)}</b>{extra}" if kind == "oferta" else f"el estreno de <b>{html.escape(query)}</b>"
            return self.say(chat, f"✅ Listo: te aviso cuando haya {what}.")
        if cmd == "/misalertas":
            if not subs:
                return self.say(chat, "No tienes alertas. Crea una con <code>/alerta nombre del juego</code>.")
            lines = [f"{i}. {'🔔 Oferta' if s['tipo'] == 'oferta' else '📅 Estreno'}: {html.escape(s['q'])}"
                     + (f" (menos de ${s['max']:,.0f})".replace(",", ".") if s.get("max") else "") for i, s in enumerate(subs, 1)]
            return self.say(chat, "<b>Tus alertas</b>\n" + "\n".join(lines))
        if cmd == "/borrar":
            if arg.strip().lower() == "todo":
                subs.clear()
                return self.say(chat, "Borré todas tus alertas.")
            if arg.strip().isdigit() and 1 <= int(arg) <= len(subs):
                gone = subs.pop(int(arg) - 1)
                return self.say(chat, f"Borré la alerta de {html.escape(gone['q'])}.")
            return self.say(chat, "Escribe el número de la alerta. Míralo con /misalertas.")
        return self.say(chat, HELP)

    def deep_link(self, chat, subs, arg):
        """Botón "Avísame" de la página: /start o_<id> (oferta) o j_<id> (estreno)."""
        kind, _, ref = arg.partition("_")
        pool = self.offers if kind == "o" else self.games
        item = next((x for x in pool if short_id(x["id"]) == ref), None)
        if not item:
            return self.say(chat, "No encontré ese juego. " + HELP)
        if len(subs) >= MAX_PER_CHAT:
            return self.say(chat, "Ya tienes 10 alertas. Borra alguna con /borrar.")
        sub = {"tipo": "oferta" if kind == "o" else "estreno", "q": item["title"][:60], "max": None,
               "avisados": [item["id"]] if kind == "o" else []}  # de la oferta actual ya sabe: se avisa de las siguientes
        subs.append(sub)
        msg = (f"✅ Listo: te aviso cuando <b>{html.escape(item['title'])}</b> tenga una nueva oferta." if kind == "o"
               else f"✅ Listo: te aviso el día que salga <b>{html.escape(item['title'])}</b>.")
        return self.say(chat, msg + "\n\nEscribe /ayuda para más opciones.")

    def read_messages(self):
        try:
            data = self.api("getUpdates", {"offset": self.store.get("offset", 0), "timeout": 0, "allowed_updates": '["message","poll"]'})
        except Exception as exc:
            print(f"Alertas: no se pudieron leer mensajes ({type(exc).__name__})", file=sys.stderr)
            return 0
        count = 0
        for up in data.get("result") or []:
            self.store["offset"] = max(self.store.get("offset", 0), up["update_id"] + 1)
            if up.get("poll") and self.on_poll:
                self.on_poll(up["poll"])
            msg = up.get("message") or {}
            chat = msg.get("chat") or {}
            if chat.get("type") == "private" and (msg.get("text") or "").startswith("/"):
                self.handle(chat["id"], msg["text"][:200])
                count += 1
        return count

    # -- avisos --
    def check(self):
        today = self.now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        notified = 0
        for chat, subs in self.store["subs"].items():
            for sub in subs:
                if sub["tipo"] == "oferta":
                    hits = [o for o in self.offers if o["id"] not in sub["avisados"] and matches(sub["q"], o["title"])
                            and (sub.get("max") is None or (cop(o) is not None and cop(o) <= sub["max"]))]
                    for o in hits[:3]:
                        head = "🎁 ¡Está GRATIS!" if o.get("currentPrice") == 0 else f"🔥 Bajó de precio: -{o.get('discountPercentage') or 0}%"
                        text = (f"🔔 <b>Tu alerta: {html.escape(sub['q'])}</b>\n{head}\n<b>{html.escape(o['title'])}</b> en {html.escape(o['store'])}\n"
                                f"{html.escape(price_line(o))}\n{html.escape(self.link_for(o))}")
                        if self.say(int(chat), text):
                            sub["avisados"] = (sub["avisados"] + [o["id"]])[-50:]
                            notified += 1
                else:
                    for g in self.games:
                        if g["id"] in sub["avisados"] or g.get("precision") != "day" or g.get("date") != today or not matches(sub["q"], g["title"]):
                            continue
                        text = (f"📅 <b>¡Hoy sale {html.escape(g['title'])}!</b>\nTu alerta de estreno: {html.escape(sub['q'])}\n"
                                f"{html.escape(self.link_for(g) or g['url'])}")
                        if self.say(int(chat), text):
                            sub["avisados"] = (sub["avisados"] + [g["id"]])[-50:]
                            notified += 1
        self.store["subs"] = {c: s for c, s in self.store["subs"].items() if s}
        return notified


def short_id(item_id):
    """Id corto y estable para el enlace t.me/bot?start=... (Telegram permite 64 caracteres)."""
    return hashlib.sha256(item_id.encode()).hexdigest()[:12]


def run(path, offers, games, link_for, now, env=os.environ, api=None, on_poll=None):
    """Lee comandos, avisa y guarda. Devuelve un texto de estado (sin datos personales)."""
    token = (env.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        return "no configurado"
    try:
        store = {"offset": 0, "subs": {}}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                store = decrypt(fh.read().strip(), token)
    except Exception as exc:
        print(f"Alertas: no se pudo abrir el archivo ({type(exc).__name__}); se empieza de cero", file=sys.stderr)
        store = {"offset": 0, "subs": {}}
    al = Alerts(store, token, offers, games, link_for, now, api)
    al.on_poll = on_poll
    commands = al.read_messages()
    notified = al.check()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(encrypt(store, token) + "\n")
    people = len(store["subs"])
    return f"{commands} mensajes atendidos, {notified} avisos enviados, {people} personas con alertas"


def bot_username(env=os.environ, api=None):
    token = (env.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        return ""
    try:
        return ((api or (lambda m, p: call(token, m, p)))("getMe", {}).get("result") or {}).get("username") or ""
    except Exception as exc:
        print(f"Alertas: getMe falló ({type(exc).__name__})", file=sys.stderr)
        return ""
