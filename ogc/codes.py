"""Códigos de canje de juegos gacha de HoYoverse (Genshin Impact, Honkai: Star Rail y Zenless Zone Zero).

Se consultan dos API públicas y gratuitas que recopilan los códigos oficiales. Un código solo se muestra
como activo si alguna fuente que respondió lo da por activo y ninguna lo da por vencido. Si ninguna fuente
responde, se conserva la última lista válida. Los códigos nuevos se anuncian una sola vez en Telegram y Discord.
"""

import html
import os
import re
import sys
import urllib.parse
import urllib.request

from .model import iso, parse_iso

GAMES = {
    "genshin": {"name": "Genshin Impact", "page": "codigos-genshin-impact.html", "seria": "genshin", "ennead": "genshin",
                "redeem": "https://genshin.hoyoverse.com/es/gift?code={code}", "currency": "Protogemas",
                "steps": ["Llega al Rango de Aventura 10 en tu cuenta.",
                          "Toca el botón «Canjear»: se abre la página oficial de HoYoverse con el código ya puesto.",
                          "Inicia sesión con tu cuenta, elige tu servidor (América) y tu personaje, y confirma.",
                          "Las recompensas te llegan al correo dentro del juego en unos minutos."],
                "ingame": "Dentro del juego: Paimon (menú) → Configuración → Cuenta → Canjear código."},
    "starrail": {"name": "Honkai: Star Rail", "page": "codigos-honkai-star-rail.html", "seria": "hkrpg", "ennead": "starrail",
                 "redeem": "https://hsr.hoyoverse.com/gift?code={code}", "currency": "Jade Estelar",
                 "steps": ["Completa la misión del tutorial (nivel de Trazacaminos 4 o más).",
                           "Toca «Canjear»: se abre la página oficial de HoYoverse con el código ya puesto.",
                           "Inicia sesión, elige el servidor América y tu personaje, y confirma.",
                           "Las recompensas llegan al correo dentro del juego."],
                 "ingame": "Dentro del juego: menú del teléfono → los tres puntos (…) → Canjear código."},
    "zenless": {"name": "Zenless Zone Zero", "page": "codigos-zenless-zone-zero.html", "seria": "nap", "ennead": "zenless",
                "redeem": "https://zenless.hoyoverse.com/redemption?code={code}", "currency": "Policromos",
                "steps": ["Completa el prólogo del juego.",
                          "Toca «Canjear»: se abre la página oficial de HoYoverse con el código ya puesto.",
                          "Inicia sesión, elige el servidor América y tu agente, y confirma.",
                          "Las recompensas llegan al correo dentro del juego."],
                "ingame": "Dentro del juego: menú → Más → Canjear código."},
}
SERIA_URL = "https://hoyo-codes.seria.moe/codes?game={game}"
ENNEAD_URL = "https://api.ennead.cc/mihoyo/{game}/codes"
# Ícono oficial de cada juego, tomado de su ficha en la App Store (API pública de Apple, sin clave)
ITUNES_URL = "https://itunes.apple.com/search?entity=software&country=co&limit=10&term={term}"
CODE_RE = re.compile(r"^[A-Z0-9]{6,20}$")
NEW_HOURS = 48
KEEP_EXPIRED = 40
MAX_ANNOUNCE = 4  # por ejecución, para no llenar los canales

# Nombres de recompensas comunes en español (como aparecen en la versión en español de los juegos)
REWARDS_ES = [
    ("Primogems", "Protogemas"), ("Primogem", "Protogemas"), ("Hero's Wit", "Experiencia de héroe"),
    ("Mora", "Mora"), ("Mystic Enhancement Ore", "Mineral de refinamiento místico"), ("Fine Enhancement Ore", "Mineral de refinamiento fino"),
    ("Adventurer's Experience", "Experiencia de aventurero"), ("Stellar Jade", "Jade Estelar"), ("Credits", "Créditos"),
    ("Credit", "Créditos"), ("Traveler's Guide", "Guía del viajero"), ("Adventure Log", "Diario de aventuras"),
    ("Refined Aether", "Éter refinado"), ("Lost Crystal", "Cristal perdido"), ("Condensed Aether", "Éter condensado"),
    ("Polychrome", "Policromos"), ("Dennies", "Dinis"), ("Denny", "Dinis"), ("Official Investigator Log", "Registro de investigador oficial"),
    ("Senior Investigator Log", "Registro de investigador sénior"), ("W-Engine Energy Module", "Módulo de energía de amplificador"),
    ("Bangboo Algorithm Module", "Módulo de algoritmo de Bangbú"), ("Bangboo System Widget", "Accesorio de sistema de Bangbú"),
]


