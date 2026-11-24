"""Reseñas de jugadores de Steam (en español) para la ficha de cada oferta.

Fuente: la lista pública de reseñas de cada juego en la tienda de Steam (appreviews, sin clave). Se guardan
en data/resenas.json y se piden pocas por corrida. Si Steam no responde (a veces redirige a su portada),
no se muestra nada: nunca se inventan reseñas. Se guardan solo el texto (limpio y recortado), si recomienda
o no el juego, las horas jugadas, la fecha y cuántas personas la marcaron útil. No se guardan nombres.
"""

import html
import re
import sys
from datetime import datetime, timedelta, timezone

from .model import iso

URL = ("https://store.steampowered.com/appreviews/{id}?json=1&language=spanish&filter=all&review_type=all"
       "&purchase_type=all&num_per_page=6&day_range=365")
MAX_NEW = 60       # juegos por corrida
KEEP_DAYS = 7      # se vuelven a pedir cada semana
MAX_FAILS = 4      # si falla seguido, se deja de insistir en esta corrida
KEEP = 3           # reseñas por juego
MAX_CHARS = 420


def clean(text):
    """Texto plano de una reseña: sin BBCode, sin HTML, sin espacios de sobra, recortado."""
    t = html.unescape(str(text or ""))
    t = re.sub(r"\[/?[a-z0-9*]+(?:=[^\]]*)?\]", " ", t, flags=re.I)  # [h1], [b], [url=...]...
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > MAX_CHARS:
        t = t[:MAX_CHARS - 1].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return t


def pick(data):
    """Las reseñas que valen la pena mostrar: con texto de verdad, las más votadas como útiles primero."""
    rows = []
    for r in (data or {}).get("reviews") or [] if isinstance(data, dict) else []:
        text = clean(r.get("review"))
        if len(text) < 40:
            continue
        a = r.get("author") or {}
        hours = round((a.get("playtime_forever") or 0) / 60)
        ts = r.get("timestamp_created")
        rows.append({"text": text, "up": bool(r.get("voted_up")), "hours": hours,
                     "date": datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d") if ts else None,
                     "helpful": int(r.get("votes_up") or 0)})
    rows.sort(key=lambda x: -x["helpful"])
    return rows[:KEEP]


def update(offers, cache, now, fetch):
    """Devuelve (caché nueva, estado). cache = {appid: {"items": [...], "at": iso}}."""
    cache = dict(cache or {})
    stale = iso(now - timedelta(days=KEEP_DAYS))
    wanted = []
    for o in offers:
        app = str(o.get("steamAppID") or "")
        if app.isdigit() and app not in wanted and (cache.get(app) or {}).get("at", "") < stale:
            wanted.append(app)
    asked = fails = streak = 0
    for app in wanted[:MAX_NEW]:
        if streak >= MAX_FAILS:
            break
        asked += 1
        try:
            data = fetch(URL.format(id=app))
            if not isinstance(data, dict) or data.get("success") != 1:
                raise ValueError("respuesta sin reseñas")
            cache[app] = {"items": pick(data), "at": iso(now)}
            streak = 0
        except Exception as exc:  # Steam a veces redirige a su portada: no se publica nada
            fails += 1
            streak += 1
            print(f"Reseñas: Steam {app} falló ({type(exc).__name__})", file=sys.stderr)
    live = {str(o.get("steamAppID")) for o in offers if o.get("steamAppID")}
    cache = {k: v for k, v in cache.items() if k in live}
    have = sum(1 for o in offers if (cache.get(str(o.get("steamAppID") or "")) or {}).get("items"))
    return cache, f"{'OK' if asked > fails else 'Sin respuesta de Steam'}, {have} ofertas con reseñas; {asked} pedidas, {fails} fallaron"


def attach(offers, cache):
    for o in offers:
        items = (cache.get(str(o.get("steamAppID") or "")) or {}).get("items")
        if items:
            o["userReviews"] = items
    return offers
