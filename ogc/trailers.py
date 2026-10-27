"""Tráileres y capturas de Steam para las ofertas: avance al pasar el cursor y fotos en la página de cada oferta.

Se usan los tráileres que ya trae el calendario y, para el resto, la ficha pública de Steam (sin clave).
Se guardan en data/trailers.json y se piden pocos por corrida para no abusar de Steam.
"""

import sys
from datetime import timedelta

from .model import iso
from .releases import DETAILS_URL, steam_trailer

MAX_NEW = 50  # fichas nuevas por corrida
KEEP_DAYS = 30  # un tráiler se vuelve a revisar al mes


def update(offers, games, cache, now, fetch):
    """Devuelve (caché nueva, estado). cache = {appid: {"trailer": {...}, "at": iso}}."""
    cache = dict(cache or {})
    for g in games or []:
        if g.get("id", "").startswith("steam-") and g.get("trailer"):
            cache[g["id"][6:]] = {"trailer": g["trailer"], "shots": g.get("shots") or [], "at": g.get("verifiedAt") or iso(now)}
    stale = iso(now - timedelta(days=KEEP_DAYS))
    wanted = []
    for o in offers:
        app = str(o.get("steamAppID") or "")
        # las fichas guardadas antes sin capturas se vuelven a pedir una vez
        if app and app not in wanted and (app not in cache or (cache[app].get("at") or "") < stale or "shots" not in cache[app]):
            wanted.append(app)
    asked = failed = 0
    for app in wanted[:MAX_NEW]:
        asked += 1
        try:
            entry = (fetch(DETAILS_URL.format(id=app)) or {}).get(app) or {}
            info = entry.get("data") if entry.get("success") else None
            ok = isinstance(info, dict)
            shots = [x["path_thumbnail"] for x in (info.get("screenshots") or []) if (x.get("path_thumbnail") or "").startswith("https://")][:6] if ok else []
            cache[app] = {"trailer": steam_trailer(info) if ok else {}, "shots": shots, "at": iso(now)}
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
        entry = cache.get(str(o.get("steamAppID") or "")) or {}
        t = entry.get("trailer")
        if t and (t.get("hls") or t.get("video")):
            o["trailer"] = t
        if entry.get("shots"):
            o["shots"] = entry["shots"]
    return offers