def get_json_default(url):
    from .sources import get_json
    return get_json(url)


NUMBERS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}


def translate(reward):
    text = re.sub(r"^(?:and|y)\s+", "", reward.strip(), flags=re.I)
    text = re.sub(r"\b(" + "|".join(NUMBERS) + r")\b", lambda m: NUMBERS[m.group(1).lower()], text, flags=re.I)
    for en, es in REWARDS_ES:
        pattern = re.escape(en).replace("'", "['’]")
        text = re.sub(rf"\b{pattern}(?:e?s)?\b", es, text, flags=re.I)
    text = re.sub(r"\s*[×x*]\s*(\d[\d,.]*k?)\b", r" ×\1", text)
    text = re.sub(r"^(\d[\d,.]*k?)\s+(.+)$", r"\2 ×\1", text)  # "40 Protogemas" -> "Protogemas ×40"
    return text[:1].upper() + text[1:]


def rewards_list(value):
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = re.split(r"\s*(?:,|;|\n)\s*(?=[^\d])", value)
    else:
        items = []
    return [translate(str(x)) for x in items if str(x).strip()][:8]


def clean(code):
    code = str(code or "").strip().upper()
    return code if CODE_RE.match(code) else None


def from_seria(data):
    """{'codes': [{'code', 'rewards', 'status'}]}: la API solo lista los que revisó; status OK = activo."""
    active, expired = {}, set()
    for row in (data or {}).get("codes", []) if isinstance(data, dict) else []:
        code = clean(row.get("code"))
        if not code:
            continue
        if str(row.get("status", "OK")).upper() in ("OK", "ACTIVE"):
            active[code] = rewards_list(row.get("rewards"))
        else:
            expired.add(code)
    return active, expired


def from_ennead(data):
    """{'active': [{'code', 'rewards': [...]}], 'inactive': [...]}"""
    active, expired = {}, set()
    if not isinstance(data, dict):
        return active, expired
    for row in data.get("active") or []:
        code = clean(row.get("code"))
        if code:
            active[code] = rewards_list(row.get("rewards"))
    for row in data.get("inactive") or []:
        code = clean(row.get("code"))
        if code:
            expired.add(code)
    return active, expired


def artwork(gid, fetch):
    """URL HTTPS del ícono oficial del juego en la App Store, o None."""
    name = GAMES[gid]["name"]
    data = fetch(ITUNES_URL.format(term=urllib.parse.quote(name)))
    for row in (data or {}).get("results", []) if isinstance(data, dict) else []:
        seller = (row.get("sellerName") or row.get("artistName") or "").upper()
        title = (row.get("trackName") or "").lower()
        url = row.get("artworkUrl512") or ""
        if ("COGNOSPHERE" in seller or "HOYOVERSE" in seller) and title.startswith(name.lower()) and url.startswith("https://"):
            return url
    return None


def update(previous, now, fetch=get_json_default):
    """Devuelve (estado nuevo, códigos nuevos [(juego, código)], texto de estado)."""
    state = {"updatedAt": iso(now), "games": {}}
    fresh, report = [], []
    for gid, g in GAMES.items():
        old = (previous.get("games") or {}).get(gid) or {}
        codes = {k: dict(v) for k, v in (old.get("codes") or {}).items()}
        active, expired, worked = {}, set(), []
        for name, url, parse in (("seria", SERIA_URL.format(game=g["seria"]), from_seria),
                                 ("ennead", ENNEAD_URL.format(game=g["ennead"]), from_ennead)):
            try:
                a, x = parse(fetch(url))
            except Exception as exc:
                print(f"Códigos {g['name']}: la fuente {name} falló ({type(exc).__name__})", file=sys.stderr)
                continue
            worked.append(name)
            for code, rewards in a.items():
                if code not in active or len(rewards) > len(active[code]):
                    active[code] = rewards
            expired |= x
        if not worked:
            state["games"][gid] = old
            report.append(f"{g['name']}: sin respuesta, se conserva la lista anterior")
            continue
        seeded = bool(old.get("lastOk"))
        for code, rewards in active.items():
            if code in expired:
                continue
            item = codes.setdefault(code, {"firstSeen": iso(now)})
            if item.get("status") != "activo" and seeded and not item.get("announced"):
                fresh.append((gid, code))
            item.update(status="activo", lastSeen=iso(now), rewards=rewards or item.get("rewards", []))
            item.pop("expiredAt", None)
        for code, item in codes.items():
            # Si una fuente falló, que el código no aparezca en la otra no basta para darlo por vencido
            if item.get("status") == "activo" and (code in expired or (code not in active and len(worked) == 2)):
                item.update(status="vencido", expiredAt=iso(now))
        for code in expired - set(codes):
            codes[code] = {"status": "vencido", "rewards": [], "expiredAt": None}
        live = {k: v for k, v in codes.items() if v.get("status") == "activo"}
        gone = sorted((kv for kv in codes.items() if kv[1].get("status") != "activo"),
                      key=lambda kv: kv[1].get("expiredAt") or "", reverse=True)[:KEEP_EXPIRED]
        image = old.get("image")
        if not image:
            try:
                image = artwork(gid, fetch)
            except Exception as exc:
                print(f"Códigos {g['name']}: no se pudo traer la imagen ({type(exc).__name__})", file=sys.stderr)
        state["games"][gid] = {"lastOk": iso(now), "sources": worked, "image": image, "codes": dict(sorted(live.items()) + gone)}
        report.append(f"{g['name']}: {len(live)} activos ({'+'.join(worked)})")
    return state, fresh[:MAX_ANNOUNCE], "; ".join(report)


