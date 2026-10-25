"""Juegos grandes de PC y consolas (PlayStation, Xbox, Switch) desde Wikidata, la base de datos de Wikipedia.

No necesita cuenta ni clave. La popularidad es real y verificable: en cuántos idiomas de Wikipedia
tiene artículo cada juego (los grandes como GTA VI tienen decenas). Las fechas se usan con la
precisión que da Wikidata: día exacto, solo el mes o, si solo se sabe el año, "por confirmar".
"""

import re
import sys
import urllib.parse
from datetime import timedelta

from .model import iso, slugify

ENDPOINT = "https://query.wikidata.org/sparql"
MIN_LANGS = 3  # un juego con artículo en 3 o más Wikipedias ya es conocido
LIMIT = 250
PLATFORMS = (("playstation", "PlayStation"), ("xbox", "Xbox"), ("nintendo switch", "Switch"),
             ("microsoft windows", "Windows"), ("macos", "Mac"), ("linux", "Linux"))

# p:/ps: (no wdt:) para traer todas las plataformas: con wdt: Wikidata solo da la "preferida" (GTA VI salía solo en Xbox)
QUERY = """SELECT ?g ?gLabel ?links (SAMPLE(?steam0) AS ?steam) (SAMPLE(?es0) AS ?es) (SAMPLE(?en0) AS ?en) (SAMPLE(?yt0) AS ?yt)
  (GROUP_CONCAT(DISTINCT CONCAT(STR(?date), "#", STR(?prec)); separator="|") AS ?dates)
  (GROUP_CONCAT(DISTINCT CONCAT(STR(?p), "=", COALESCE(?platL, "")); separator="|") AS ?plats) (GROUP_CONCAT(DISTINCT ?genL; separator="|") AS ?gens) WHERE {
  ?g wdt:P31 wd:Q7889; p:P577/psv:P577 [wikibase:timeValue ?date; wikibase:timePrecision ?prec];
     wikibase:sitelinks ?links.
  FILTER(?links >= %(min)d && ?date >= "%(start)sT00:00:00Z"^^xsd:dateTime && ?date <= "%(end)sT00:00:00Z"^^xsd:dateTime)
  FILTER NOT EXISTS { ?g wdt:P577 ?old FILTER(?old < "%(start)sT00:00:00Z"^^xsd:dateTime) }
  OPTIONAL { ?g p:P400/ps:P400 ?p. OPTIONAL { ?p rdfs:label ?platL FILTER(lang(?platL) IN ("en", "es", "mul")) } }
  OPTIONAL { ?g p:P136/ps:P136 ?ge. ?ge rdfs:label ?genL FILTER(lang(?genL) = "es") }
  OPTIONAL { ?g wdt:P1733 ?steam0 }
  OPTIONAL { ?g wdt:P1651 ?yt0 }
  OPTIONAL { ?es0 schema:about ?g; schema:isPartOf <https://es.wikipedia.org/> }
  OPTIONAL { ?en0 schema:about ?g; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en,mul". }
} GROUP BY ?g ?gLabel ?links ORDER BY DESC(?links) LIMIT %(limit)d"""


def val(row, key):
    return (row.get(key) or {}).get("value") or ""


# por número de Wikidata, porque algunas consolas no tienen nombre en inglés (PlayStation 5, por ejemplo)
PLATFORM_IDS = {"Q63184502": "PlayStation", "Q5014725": "PlayStation", "Q98973368": "Xbox", "Q13361286": "Xbox",
                "Q19610114": "Switch", "Q1406": "Windows", "Q14116": "Mac", "Q388": "Linux"}


def platform_names(text):
    """De "http://www.wikidata.org/entity/Q63184502=|...=Microsoft Windows" saca las plataformas conocidas."""
    out = []
    for part in text.split("|"):
        uri, _, name = part.partition("=") if "=" in part else ("", "", part)
        label = PLATFORM_IDS.get(uri.rsplit("/", 1)[-1])
        if not label:
            label = next((lab for key, lab in PLATFORMS if name.lower().startswith(key)), None)
        if label and label not in out:
            out.append(label)
    return out


