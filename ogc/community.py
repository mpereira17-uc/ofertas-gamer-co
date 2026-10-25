"""Comunidad automática: resumen diario en Telegram, encuesta semanal (Telegram y Discord) y su resultado.

Todo sale por las API oficiales. El resumen usa solo datos reales del día; la encuesta pregunta
por juegos que de verdad están gratis o en oferta esa semana.
"""

import html
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid

from .channels import CO_TZ, price_line

DAILY_FROM_HOUR = 7  # desde las 7 a. m. (hora Colombia)


def daily_due(now, state):
    co = now.astimezone(CO_TZ)
    return co.hour >= DAILY_FROM_HOUR and state.get("sentDate") != co.strftime("%Y-%m-%d")


def daily_text(dotd, free, today_games, link):
    e = html.escape
    lines = ["☀️ <b>Buenos días, gamers</b>", ""]
    if dotd:
        lines += [f"⭐ <b>Oferta del día:</b> {e(dotd['title'])} · -{dotd.get('discountPercentage') or 0}% · {e(price_line(dotd))}", ""]
    if free:
        lines.append("🎁 <b>Gratis ahora:</b> " + ", ".join(e(o["title"]) for o in free[:5]))
    if today_games:
        lines.append("📅 <b>Sale hoy:</b> " + ", ".join(e(g["title"]) for g in today_games[:5]))
    lines += ["", f'Todo aquí: <a href="{e(link)}">{e(link)}</a>', "<i>Confirma el precio en la tienda antes de comprar.</i>"]
    return "\n".join(lines)[:1000]


def _post(method, fields, files=None, token=None):
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in fields.items():
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, (name, data, mime) in files.items():
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\n'
                     f"Content-Type: {mime}\r\n\r\n").encode() + data + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    else:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read() or b"{}")


def send_daily(text, image_bytes=None, image_url=""):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        if image_bytes:
            _post("sendPhoto", {"chat_id": chat, "caption": text, "parse_mode": "HTML"}, {"photo": ("oferta.jpg", image_bytes, "image/jpeg")})
        elif image_url:
            _post("sendPhoto", {"chat_id": chat, "photo": image_url, "caption": text, "parse_mode": "HTML"})
        else:
            _post("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML"})
        return True
    except Exception as exc:  # nunca imprimir la URL: lleva el token
        print(f"Telegram falló con el resumen diario: {type(exc).__name__}", file=sys.stderr)
        return False


def poll_options(snap):
    names = []
    for item in snap.get("free", []) + snap.get("deals", []) + snap.get("games", []):
        t = item["title"][:90]
        if t not in names:
            names.append(t)
        if len(names) == 4:
            break
    return names + ["Otro / ninguno"] if len(names) >= 2 else []


QUESTION = "🎮 ¿Cuál vas a jugar este fin de semana?"


def send_poll(snap, dc=None):
    """Encuesta en el canal de Telegram (anónima) y en Discord. Devuelve {"telegram": poll_id, "discord": bool}."""
    options = poll_options(snap)
    out = {"question": QUESTION, "options": options, "week": snap["week"]}
    if not options:
        return out
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat:
        try:
            res = _post("sendPoll", {"chat_id": chat, "question": QUESTION, "options": json.dumps(options, ensure_ascii=False),
                                     "is_anonymous": "true"})
            out["telegram"] = ((res.get("result") or {}).get("poll") or {}).get("id")
        except Exception as exc:
            print(f"Telegram falló con la encuesta: {type(exc).__name__}", file=sys.stderr)
    if dc is not None and dc.ready:
        out["discord"] = dc.post_raw("ofertas", {"poll": {"question": {"text": QUESTION[:300]},
                                                          "answers": [{"poll_media": {"text": o[:55]}} for o in options],
                                                          "duration": 72, "allow_multiselect": False}})
    return out


def apply_poll_update(state, poll):
    """Guarda los votos que Telegram manda cuando cambia una encuesta del bot."""
    if state.get("telegram") and poll.get("id") == state["telegram"]:
        state["votes"] = {o.get("text", ""): o.get("voter_count", 0) for o in poll.get("options") or []}
        state["total"] = poll.get("total_voter_count", 0)
        state["closed"] = bool(poll.get("is_closed"))
    return state
