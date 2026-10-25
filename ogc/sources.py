"""Fuentes autorizadas de ofertas. Solo APIs públicas, con reintentos y espera progresiva."""

import json
import sys
import time
import urllib.parse
import urllib.request

from .affiliates import build_destination
from .model import compute_status, discount, iso, slugify

USER_AGENT = "ofertas-gamer-co/2.0 (+https://github.com/mpereira17-uc/ofertas-gamer-co)"
EPIC_URL = ("https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
            "?locale=es-ES&country=CO&allowCountries=CO")
CHEAPSHARK_URL = "https://www.cheapshark.com/api/1.0/deals?"
RATE_URL = "https://open.er-api.com/v6/latest/USD"


def get_json(url, attempts=3):
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as exc:
            if attempt == attempts - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(f"Reintento en {wait}s ({host_of(url)}): {exc}", file=sys.stderr)
            time.sleep(wait)


def host_of(url):
    return urllib.parse.urlparse(url).hostname


def usd_to_cop():
    """Devuelve (tasa, fecha) o (None, None). Sin tasa confiable no se muestran pesos."""
    try:
        data = get_json(RATE_URL)
        rate = float(data["rates"]["COP"])
        if data.get("result") not in (None, "success") or not 1000 < rate < 20000:
            raise ValueError(f"tasa sospechosa: {rate}")
        return rate, data.get("time_last_update_utc")
    except Exception as exc:
        print(f"Sin tasa de cambio confiable ({exc}); no se mostrarán pesos", file=sys.stderr)
        return None, None


def cop(amount, currency, rate):
    if amount is None:
        return None
    if currency == "COP":
        return round(amount)
    if currency == "USD" and rate:
        return int(round(amount * rate / 100) * 100)
    return None


def make_offer(*, oid, title, store, official_url, image, original, current, currency, rate, now, cfg,
               source, starts=None, expires=None, platform="PC", drm=None, regions=None, tags=None,
               description=""):
    destination, affiliate, network = build_destination(official_url, store)
    offer = {
        "id": oid,
        "slug": slugify(title),
        "title": title.strip(),
        "description": description,
        "store": store["name"],
        "storeId": store["id"],
        "platform": platform,
        "operatingSystem": None,
        "drm": drm,
        "regions": regions or [],
        "originalPrice": original,
        "currentPrice": current,
        "currency": currency,
        "copApproximation": cop(current, currency, rate) if currency != "COP" else None,
        "discountPercentage": discount(original, current),
        "image": image if image and image.startswith("https://") else "",
        "officialUrl": official_url,
        "destinationUrl": destination,
        "affiliateNetwork": network,
        "affiliate": affiliate,
        "sponsored": False,
        "startsAt": starts,
        "expiresAt": expires,
        "verifiedAt": iso(now),
        "source": source,
        "sourceType": "api",
        "status": "Disponible",
        "tags": tags or [],
        "telegramPublishedAt": None,
        "createdAt": iso(now),
        "updatedAt": iso(now),
    }
    offer["status"] = compute_status(offer, now, cfg.get("dias_proximo_a_vencer", 2))
    return offer


def epic_free_games(stores, rate, now, cfg, fetch=get_json):
    store = stores["epic"]
    offers = []
    for el in fetch(EPIC_URL)["data"]["Catalog"]["searchStore"]["elements"]:
        promos = (el.get("promotions") or {}).get("promotionalOffers") or []
        free_now = [o for p in promos for o in p.get("promotionalOffers", [])
                    if o["discountSetting"]["discountPercentage"] == 0]
        total = el["price"]["totalPrice"]
        if not free_now or total["discountPrice"] != 0:
            continue
        slug = el.get("productSlug") or ""
        mappings = (el.get("catalogNs") or {}).get("mappings") or el.get("offerMappings") or []
        if mappings:
            slug = mappings[0].get("pageSlug") or slug
        slug = slug.split("/")[0]
        url = f"https://store.epicgames.com/es-ES/p/{slug}" if slug else "https://store.epicgames.com/es-ES/free-games"
        decimals = (total.get("currencyInfo") or {}).get("decimals", 2)
        currency = total.get("currencyCode") or "USD"
        original = total["originalPrice"] / 10 ** decimals if total.get("originalPrice") else None
        image = next((i["url"] for i in el.get("keyImages", [])
                      if i["type"] in ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail")), "")
        offers.append(make_offer(
            oid=f"epic-{el['id']}-{free_now[0]['endDate'][:10]}", title=el["title"], store=store,
            official_url=url, image=image, original=original, current=0, currency=currency, rate=rate,
            now=now, cfg=cfg, source="epic", starts=free_now[0].get("startDate"),
            expires=free_now[0].get("endDate"), drm="Epic Games Store", regions=["CO"], tags=["gratis"],
            description=(el.get("description") or "")[:300]))
    return offers


def cheapshark_deals(stores, rate, now, cfg, fetch=get_json):
    by_cs = {s["cheapsharkId"]: s for s in stores.values() if s.get("cheapsharkId") and s.get("active")}
    f = cfg["filtros_ofertas"]
    params = {"storeID": ",".join(by_cs), "sortBy": "Deal Rating", "pageSize": 60,
              "upperPrice": f["precio_maximo_usd"], "metacritic": f.get("metacritic_minimo", 0), "onSale": 1}
    deals, seen = [], set()
    for page in range(f.get("paginas_cheapshark", 1)):
        try:
            batch = fetch(CHEAPSHARK_URL + urllib.parse.urlencode(dict(params, pageNumber=page)))
        except Exception:
            if page == 0:
                raise  # sin la primera página la fuente cuenta como caída
            break
        for d in batch:
            key = d.get("dealID") or (d.get("gameID"), d.get("storeID"))
            if key not in seen:
                seen.add(key)
                deals.append(d)
        if len(batch) < params["pageSize"]:
            break
    offers = []
    for d in deals:
        store = by_cs.get(d.get("storeID"))
        if not store or float(d["savings"]) < f["descuento_minimo"]:
            continue
        if store["id"] == "steam" and d.get("steamAppID"):
            url = store["productUrl"].format(steamAppID=d["steamAppID"])
        else:
            url = store["searchUrl"].format(query=urllib.parse.quote(d["title"]))
        offers.append(make_offer(
            oid=f"cs-{d['gameID']}-{d['storeID']}-{d['salePrice']}", title=d["title"], store=store,
            official_url=url, image=d.get("thumb", ""), original=float(d["normalPrice"]),
            current=float(d["salePrice"]), currency="USD", rate=rate, now=now, cfg=cfg, source="cheapshark",
            drm="Steam" if store["id"] == "steam" else None,
            tags=["descuento"] + (["metacritic-" + d["metacriticScore"]] if d.get("metacriticScore") not in (None, "0") else [])))
        offers[-1]["metacritic"] = int(d["metacriticScore"]) if str(d.get("metacriticScore") or "0").isdigit() else 0
    return offers
