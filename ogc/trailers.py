"""Tráileres de Steam para las ofertas: así se puede ver un avance al pasar el cursor por la tarjeta.

Se usan los tráileres que ya trae el calendario y, para el resto, la ficha pública de Steam (sin clave).
Se guardan en data/trailers.json y se piden pocos por corrida para no abusar de Steam.
"""

import sys
from datetime import timedelta

from .model import iso
from .releases import DETAILS_URL, steam_trailer

MAX_NEW = 60  # fichas nuevas por corrida
KEEP_DAYS = 30  # un tráiler se vuelve a revisar al mes


def update(offers, games, cache, now, fetch):
    """Devuelve (caché nueva, estado). cache = {appid: {"trailer": {...}, "at": iso}}."""
    cache = dict(cache or {})
    for g in games or []:
        if g.get("id", "").startswith("steam-") and g.get("trailer"):
            cache[g["id"][6:]] = {"trailer": g["trailer"], "at": g.get("verifiedAt") or iso(now)}
    stale = iso(now - timedelta(days=KEEP_DAYS))
    wanted = []
    for o in offers:
        app = str(o.get("steamAppID") or "")
        if app and app not in wanted and (app not in cache or (cache[app].get("at") or "") < stale):
            wanted.append(app)
    asked = failed = 0
    for app in wanted[:MAX_NEW]:
        asked += 1
        try:
            entry = (fetch(DETAILS_URL.format(id=app)) or {}).get(app) or {}
            info = entry.get("data") if entry.get("success") else None
            cache[app] = {"trailer": steam_trailer(info) if isinstance(info, dict) else {}, "at": iso(now)}
        except Exception as exc:  # un juego que falla no tumba nada; se reintenta en otra corrida
            failed += 1
            print(f"Tráileres: Steam {app} falló: {exc}", file=sys.stderr)
    live = {str(o.get("steamAppID")) for o in offers if o.get("steamAppID")}
    cache = {k: v for k, v in cache.items() if k in live or any(g.get("id") == f"steam-{k}" for g in games or [])}
    have = sum(1 for o in offers if (cache.get(str(o.get("steamAppID") or "")) or {}).get("trailer"))
    return cache, f"OK, {have} ofertas con tráiler; {asked} fichas pedidas{f', {failed} fallaron' if failed else ''}"


def attach(offers, cache):
    """Pone en cada oferta su tráiler (si lo hay) para que la página lo muestre."""
    for o in offers:
        t = (cache.get(str(o.get("steamAppID") or "")) or {}).get("trailer")
        if t and (t.get("hls") or t.get("video")):
            o["trailer"] = t
    return offers
