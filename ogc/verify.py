"""Verificación antes de publicar (pedido de pepe, 2026-11-13: «hay que verificar bien la información antes de
montarla en mi página»).

CheapShark da precios de Estados Unidos y, fuera de Steam, solo un enlace de búsqueda. Antes de publicar:
- Steam: se confirma con la tienda de Steam para Colombia (IStoreBrowseService, país CO). Se publica el precio
  oficial en pesos, el descuento y la fecha de fin. Si en Colombia no tiene descuento, no se publica.
- GOG: se busca en el catálogo público de GOG para Colombia. Se publica solo si el título coincide, tiene
  descuento allá, y con el enlace a la página exacta del juego y su precio para Colombia.
- Las demás tiendas (Humble, Fanatical, Green Man Gaming) no permiten comprobarlo de forma automática:
  sus ofertas no se publican hasta tener cómo verificarlas.
Si la verificación de Steam o de GOG falla por completo, se lanza un error y el bot conserva la última
lista válida (no se publica nada sin verificar).
"""

import json
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone

from .model import discount

STEAM_API = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?input_json="
GOG_SEARCH = "https://catalog.gog.com/v1/catalog?limit=5&query=like:{q}&productType=in:game,pack&countryCode=CO&currencyCode=USD"
VERIFIED_STORES = {"steam", "gog"}
BATCH = 50


def norm(title):
    t = re.sub(r"[™®©]", "", str(title or ""))
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"['’`]", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _int(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def verify_steam(offers, fetch):
    """Devuelve las ofertas de Steam con el precio oficial para Colombia (en pesos); quita las que allá no tienen descuento."""
    ids = []
    for o in offers:
        app = o.get("steamAppID")
        if isinstance(app, int) and app not in ids:
            ids.append(app)
    found, answered = {}, 0
    for start in range(0, len(ids), BATCH):
        q = {"ids": [{"appid": a} for a in ids[start:start + BATCH]], "context": {"country_code": "CO", "language": "spanish"},
             "data_request": {"include_all_purchase_options": True}}
        try:
            data = fetch(STEAM_API + urllib.parse.quote(json.dumps(q))) or {}
        except Exception:
            continue
        answered += 1
        for it in (data.get("response") or {}).get("store_items") or []:
            found[it.get("appid")] = it.get("best_purchase_option") or {}
    if ids and not answered:
        raise RuntimeError("Steam no respondió la verificación de precios para Colombia")
    out = []
    for o in offers:
        b = found.get(o.get("steamAppID")) or {}
        pct = _int(b.get("discount_pct"))  # Steam a veces manda los números como texto
        final, orig = _int(b.get("final_price_in_cents")), _int(b.get("original_price_in_cents"))
        if not pct or not final or not orig or final >= orig:
            continue
        end = next((d.get("discount_end_date") for d in b.get("active_discounts") or [] if d.get("discount_end_date")), None)
        now_cop, was_cop = round(final / 100), round(orig / 100)
        v = dict(o, currency="COP", currentPrice=now_cop, originalPrice=was_cop, discountPercentage=discount(was_cop, now_cop),
                 copApproximation=None, regions=["CO"], verifiedFor="CO")
        if end:
            v["expiresAt"] = datetime.fromtimestamp(int(end), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(v)
    return out


def verify_gog(offers, fetch, rate=None):
    """Confirma cada oferta de GOG en su catálogo para Colombia y la deja con la página exacta y el precio de allá."""
    out, answered = [], 0
    for o in offers:
        try:
            data = fetch(GOG_SEARCH.format(q=urllib.parse.quote(o["title"][:80]))) or {}
        except Exception:
            continue
        answered += 1
        want = norm(o["title"])
        p = next((x for x in data.get("products") or [] if norm(x.get("title")) == want), None)
        price = (p or {}).get("price") or {}
        final, base = _money((price.get("finalMoney") or {}).get("amount")), _money((price.get("baseMoney") or {}).get("amount"))
        link = (p or {}).get("storeLink") or ""
        if not p or not final or not base or final >= base or not link.startswith("https://www.gog.com/"):
            continue
        v = dict(o, currentPrice=final, originalPrice=base, discountPercentage=discount(base, final), officialUrl=link, destinationUrl=link,
                 regions=["CO"], verifiedFor="CO")
        if rate:
            v["copApproximation"] = round(final * rate)
        out.append(v)
    if offers and not answered:
        raise RuntimeError("GOG no respondió la verificación")
    return out


def run(offers, fetch, rate=None):
    """Devuelve (ofertas verificadas, texto de estado). Las de Epic (fuente propia) no pasan por aquí."""
    steam = verify_steam([o for o in offers if o.get("storeId") == "steam"], fetch)
    gog = verify_gog([o for o in offers if o.get("storeId") == "gog"], fetch, rate)
    dropped = {}
    for o in offers:
        if o.get("storeId") not in VERIFIED_STORES:
            dropped[o["store"]] = dropped.get(o["store"], 0) + 1
    n_steam = sum(1 for o in offers if o.get("storeId") == "steam")
    n_gog = sum(1 for o in offers if o.get("storeId") == "gog")
    text = (f"Steam: {len(steam)} de {n_steam} confirmadas para Colombia; GOG: {len(gog)} de {n_gog}"
            + ("; sin verificación (no se publican): " + ", ".join(f"{k} {v}" for k, v in sorted(dropped.items())) if dropped else ""))
    return steam + gog, text
