"""Novedades de PC Game Pass: los juegos que Microsoft agregó hace poco al catálogo de PC.

Fuente oficial y pública (sin clave): las listas del catálogo de Game Pass para el mercado de Colombia y la
ficha de cada producto en el catálogo de la Microsoft Store (título, editor y póster vertical). Se guarda en
data/gamepass.json; si la fuente falla, se conserva la última lista. No es un juego gratis: viene incluido
con la suscripción, y la página lo dice así.
"""

import sys

from .model import iso

RECENT = "https://catalog.gamepass.com/sigls/v2?id=f13cf6b4-57e6-4459-89df-6aec18cf0538&language=es-co&market=CO"
ALL_PC = "https://catalog.gamepass.com/sigls/v2?id=609d944c-d395-4c0a-9ea4-e9f39b52c1ad&language=es-co&market=CO"
PRODUCTS = "https://displaycatalog.mp.microsoft.com/v7.0/products?bigIds={ids}&market=CO&languages=es-co&MS-CV=DGU1mcuYo0WMMp+F.1"
STORE_URL = "https://www.microsoft.com/es-co/p/x/{id}"
MAX_ITEMS = 24
BATCH = 20


def _ids(rows):
    out = []
    for r in rows if isinstance(rows, list) else []:
        pid = str((r or {}).get("id") or "")
        if pid.isalnum() and 8 <= len(pid) <= 16 and pid not in out:
            out.append(pid)
    return out


def _image(lp, purpose):
    for im in lp.get("Images") or []:
        if im.get("ImagePurpose") == purpose:
            uri = im.get("Uri") or ""
            uri = "https:" + uri if uri.startswith("//") else uri
            if uri.startswith("https://store-images.s-microsoft.com/"):
                return uri
    return ""


def _product(p):
    lp = (p.get("LocalizedProperties") or [{}])[0]
    pid, title = p.get("ProductId") or "", (lp.get("ProductTitle") or "").strip()
    poster = _image(lp, "Poster") or _image(lp, "BoxArt")
    if not pid or not title or not poster:
        return None
    return {"id": pid, "title": title[:120], "publisher": (lp.get("PublisherName") or "").strip()[:80],
            "poster": poster + "?w=300", "url": STORE_URL.format(id=pid)}


def update(previous, now, fetch):
    """Devuelve (estado, texto de estado). estado = {"updatedAt", "total", "recent": [...], "firstSeen": {id: iso}}."""
    previous = previous or {}
    try:
        ids = _ids(fetch(RECENT))[:MAX_ITEMS]
        if not ids:
            raise ValueError("la lista de recientes llegó vacía")
        found = {}
        for start in range(0, len(ids), BATCH):
            data = fetch(PRODUCTS.format(ids=",".join(ids[start:start + BATCH]))) or {}
            for p in data.get("Products") or []:
                item = _product(p)
                if item:
                    found[item["id"]] = item
        recent = [found[i] for i in ids if i in found]
        if not recent:
            raise ValueError("ningún juego trajo título e imagen")
        try:
            total = len(_ids(fetch(ALL_PC)))
        except Exception:
            total = previous.get("total") or 0
        seen = dict(previous.get("firstSeen") or {})
        first = not seen
        for it in recent:
            seen.setdefault(it["id"], None if first else iso(now))  # en la primera revisión no se sabe cuándo llegó
        seen = {k: v for k, v in seen.items() if k in {it["id"] for it in recent}}
        state = {"updatedAt": iso(now), "total": total, "recent": recent, "firstSeen": seen}
        return state, f"OK, {len(recent)} recientes de {total} juegos de PC"
    except Exception as exc:
        print(f"PC Game Pass falló ({type(exc).__name__}): {exc}", file=sys.stderr)
        return previous, f"Falló ({type(exc).__name__}); se usa la lista anterior"
