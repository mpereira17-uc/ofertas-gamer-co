"""Juegos grandes de PC y consolas (PlayStation, Xbox, Switch) desde Wikidata, la base de datos de Wikipedia.

No necesita cuenta ni clave. La popularidad es real y verificable: en cuántos idiomas de Wikipedia
tiene artículo cada juego (los grandes como GTA VI tienen decenas). Las fechas se usan con la
precisión que da Wikidata: día exacto, solo el mes o, si solo se sabe el año, "por confirmar".
"""

import sys
import urllib.parse
from datetime import timedelta

from .model import iso, slugify

ENDPOINT = "https://query.wikidata.org/sparql"
MIN_LANGS = 6  # un juego con artículo en 6 o más Wikipedias ya es conocido
LIMIT = 120
PLATFORMS = (("playstation", "PlayStation"), ("xbox", "Xbox"), ("nintendo switch", "Switch"),
             ("microsoft windows", "Windows"), ("macos", "Mac"), ("linux", "Linux"))

QUERY = """SELECT ?g ?gLabel ?date ?prec ?links ?steam ?es ?en
  (GROUP_CONCAT(DISTINCT ?platL; separator="|") AS ?plats) (GROUP_CONCAT(DISTINCT ?genL; separator="|") AS ?gens) WHERE {
  ?g wdt:P31 wd:Q7889; p:P577/psv:P577 [wikibase:timeValue ?date; wikibase:timePrecision ?prec];
     wikibase:sitelinks ?links.
  FILTER(?links >= %(min)d && ?date >= "%(start)sT00:00:00Z"^^xsd:dateTime && ?date <= "%(end)sT00:00:00Z"^^xsd:dateTime)
  FILTER NOT EXISTS { ?g wdt:P577 ?old FILTER(?old < "%(start)sT00:00:00Z"^^xsd:dateTime) }
  OPTIONAL { ?g wdt:P400 ?p. ?p rdfs:label ?platL FILTER(lang(?platL) = "en") }
  OPTIONAL { ?g wdt:P136 ?ge. ?ge rdfs:label ?genL FILTER(lang(?genL) = "es") }
  OPTIONAL { ?g wdt:P1733 ?steam }
  OPTIONAL { ?es schema:about ?g; schema:isPartOf <https://es.wikipedia.org/> }
  OPTIONAL { ?en schema:about ?g; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
} GROUP BY ?g ?gLabel ?date ?prec ?links ?steam ?es ?en ORDER BY DESC(?links) LIMIT %(limit)d"""


def val(row, key):
    return (row.get(key) or {}).get("value") or ""


def platform_names(text):
    out = []
    for name in text.lower().split("|"):
        for key, label in PLATFORMS:
            if name.startswith(key) and label not in out:
                out.append(label)
    return out


def to_game(row, now):
    qid = val(row, "g").rsplit("/", 1)[-1]
    title = val(row, "gLabel").strip()
    if not qid.startswith("Q") or not title or title == qid:
        return None
    day, prec = val(row, "date")[:10], int(val(row, "prec") or 0)
    if prec >= 11:
        date, precision, text = day, "day", day
    elif prec == 10:
        date, precision, text = day[:7] + "-01", "month", day[:7]
    else:  # solo el año (o menos): no se inventa el día
        date, precision, text = None, None, day[:4]
    steam = val(row, "steam")
    if steam.isdigit():
        url = f"https://store.steampowered.com/app/{steam}/"
        image = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{steam}/header.jpg"
    else:
        url, image = val(row, "es") or val(row, "en") or f"https://www.wikidata.org/wiki/{qid}", ""
    return {
        "id": f"steam-{steam}" if steam.isdigit() else f"wd-{qid}",
        "slug": slugify(title),
        "title": title,
        "description": "",
        "store": "Steam" if steam.isdigit() else "Wikipedia",
        "url": url,
        "image": image,
        "platforms": platform_names(val(row, "plats")) or ["Windows"],
        "genres": [g.capitalize() for g in val(row, "gens").split("|") if g][:3],
        "releaseText": text,
        "date": date,
        "precision": precision,
        "comingSoon": not date or date >= now.strftime("%Y-%m-%d") or precision == "month",
        "verifiedAt": iso(now),
        "source": "wikidata",
        "languages": int(val(row, "links") or 0),
    }


def fetch_games(now, fetch):
    start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=730)).strftime("%Y-%m-%d")
    query = QUERY % {"min": MIN_LANGS, "start": start, "end": end, "limit": LIMIT}
    data = fetch(f"{ENDPOINT}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}") or {}
    games, seen = [], set()
    for row in (data.get("results") or {}).get("bindings") or []:
        game = to_game(row, now)
        if game and game["id"] not in seen:  # un juego con varias fechas sale una sola vez (la primera)
            seen.add(game["id"])
            games.append(game)
    return games


def merge(steam, extra):
    """Une Steam y Wikidata sin repetir. Si el juego ya está en Steam se queda esa ficha y se le suman
    las consolas. El orden mezcla las dos listas de popularidad (1 de Steam, 1 de Wikidata...)."""
    for i, g in enumerate(steam):
        g.pop("wdRank", None)
        g["steamRank"] = g.get("rank") or i + 1
    by_id = {g["id"]: g for g in steam}
    by_slug = {g["slug"]: g for g in steam}
    added = []
    for pos, g in enumerate(extra):
        twin = by_id.get(g["id"]) or by_slug.get(g["slug"])
        if twin:
            twin["platforms"] = twin["platforms"] + [p for p in g["platforms"] if p not in twin["platforms"]]
            twin["wdRank"] = pos + 1
        else:
            added.append(dict(g, wdRank=pos + 1))
    ordered = sorted(steam + added, key=lambda g: min(g.get("steamRank") or 9999, g.get("wdRank") or 9999))
    return [dict(g, rank=i + 1) for i, g in enumerate(ordered)]


def add_consoles(steam, previous, now, fetch):
    """Devuelve (juegos, estado). Si Wikidata falla se usan los juegos de Wikidata de la vez anterior."""
    old = [g for g in previous if g.get("source") == "wikidata"]
    try:
        extra = fetch_games(now, fetch)
        if not extra:
            raise ValueError("Wikidata no devolvió juegos")
        return merge(steam, extra), f"OK, {len(extra)} juegos"
    except Exception as exc:
        print(f"Wikidata falló: {type(exc).__name__}: {exc}", file=sys.stderr)
        return merge(steam, old) if old else steam, f"Falló ({type(exc).__name__}); se conservan los anteriores"