def to_game(row, now):
    qid = val(row, "g").rsplit("/", 1)[-1]
    title = val(row, "gLabel").strip()
    if not qid.startswith("Q") or not title or title == qid:
        return None
    date_text, prec_text = first_date(val(row, "dates"))
    day, prec = date_text[:10], int(prec_text or 0)
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
        "platforms": platform_names(val(row, "plats")),
        "genres": [g.capitalize() for g in val(row, "gens").split("|") if g][:3],
        "releaseText": text,
        "date": date,
        "precision": precision,
        "comingSoon": not date or date >= now.strftime("%Y-%m-%d") or precision == "month",
        "verifiedAt": iso(now),
        "source": "wikidata",
        "youtube": val(row, "yt") if re.fullmatch(r"[A-Za-z0-9_-]{11}", val(row, "yt")) else "",
        "languages": int(val(row, "links") or 0),
    }


def first_date(text):
    """De "2026-11-19T00:00:00Z#11|2027-..." toma la fecha más temprana con su precisión."""
    pairs = sorted(p.split("#") for p in text.split("|") if "#" in p)
    return (pairs[0][0], pairs[0][1]) if pairs else ("", "0")


def fetch_games(now, fetch):
    start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=730)).strftime("%Y-%m-%d")
    query = QUERY % {"min": MIN_LANGS, "start": start, "end": end, "limit": LIMIT}
    data = fetch(f"{ENDPOINT}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}") or {}
    games, seen = [], set()
    for row in (data.get("results") or {}).get("bindings") or []:
        game = to_game(row, now)
        if game and game["id"] not in seen:
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


SUMMARY = "https://es.wikipedia.org/api/rest_v1/page/summary/{}"


def enrich(games, previous, fetch, limit=80):
    """Portada y resumen para los juegos que no vienen de Steam.
    Portada: la miniatura del tráiler oficial en YouTube; si no hay, la imagen de Wikipedia en español
    (allí solo se permiten imágenes libres). Resumen: el primer párrafo del artículo de Wikipedia en español.
    Lo ya conseguido en ejecuciones anteriores se reutiliza."""
    old = {g["id"]: g for g in previous}
    asked = 0
    for g in games:
        if g.get("store") == "Steam":
            continue
        prev = old.get(g["id"]) or {}
        for key in ("image", "imageSmall", "description"):
            if prev.get(key) and not g.get(key):
                g[key] = prev[key]
        if g.get("youtube") and not g.get("image"):
            g["image"] = f"https://i.ytimg.com/vi/{g['youtube']}/maxresdefault.jpg"
            g["imageSmall"] = f"https://i.ytimg.com/vi/{g['youtube']}/hqdefault.jpg"
        page = g["url"].split("/wiki/", 1)[1] if g["url"].startswith("https://es.wikipedia.org/wiki/") else ""
        if page and (not g.get("description") or not g.get("image")) and asked < limit and not prev.get("summaryChecked"):
            asked += 1
            try:
                info = fetch(SUMMARY.format(page)) or {}
            except Exception as exc:
                print(f"Wikipedia: resumen de {page} falló: {type(exc).__name__}", file=sys.stderr)
                continue
            text = re.sub(r"\s+", " ", info.get("extract") or "").strip()
            if text and not g.get("description"):
                g["description"] = text[:400]
            thumb = ((info.get("originalimage") or info.get("thumbnail") or {}).get("source") or "")
            if thumb.startswith("https://upload.wikimedia.org/") and not g.get("image"):
                g["image"] = thumb
            g["summaryChecked"] = True
        elif prev.get("summaryChecked"):
            g["summaryChecked"] = True
    return games


def add_consoles(steam, previous, now, fetch):
    """Devuelve (juegos, estado). Si Wikidata falla se usan los juegos de Wikidata de la vez anterior."""
    old = [g for g in previous if g.get("source") == "wikidata"]
    try:
        extra = fetch_games(now, fetch)
        if not extra:
            raise ValueError("Wikidata no devolvió juegos")
        return merge(steam, enrich(extra, previous, fetch)), f"OK, {len(extra)} juegos"
    except Exception as exc:
        print(f"Wikidata falló: {type(exc).__name__}: {exc}", file=sys.stderr)
        return merge(steam, old) if old else steam, f"Falló ({type(exc).__name__}); se conservan los anteriores"
