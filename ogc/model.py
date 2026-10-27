"""Modelo de datos de una oferta, validación y combinación con la versión anterior."""

import re
import unicodedata
import urllib.parse
from datetime import datetime, timedelta, timezone

FIELDS = [
    "id", "slug", "title", "description", "store", "storeId", "platform", "operatingSystem", "drm",
    "regions", "originalPrice", "currentPrice", "currency", "copApproximation", "discountPercentage",
    "image", "officialUrl", "destinationUrl", "affiliateNetwork", "affiliate", "sponsored", "startsAt",
    "expiresAt", "verifiedAt", "source", "sourceType", "status", "tags", "telegramPublishedAt",
    "createdAt", "updatedAt", "metacritic", "imageSmall", "otherStores", "steamAppID", "trailer",
]
REQUIRED = ["id", "title", "store", "storeId", "officialUrl", "destinationUrl", "currency", "verifiedAt", "source"]
STATUSES = {"Disponible", "Gratuito", "Próximo a vencer", "Vencido", "Pendiente de verificación",
            "No disponible para Colombia"}


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80] or "oferta"


def host(url):
    return urllib.parse.urlparse(url).hostname or ""


def https_url(url):
    parsed = urllib.parse.urlparse(url or "")
    return parsed.scheme == "https" and bool(parsed.hostname)


def discount(original, current):
    """Solo calcula el descuento con datos completos y coherentes."""
    if original is None or current is None or original <= 0 or current < 0 or current > original:
        return None
    return round((1 - current / original) * 100)


def compute_status(offer, now, soon_days):
    expires = parse_iso(offer.get("expiresAt"))
    if expires and expires <= now:
        return "Vencido"
    if expires and expires - now <= timedelta(days=soon_days):
        return "Próximo a vencer"
    if offer.get("currentPrice") == 0:
        return "Gratuito"
    return "Disponible"


def validate(offer, stores_by_id):
    """Devuelve la lista de errores. Una oferta con errores no se publica."""
    errors = []
    for field in REQUIRED:
        if offer.get(field) in (None, ""):
            errors.append(f"falta {field}")
    store = stores_by_id.get(offer.get("storeId"))
    if not store or not store.get("active"):
        errors.append("tienda no autorizada")
    if not https_url(offer.get("officialUrl")):
        errors.append("officialUrl no es HTTPS")
    elif store and host(offer["officialUrl"]) not in store["domains"]:
        errors.append(f"dominio no autorizado: {host(offer['officialUrl'])}")
    if not https_url(offer.get("destinationUrl")):
        errors.append("destinationUrl no es HTTPS")
    elif not offer.get("affiliate") and offer.get("destinationUrl") != offer.get("officialUrl"):
        errors.append("enlace distinto del oficial sin afiliación aprobada")
    if offer.get("image") and not https_url(offer["image"]):
        errors.append("imagen no HTTPS")
    for price in ("originalPrice", "currentPrice"):
        value = offer.get(price)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            errors.append(f"{price} inválido")
    if offer.get("discountPercentage") is not None and \
            offer["discountPercentage"] != discount(offer.get("originalPrice"), offer.get("currentPrice")):
        errors.append("descuento no coincide con los precios")
    if offer.get("status") not in STATUSES:
        errors.append("estado inválido")
    unknown = set(offer) - set(FIELDS)
    if unknown:
        errors.append(f"campos desconocidos: {sorted(unknown)}")
    return errors


def merge(previous, fresh_by_source, failed_sources, now, cfg):
    """Combina las ofertas nuevas con las anteriores.

    - Una fuente que respondió bien reemplaza sus ofertas anteriores.
    - Una fuente que falló conserva sus ofertas anteriores durante un tiempo limitado, para no
      vaciar la página por un error temporal.
    - Se conservan createdAt y telegramPublishedAt de cada oferta ya conocida.
    """
    prev_by_id = {o["id"]: o for o in previous}
    keep_until = now - timedelta(hours=cfg.get("horas_retener_oferta_sin_confirmar", 24))
    result = []
    for source, offers in fresh_by_source.items():
        for offer in offers:
            old = prev_by_id.get(offer["id"])
            if old:
                offer["createdAt"] = old.get("createdAt") or offer["createdAt"]
                offer["telegramPublishedAt"] = old.get("telegramPublishedAt")
            result.append(offer)
    for old in previous:
        if old.get("source") in failed_sources and (parse_iso(old.get("verifiedAt")) or now) >= keep_until:
            result.append(old)
    return result


def dedupe(offers):
    """Una sola oferta por juego: gana la gratuita y luego el mayor descuento."""
    offers = sorted(offers, key=lambda o: (o.get("currentPrice") != 0, -(o.get("discountPercentage") or 0)))
    seen, unique, winner = set(), [], {}
    for offer in offers:
        key = slugify(offer["title"])
        if offer["id"] in seen:
            continue
        if key in seen:  # el mismo juego en otra tienda: se guarda para "Compara tiendas"
            if offer["storeId"] != winner[key]["storeId"] and not any(x["storeId"] == offer["storeId"] for x in winner[key]["otherStores"]):
                winner[key]["otherStores"].append({k: offer.get(k) for k in ALT_FIELDS})
            continue
        seen.update({offer["id"], key})
        offer = dict(offer, otherStores=[])
        winner[key] = offer
        unique.append(offer)
    return unique


ALT_FIELDS = ("id", "title", "store", "storeId", "currentPrice", "originalPrice", "currency", "discountPercentage",
              "copApproximation", "destinationUrl", "officialUrl", "affiliate", "image", "verifiedAt")
