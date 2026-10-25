"""Calendario de lanzamientos: próximos y recientes de Steam, con la fecha que publica la tienda.

No se inventan fechas: si Steam no da un día exacto se muestra "por confirmar" o solo el mes.
"""

import re
import sys
from datetime import datetime

from .model import iso, slugify

FEATURED_URL = "https://store.steampowered.com/api/featuredcategories?cc=co&l=english"
DETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={id}&cc=co&l=spanish"
DETAILS_DATE_URL = "https://store.steampowered.com/api/appdetails?appids={id}&cc=co&l=english&filters=release_date"
MAX_GAMES = 40

MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DAY_FORMATS = ("%d %b, %Y", "%b %d, %Y", "%d %B, %Y", "%B %d, %Y", "%d %b %Y", "%b %d %Y")
MONTH_FORMATS = ("%B %Y", "%b %Y")


def parse_release(text):
    """Convierte la fecha de Steam en (AAAA-MM-DD, precisión). Precisión: 'day', 'month' o None."""
    text = (text or "").strip().replace(".", "")
    for fmt in DAY_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d"), "day"
        except ValueError:
            pass
    for fmt in MONTH_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-01"), "month"
        except ValueError:
            pass
    return None, None


def date_label(date, precision):
    if not date:
        return "Fecha por confirmar"
    d = datetime.strptime(date, "%Y-%m-%d")
    if precision == "month":
        return f"{MONTHS_ES[d.month - 1].capitalize()} de {d.year}"
    return f"{DAYS_ES[d.weekday()].capitalize()} {d.day} de {MONTHS_ES[d.month - 1]} de {d.year}"


def relative_label(date, precision, now):
    if not date or precision != "day":
        return ""
    days = (datetime.strptime(date, "%Y-%m-%d").date() - now.date()).days
    if days == 0:
        return "hoy"
    if days == 1:
        return "mañana"
    if days == -1:
        return "ayer"
    return f"en {days} días" if days > 0 else f"hace {-days} días"


def steam_ids(featured):
    ids = []
    for key in ("coming_soon", "new_releases"):
        for item in (featured.get(key) or {}).get("items", []):
            if isinstance(item.get("id"), int) and item["id"] not in ids:
                ids.append(item["id"])
    return ids[:MAX_GAMES]


def steam_releases(now, fetch):
    featured = fetch(FEATURED_URL)
    games = []
    for app_id in steam_ids(featured):
        try:
            data = (fetch(DETAILS_URL.format(id=app_id)) or {}).get(str(app_id)) or {}
            dates = (fetch(DETAILS_DATE_URL.format(id=app_id)) or {}).get(str(app_id)) or {}
        except Exception as exc:  # un juego que falla no tumba el calendario
            print(f"Lanzamientos: Steam {app_id} falló: {exc}", file=sys.stderr)
            continue
        info = data.get("data") if data.get("success") else None
        if not info or info.get("type") != "game":
            continue
        raw = ((dates.get("data") or {}).get("release_date") or {}).get("date") or ""
        date, precision = parse_release(raw)
        image = info.get("header_image") or ""
        platforms = [n for k, n in (("windows", "Windows"), ("mac", "Mac"), ("linux", "Linux"))
                     if (info.get("platforms") or {}).get(k)]
        games.append({
            "id": f"steam-{app_id}",
            "slug": slugify(info.get("name", "")),
            "title": info.get("name", "").strip(),
            "description": re.sub(r"<[^>]+>", "", info.get("short_description") or "").strip(),
            "store": "Steam",
            "url": f"https://store.steampowered.com/app/{app_id}/",
            "image": image if image.startswith("https://") else "",
            "platforms": platforms or ["Windows"],
            "genres": [g["description"] for g in info.get("genres") or [] if g.get("description")][:3],
            "releaseText": raw,
            "date": date,
            "precision": precision,
            "comingSoon": bool((info.get("release_date") or {}).get("coming_soon")),
            "verifiedAt": iso(now),
        })
    return [g for g in games if g["title"]]


def update(previous, now, fetch):
    """Devuelve (juegos, estado). Si Steam falla se conserva la última versión válida."""
    try:
        games = steam_releases(now, fetch)
        if not games:
            raise ValueError("Steam no devolvió juegos")
        return games, f"OK, {len(games)} juegos"
    except Exception as exc:
        print(f"Lanzamientos: Steam falló: {exc}", file=sys.stderr)
        return previous, f"Falló ({type(exc).__name__}); se conserva la última versión válida"
