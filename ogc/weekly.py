"""Resumen semanal: cada viernes (hora Colombia) sale solo a Telegram, Discord y Bluesky, y queda en la web.

Solo usa ofertas y lanzamientos reales que ya están en los datos; no inventa nada.
El historial (data/resumenes.json) guarda una foto de cada resumen para que su página no cambie después.
"""

import html
import os
import sys
import urllib.parse
import urllib.request
from datetime import timedelta

from .channels import CO_TZ, MESES, money, price_line

FRIDAY = 4
FROM_HOUR = 9  # desde las 9 a. m. del viernes
KEEP = 26  # semanas guardadas en el historial
FIELDS = ("id", "title", "store", "storeId", "currentPrice", "originalPrice", "currency", "discountPercentage",
          "copApproximation", "image", "imageSmall", "destinationUrl", "officialUrl", "affiliate", "expiresAt", "regions")
GAME_FIELDS = ("id", "title", "date", "precision", "platforms", "genres", "image", "url", "store", "source")


def week_key(now):
    y, w, _ = now.astimezone(CO_TZ).isocalendar()
    return f"{y}-S{w:02d}"


def is_due(now, history):
    co = now.astimezone(CO_TZ)
    done = {h["week"] for h in history}
    return co.weekday() == FRIDAY and co.hour >= FROM_HOUR and week_key(now) not in done


def pick(offers, games, now, deals_count=10):
    live = [o for o in offers if o.get("status") != "Vencido"]
    free = [o for o in live if o.get("currentPrice") == 0][:6]
    deals = sorted([o for o in live if o.get("currentPrice") and (o.get("discountPercentage") or 0) >= 50],
                   key=lambda o: (-("CO" in (o.get("regions") or [])), -((o.get("metacritic") or 0) // 10),
                                  -(o.get("discountPercentage") or 0)))[:deals_count]
    today = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
    week_end = (now + timedelta(days=7)).astimezone(CO_TZ).strftime("%Y-%m-%d")
    coming = sorted([g for g in games if g.get("precision") == "day" and g.get("date") and today <= g["date"] <= week_end],
                    key=lambda g: g.get("rank") or 9999)[:6]
    return free, deals, coming


def snapshot(now, free, deals, coming):
    keep = lambda items, fields: [{k: it.get(k) for k in fields if it.get(k) is not None} for it in items]
    co = now.astimezone(CO_TZ)
    return {"week": week_key(now), "date": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "label": f"{co.day} de {MESES[co.month - 1]} de {co.year}",
            "free": keep(free, FIELDS), "deals": keep(deals, FIELDS), "games": keep(coming, GAME_FIELDS)}


def page_name(snap):
    return f"resumen-{snap['week'].lower()}.html"


def telegram_text(snap, link):
    e = html.escape
    lines = [f"<b>🗓️ Resumen semanal · {e(snap['label'])}</b>", ""]
    if snap["free"]:
        lines.append("<b>🎁 Gratis esta semana</b>")
        lines += [f"• {e(o['title'])} ({e(o['store'])})" for o in snap["free"]]
        lines.append("")
    if snap["deals"]:
        lines.append("<b>🔥 Mejores descuentos</b>")
        lines += [f"• {e(o['title'])}: -{o.get('discountPercentage') or 0}% · {e(price_line(o))}" for o in snap["deals"]]
        lines.append("")
    if snap["games"]:
        lines.append("<b>📅 Salen esta semana</b>")
        lines += [f"• {e(g['title'])} ({e(g['date'][8:10])}/{e(g['date'][5:7])})" for g in snap["games"]]
        lines.append("")
    lines.append(f'Todo con enlaces: <a href="{e(link)}">{e(link)}</a>')
    lines.append("<i>Los precios pueden cambiar: confirma en la tienda.</i>")
    return "\n".join(lines)[:4000]


def short_text(snap):
    parts = [f"🗓️ Resumen semanal de ofertas gamer ({snap['label']})"]
    if snap["free"]:
        parts.append(f"🎁 {len(snap['free'])} gratis: " + ", ".join(o["title"] for o in snap["free"][:3]))
    if snap["deals"]:
        top = snap["deals"][0]
        parts.append(f"🔥 Top: {top['title']} -{top.get('discountPercentage') or 0}%")
    return "\n".join(parts) + "\n"


def discord_embed(snap, link):
    fields = []
    if snap["free"]:
        fields.append({"name": "🎁 Gratis", "value": "\n".join(f"• {o['title']} ({o['store']})" for o in snap["free"])[:1024]})
    if snap["deals"]:
        fields.append({"name": "🔥 Mejores descuentos", "value": "\n".join(
            f"• {o['title']}: -{o.get('discountPercentage') or 0}% · {money(o['currentPrice'], o['currency'])}" for o in snap["deals"])[:1024]})
    if snap["games"]:
        fields.append({"name": "📅 Salen esta semana", "value": "\n".join(
            f"• {g['title']} ({g['date'][8:10]}/{g['date'][5:7]})" for g in snap["games"])[:1024]})
    embed = {"title": f"🗓️ Resumen semanal · {snap['label']}", "url": link, "color": 0x5B8CFF, "fields": fields,
             "footer": {"text": "Ofertas Gamer CO · confirma el precio en la tienda"}}
    image = next((o.get("image") for o in snap["deals"] + snap["free"] if (o.get("image") or "").startswith("https://")), None)
    if image:
        embed["image"] = {"url": image}
    return embed


def send_telegram_text(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text, "parse_mode": "HTML"}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data,
                                                      method="POST"), timeout=30).read()
        return True
    except Exception as exc:  # nunca imprimir la URL: lleva el token
        print(f"Telegram falló con el resumen semanal: {type(exc).__name__}", file=sys.stderr)
        return False


def publish(snap, link, dc=None, bluesky=None):
    """Envía el resumen a cada red. Devuelve la lista de redes donde salió."""
    done = []
    if send_telegram_text(telegram_text(snap, link)):
        done.append("Telegram")
    if dc is not None and dc.ready and dc.post("ofertas", [discord_embed(snap, link)]):
        done.append("Discord")
    if bluesky is not None:
        image = next((o.get("image") for o in snap["deals"] + snap["free"] if o.get("image")), None)
        if bluesky(short_text(snap), link, f"Resumen semanal · {snap['label']}", "Gratis, mejores descuentos y estrenos de la semana", image):
            done.append("Bluesky")
    return done
