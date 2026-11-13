"""Portadas verticales (600×900) de Steam para las cajas del diseño «Estantería».

Se piden a la API pública IStoreBrowseService/GetItems (sin clave), en lotes, y se guardan en
data/portadas.json. Solo se vuelve a preguntar por un juego cada 14 días. Si Steam falla, se usa lo guardado.
"""

import json
import sys
import urllib.parse
from datetime import timedelta

from .model import iso

API = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?input_json="
CDN = "https://shared.fastly.steamstatic.com/store_item_assets/"
BATCH = 50
MAX_BATCHES = 12  # hasta 600 juegos por corrida
KEEP_DAYS = 14


def _url(item):
    a = item.get("assets") or {}
    fmt, name = a.get("asset_url_format") or "", a.get("library_capsule") or ""
    if not fmt or not name or "${FILENAME}" not in fmt or ":" in fmt:
        return ""
    return CDN + fmt.replace("${FILENAME}", name)


def update(offers, cache, now, fetch):
    """Devuelve (caché nueva, estado). cache = {appid: {"url": str ("" si no tiene), "at": iso}}."""
    cache = dict(cache or {})
    stale = iso(now - timedelta(days=KEEP_DAYS))
    wanted = []
    for o in offers:
        app = str(o.get("steamAppID") or "")
        if app.isdigit() and app not in wanted and (cache.get(app) or {}).get("at", "") < stale:
            wanted.append(app)
    asked = failed = 0
    for start in range(0, min(len(wanted), BATCH * MAX_BATCHES), BATCH):
        chunk = wanted[start:start + BATCH]
        query = {"ids": [{"appid": int(a)} for a in chunk], "context": {"country_code": "CO", "language": "spanish"},
                 "data_request": {"include_assets": True}}
        try:
            data = fetch(API + urllib.parse.quote(json.dumps(query))) or {}
            found = {str(it.get("appid")): _url(it) for it in (data.get("response") or {}).get("store_items") or []}
            for app in chunk:
                cache[app] = {"url": found.get(app, ""), "at": iso(now)}
            asked += len(chunk)
        except Exception as exc:  # un lote que falla no tumba nada; se reintenta en otra corrida
            failed += 1
            print(f"Portadas: Steam falló ({type(exc).__name__}): {exc}", file=sys.stderr)
    live = {str(o.get("steamAppID")) for o in offers if o.get("steamAppID")}
    cache = {k: v for k, v in cache.items() if k in live}
    have = sum(1 for o in offers if (cache.get(str(o.get("steamAppID") or "")) or {}).get("url"))
    return cache, f"OK, {have} ofertas con portada vertical; {asked} juegos consultados" + (f"; {failed} {'lote falló' if failed == 1 else 'lotes fallaron'}" if failed else "")


def attach(offers, cache):
    """Pone en cada oferta su portada vertical (`capsule`) si Steam la tiene."""
    for o in offers:
        url = (cache.get(str(o.get("steamAppID") or "")) or {}).get("url") or ""
        if url.startswith(CDN):
            o["capsule"] = url
    return offers
