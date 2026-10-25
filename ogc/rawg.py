"""Juegos de consola (PlayStation, Xbox, Switch) desde la API oficial de RAWG.

Solo se activa con el secreto RAWG_API_KEY. La clave nunca se imprime ni se guarda.
RAWG pide citar la fuente: la página de lanzamientos enlaza a rawg.io cuando hay juegos de RAWG.
"""

import os
import sys
import urllib.parse
from datetime import timedelta

from .model import iso, slugify

API = "https://api.rawg.io/api/games"
PAGES = 3  # 40 juegos por página, ordenados por cuántos jugadores los agregaron (popularidad real de RAWG)
PLATFORMS = (("playstation", "PlayStation"), ("xbox", "Xbox"), ("nintendo switch", "Switch"),
             ("pc", "Windows"), ("macos", "Mac"), ("linux", "Linux"))


def platform_names(item):
    out = []
    for p in item.get("platforms") or []:
        name = ((p or {}).get("platform") or {}).get("name", "").lower()
        for key, label in PLATFORMS:
            if name.startswith(key) and label not in out:
                out.append(label)
    return out


def to_game(item, now, allow_tba=False):
    title = (item.get("name") or "").strip()
    released = item.get("released") or ""
    image = item.get("background_image") or ""
    if not title or not item.get("slug"):
        return None
    tba = bool(item.get("tba")) or len(released) != 10
    if tba and not allow_tba:
        return None
    return {
        "id": f"rawg-{item['id']}",
        "slug": slugify(title),
        "title": title,
        "description": "",
        "store": "RAWG",
        "url": f"https://rawg.io/games/{urllib.parse.quote(item['slug'])}",
        "image": image if image.startswith("https://") else "",
        "platforms": platform_names(item) or ["Windows"],
        "genres": [g["name"] for g in item.get("genres") or [] if g.get("name")][:3],
        "releaseText": "" if tba else released,
        "date": None if tba else released,
        "precision": None if tba else "day",
        "comingSoon": tba or released >= now.strftime("%Y-%m-%d"),
        "verifiedAt": iso(now),
        "source": "rawg",
        "added": item.get("added") or 0,  # cuántos jugadores de RAWG lo agregaron: su medida de popularidad
    }


def fetch_games(now, fetch, key):
    """Dos consultas: lo que sale (o salió) cerca de hoy, y los más esperados de los próximos dos años
    (ahí entran los grandes como GTA VI aunque su fecha no sea exacta: se muestran "por confirmar")."""
    day = lambda d: (now + timedelta(days=d)).strftime("%Y-%m-%d")
    games, seen = [], set()
    for dates, pages, allow_tba in ((f"{day(-30)},{day(120)}", PAGES, False), (f"{day(1)},{day(730)}", 2, True)):
        for page in range(1, pages + 1):
            query = urllib.parse.urlencode({"key": key, "dates": dates, "ordering": "-added", "page_size": 40, "page": page})
            data = fetch(f"{API}?{query}") or {}
            for item in data.get("results") or []:
                game = to_game(item, now, allow_tba)
                if game and game["id"] not in seen:
                    seen.add(game["id"])
                    games.append(game)
            if not data.get("next"):
                break
    games.sort(key=lambda g: -(g.get("added") or 0))
    return games


def merge(steam, rawg):
    """Une Steam y RAWG sin repetir juegos. Si un juego está en los dos, se queda la ficha de Steam
    y se le suman las consolas. El orden mezcla las dos listas de popularidad (1 de Steam, 1 de RAWG...)."""
    for i, g in enumerate(steam):
        g.pop("rawgRank", None)
        g["steamRank"] = g.get("rank") or i + 1
    by_slug = {g["slug"]: g for g in steam}
    extra = []
    for pos, g in enumerate(rawg):
        twin = by_slug.get(g["slug"])
        if twin:
            twin["platforms"] = twin["platforms"] + [p for p in g["platforms"] if p not in twin["platforms"]]
            twin["rawgRank"] = pos + 1
        else:
            extra.append(dict(g, rawgRank=pos + 1))
    ordered = sorted(steam + extra, key=lambda g: min(g.get("steamRank") or 9999, g.get("rawgRank") or 9999))
    return [dict(g, rank=i + 1) for i, g in enumerate(ordered)]


def add_consoles(steam, previous, now, fetch, env=os.environ):
    """Devuelve (juegos, estado). Sin clave o si RAWG falla, se usan los juegos de RAWG de la vez anterior."""
    key = (env.get("RAWG_API_KEY") or "").strip()
    old = [g for g in previous if g.get("source") == "rawg"]
    if not key:
        return merge(steam, old) if old else steam, "Sin configurar (falta el secreto RAWG_API_KEY)"
    try:
        rawg = fetch_games(now, fetch, key)
        if not rawg:
            raise ValueError("RAWG no devolvió juegos")
        return merge(steam, rawg), f"OK, {len(rawg)} juegos"
    except Exception as exc:  # no se imprime la URL: lleva la clave
        print(f"RAWG falló: {type(exc).__name__}", file=sys.stderr)
        return merge(steam, old) if old else steam, f"Falló ({type(exc).__name__}); se conservan los anteriores"
