"""Arma el servidor de Discord de Ofertas Gamer CO con la API oficial de bots.

Solo crea lo que falta (categorías, canales y mensajes fijos): no borra ni renombra nada,
así que se puede ejecutar varias veces sin dañar el servidor.

Necesita el secreto DISCORD_BOT_TOKEN y la variable DISCORD_GUILD_ID (el número del servidor).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://discord.com/api/v10"
SITE = "https://ofertas-gamer-co.pages.dev/"
TELEGRAM = "https://t.me/ofertasgamerco"
SEND_MESSAGES = 1 << 11
ADD_REACTIONS = 1 << 6
GREEN, PURPLE = 0x22C55E, 0x7C3AED

# (categoría, [(tipo, nombre, tema, solo_lectura)])
LAYOUT = [
    ("📌 INFORMACIÓN", [
        ("text", "👋・bienvenida", "Empieza aquí: qué es Ofertas Gamer CO y cómo usar el servidor.", True),
        ("text", "📜・reglas", "Reglas de la comunidad.", True),
        ("text", "📢・anuncios", "Novedades del canal y de la página.", True),
    ]),
    ("🎮 OFERTAS", [
        ("text", "🔥・ofertas", f"Ofertas verificadas publicadas automáticamente cada 4 horas. Todas en {SITE}", True),
        ("text", "🎁・juegos-gratis", "Juegos gratis por tiempo limitado.", True),
        ("text", "📅・lanzamientos", f"Próximos lanzamientos. Calendario completo: {SITE}lanzamientos.html", True),
    ]),
    ("💬 COMUNIDAD", [
        ("text", "💬・chat-general", "Habla de juegos con la comunidad.", False),
        ("text", "🕹️・recomendaciones", "¿Qué estás jugando? Recomienda juegos.", False),
        ("text", "📸・capturas", "Comparte capturas y clips de tus partidas.", False),
        ("text", "💡・sugerencias", "Ideas para mejorar el canal y la página.", False),
        ("voice", "🔊 Jugando juntos", "", False),
        ("voice", "🎧 Sala de espera", "", False),
    ]),
]

MESSAGES = {
    "👋・bienvenida": {
        "title": "🎮 ¡Bienvenido a Ofertas Gamer CO!",
        "color": GREEN,
        "description": (
            "Aquí encuentras **ofertas verificadas de videojuegos** para Colombia, juegos gratis y próximos lanzamientos.\n\n"
            "**Cómo usar el servidor**\n"
            "🔥 <#ofertas> ofertas nuevas cada 4 horas, automáticas\n"
            "🎁 <#juegos-gratis> juegos gratis por tiempo limitado\n"
            "📅 <#lanzamientos> lo que viene\n"
            "💬 <#chat-general> para hablar con la comunidad\n\n"
            f"🌐 **Página:** {SITE}\n"
            f"📲 **Telegram:** {TELEGRAM}\n\n"
            "Los precios pueden cambiar en cualquier momento: confirma siempre en la tienda antes de comprar."
        ),
    },
    "📜・reglas": {
        "title": "📜 Reglas",
        "color": PURPLE,
        "description": (
            "**1.** Respeto ante todo: nada de insultos, acoso ni discriminación.\n"
            "**2.** Sin spam ni publicidad sin permiso.\n"
            "**3.** Nada de piratería, cuentas robadas ni claves de dudosa procedencia.\n"
            "**4.** Usa cada canal para su tema.\n"
            "**5.** Nada de contenido NSFW.\n"
            "**6.** No compartas datos personales tuyos ni de otros.\n"
            "**7.** Sigue las normas de Discord: https://discord.com/guidelines\n\n"
            "Quien no cumpla puede ser silenciado o expulsado."
        ),
    },
    "📢・anuncios": {
        "title": "📢 ¡El servidor está abierto!",
        "color": GREEN,
        "description": (
            "Desde hoy las mejores ofertas llegan solas a este servidor.\n\n"
            f"Todas las ofertas y el calendario de lanzamientos: {SITE}\n"
            "Invita a tus amigos gamers. 🎮"
        ),
    },
}


def call(method, path, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": f"DiscordBot ({SITE}, 1.0)",
    })
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            if exc.code == 429:  # límite de velocidad de Discord: esperar lo que pide
                time.sleep(float(json.loads(exc.read() or b"{}").get("retry_after", 2)) + 0.5)
                continue
            raise SystemExit(f"Discord respondió {exc.code} en {method} {path}: {exc.read()[:300]!r}")
    raise SystemExit("Discord siguió limitando las peticiones; prueba más tarde")


def setup(token, guild, api=call):
    channels = api("GET", f"/guilds/{guild}/channels", token)
    by_name = {(c["name"], c["type"]): c for c in channels}
    read_only = [{"id": guild, "type": 0, "deny": str(SEND_MESSAGES)}]  # @everyone lee pero no escribe
    created, ids = [], {}
    for position, (category, items) in enumerate(LAYOUT):
        cat = by_name.get((category, 4))
        if not cat:
            cat = api("POST", f"/guilds/{guild}/channels", token, {"name": category, "type": 4, "position": position})
            created.append(category)
        for kind, name, topic, locked in items:
            ctype = 0 if kind == "text" else 2
            chan = by_name.get((name, ctype))
            if not chan:
                payload = {"name": name, "type": ctype, "parent_id": cat["id"]}
                if topic:
                    payload["topic"] = topic
                if locked:
                    payload["permission_overwrites"] = read_only
                chan = api("POST", f"/guilds/{guild}/channels", token, payload)
                created.append(name)
            ids[name] = chan["id"]
    posted = []
    for name, embed in MESSAGES.items():
        if api("GET", f"/channels/{ids[name]}/messages?limit=1", token):
            continue  # ya tiene mensajes: no se repite
        desc = embed["description"]
        for short in ("ofertas", "juegos-gratis", "lanzamientos", "chat-general"):
            full = next(n for n in ids if n.endswith("・" + short))
            desc = desc.replace(f"<#{short}>", f"<#{ids[full]}>")
        api("POST", f"/channels/{ids[name]}/messages", token,
            {"embeds": [dict(embed, description=desc)], "allowed_mentions": {"parse": []}})
        posted.append(name)
    return created, posted, ids


def main():
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    guild = (os.environ.get("DISCORD_GUILD_ID") or "").strip()
    if not token or not guild.isdigit():
        sys.exit("Falta el secreto DISCORD_BOT_TOKEN o la variable DISCORD_GUILD_ID")
    created, posted, ids = setup(token, guild)
    print(f"Creados: {', '.join(created) or 'nada nuevo'}")
    print(f"Mensajes publicados: {', '.join(posted) or 'ninguno nuevo'}")
    print(f"Canal para el webhook de ofertas: 🔥・ofertas (id {ids['🔥・ofertas']})")


if __name__ == "__main__":
    main()
