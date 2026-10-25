"""Distribución: Telegram (automático) y texto para WhatsApp (manual). Discord está en ogc/discord.py."""

import html
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import timedelta, timezone

from .model import parse_iso


def money(amount, currency):
    if amount is None:
        return ""
    if currency == "COP":
        return "$" + f"{amount:,.0f}".replace(",", ".") + " COP"
    return f"US${amount:,.2f}"


def cop_text(offer):
    value = offer.get("copApproximation")
    return ("≈ $" + f"{value:,.0f}".replace(",", ".") + " COP aprox.") if value else ""


def price_line(offer):
    if offer.get("currentPrice") == 0:
        before = money(offer.get("originalPrice"), offer["currency"])
        return "GRATIS" + (f" (antes {before})" if before else "")
    parts = [money(offer["currentPrice"], offer["currency"])]
    if offer.get("originalPrice"):
        parts.append(f"antes {money(offer['originalPrice'], offer['currency'])}")
    if cop_text(offer):
        parts.append(cop_text(offer))
    return " · ".join(parts)


CO_TZ = timezone(timedelta(hours=-5))  # Colombia no tiene horario de verano
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def co_time(dt):
    """Fecha y hora en hora Colombia: '29 de octubre de 2026, 10:00 a. m. (hora Colombia)'."""
    d = dt.astimezone(CO_TZ)
    hour = d.hour % 12 or 12
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}, {hour}:{d.minute:02d} {'a. m.' if d.hour < 12 else 'p. m.'} (hora Colombia)"


def date_es(value):
    dt = parse_iso(value)
    return co_time(dt) if dt else ""


def time_left(value, now):
    """Texto corto del tiempo que le queda a una oferta, o '' si no hay fecha."""
    dt = parse_iso(value)
    if not dt:
        return ""
    mins = int((dt - now).total_seconds() // 60)
    if mins <= 0:
        return "Terminó"
    days, hours = mins // 1440, mins % 1440 // 60
    if days > 30:
        d = dt.astimezone(CO_TZ)
        return f"Disponible hasta el {d.day} de {MESES[d.month - 1]}"
    if days >= 1:
        return f"Termina en {days} {'día' if days == 1 else 'días'}" + (f", {hours} h" if hours else "")
    return f"Termina en {hours} h {mins % 60} min" if hours else f"Termina en {mins} min"


def region_text(offer):
    return "Colombia" if "CO" in offer.get("regions", []) else "no verificada (precio de referencia)"


def is_big_free(offer):
    """Un juego de pago caro que hoy está gratis (precio normal de US$20 o $70.000 o más)."""
    if offer.get("currentPrice") != 0 or not offer.get("originalPrice"):
        return False
    return offer["originalPrice"] >= (70000 if offer.get("currency") == "COP" else 20)


def telegram_caption(offer, prefix=""):
    title = html.escape(offer["title"])
    if not prefix and is_big_free(offer):
        prefix = "🚨 <b>JUEGO GRANDE GRATIS</b>\n"
    head = prefix + (f"🎁 <b>GRATIS</b> · {title}" if offer.get("currentPrice") == 0 else \
        f"🔥 <b>-{offer['discountPercentage']}%</b> · {title}" if offer.get("discountPercentage") else f"🔥 {title}")
    lines = [head, f"🛒 {html.escape(offer['store'])}", f"💲 {html.escape(price_line(offer))}"]
    lines.append(f"⏰ Hasta el {date_es(offer['expiresAt'])}" if offer.get("expiresAt") else "⏰ Vigencia: no informada por la tienda")
    lines.append(f"🌎 Región: {region_text(offer)}")
    lines.append(f'👉 <a href="{html.escape(offer["destinationUrl"])}">Ver oferta</a>')
    if offer.get("affiliate"):
        lines.append("<i>Enlace de afiliado: podemos recibir una comisión sin costo extra para ti.</i>")
    return "\n".join(lines)


def send_telegram(offer, token=None, chat=None, prefix=""):
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = chat or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    text = telegram_caption(offer, prefix)
    if offer.get("image"):
        method, payload = "sendPhoto", {"chat_id": chat, "photo": offer["image"], "caption": text, "parse_mode": "HTML"}
    else:
        method, payload = "sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}",
                                 data=urllib.parse.urlencode(payload).encode(), method="POST")
    try:
        urllib.request.urlopen(req, timeout=30).read()
        return True
    except Exception as exc:
        # Nunca imprimir la URL: contiene el token.
        print(f"Telegram falló con '{offer['title']}': {type(exc).__name__}", file=sys.stderr)
        return False


def whatsapp_text(offers, cfg, updated):
    # WhatsApp usa *negrita*. Meta no permite publicar en canales por API, así que se copia a mano.
    lines = [f"*🎮 Ofertas Gamer CO · {updated}*", ""]
    for o in offers[: cfg.get("ofertas_en_whatsapp", 8)]:
        tag = "🎁 *GRATIS*" if o.get("currentPrice") == 0 else f"🔥 *-{o['discountPercentage']}%*"
        lines.append(f"{tag} · {o['title']} ({o['store']})")
        lines.append(price_line(o) + (f" · hasta {date_es(o['expiresAt'])}" if o.get("expiresAt") else ""))
        lines.append(o["destinationUrl"])
        lines.append("")
    lines.append("Los precios pueden cambiar: revisa en la tienda antes de comprar.")
    if any(o.get("affiliate") for o in offers[: cfg.get("ofertas_en_whatsapp", 8)]):
        lines.append("Algunos enlaces son de afiliado.")
    lines.append(f"Todas las ofertas: {cfg['url_web']}")
    if cfg.get("enlace_canal_telegram"):
        lines.append(f"Al instante en Telegram: {cfg['enlace_canal_telegram']}")
    return "\n".join(lines)