def active_codes(state, gid):
    codes = ((state.get("games") or {}).get(gid) or {}).get("codes") or {}
    rows = [dict(v, code=k) for k, v in codes.items() if v.get("status") == "activo"]
    return sorted(rows, key=lambda r: r.get("firstSeen") or "", reverse=True)


def expired_codes(state, gid):
    codes = ((state.get("games") or {}).get(gid) or {}).get("codes") or {}
    return [dict(v, code=k) for k, v in codes.items() if v.get("status") != "activo"]


def is_new(item, now):
    seen = parse_iso(item.get("firstSeen"))
    return bool(seen and (now - seen).total_seconds() < NEW_HOURS * 3600)


def announce_text(gid, item, link):
    g, e = GAMES[gid], html.escape
    lines = [f"🎟️ <b>Nuevo código de {e(g['name'])}</b>", "", f"<code>{e(item['code'])}</code>"]
    if item.get("rewards"):
        lines.append("🎁 " + e(", ".join(item["rewards"])))
    lines += [f'👉 <a href="{e(g["redeem"].format(code=item["code"]))}">Canjear en la página oficial</a>',
              f'📋 Todos los códigos: <a href="{e(link)}">{e(link)}</a>', "<i>Úsalo pronto: los códigos vencen sin aviso.</i>"]
    return "\n".join(lines)


def send_telegram(text, token=None, chat=None):
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = chat or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", method="POST",
                                 data=urllib.parse.urlencode({"chat_id": chat, "text": text, "parse_mode": "HTML",
                                                              "disable_web_page_preview": "true"}).encode())
    try:
        urllib.request.urlopen(req, timeout=30).read()
        return True
    except Exception as exc:  # nunca imprimir la URL: lleva el token
        print(f"Telegram falló con un código: {type(exc).__name__}", file=sys.stderr)
        return False


def discord_payload(gid, item, link, image=None):
    g = GAMES[gid]
    lines = [f"`{item['code']}`"]
    if item.get("rewards"):
        lines.append("🎁 " + ", ".join(item["rewards"]))
    lines += [f"[Canjear en la página oficial]({g['redeem'].format(code=item['code'])}) · [Todos los códigos]({link})"]
    return {"embeds": [{"title": f"🎟️ Nuevo código de {g['name']}"[:250], "url": link, "description": "\n".join(lines)[:2000],
                        "color": 0xFFC83D, "footer": {"text": "Los códigos vencen sin aviso"}}
                       | ({"thumbnail": {"url": image}} if (image or "").startswith("https://") else {})]}


def announce(state, fresh, base, dc=None, send=send_telegram):
    """Publica cada código nuevo una vez. Devuelve cuántos salieron."""
    sent = 0
    for gid, code in fresh:
        item = state["games"][gid]["codes"].get(code)
        if not item or item.get("announced"):
            continue
        link = base + GAMES[gid]["page"]
        ok = send(announce_text(gid, dict(item, code=code), link))
        if dc is not None and dc.ready:
            ok = dc.post_raw("gratis", discord_payload(gid, dict(item, code=code), link, state["games"][gid].get("image"))) or ok
        if ok:
            item["announced"] = True
            sent += 1
    return sent
