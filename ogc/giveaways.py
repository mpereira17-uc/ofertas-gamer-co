"""Regalos de juegos en todas las tiendas, con la API pública y gratuita de GamerPower.

https://www.gamerpower.com/api-read: no necesita clave y pide citar la fuente (el sitio la cita).
Trae lo que está gratis ahora en Steam, Epic, GOG, Amazon (Prime Gaming / Luna), itch.io y otras.
Solo se guarda lo que la fuente dice; los enlaces abren la página oficial del regalo (vía GamerPower).
"""

import re
from datetime import datetime, timedelta, timezone

API = "https://www.gamerpower.com/api/giveaways"
SOURCE_URL = "https://www.gamerpower.com/"
KEEP_DAYS = 14  # cuánto se recuerda un regalo ya terminado, para las Novedades

GROUPS = [  # (clave, nombre visible, palabras en el campo "platforms")
    ("steam", "Steam", ("steam",)),
    ("epic", "Epic Games", ("epic",)),
    ("gog", "GOG", ("gog",)),
    ("amazon", "Amazon Prime Gaming y Luna", ("prime", "amazon", "luna")),
    ("itch", "itch.io", ("itch",)),
    ("otros", "Otras tiendas y plataformas", ()),
]
TYPES = {"game": "Juego", "beta": "Beta o prueba", "early access": "Acceso anticipado"}


def clean_title(title):
    t = re.sub(r"\s*\([^)]*\)\s*giveaway\s*$", "", title or "", flags=re.I)
    t = re.sub(r"\s*(key\s+)?giveaway\s*$", "", t, flags=re.I)
    t = re.sub(r"\s+(on\s+)?(steam|epic games( store)?|gog|itch\.io|prime gaming|amazon luna)(\s+key)?\s*$", "", t, flags=re.I)
    return t.strip(" -–") or (title or "").strip()


def group_of(platforms):
    low = (platforms or "").lower()
    for key, _, words in GROUPS:
        if any(w in low for w in words):
            return key
    return "otros"


def parse_end(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def normalize(raw, now):
    """Convierte un regalo de GamerPower. Devuelve None si no sirve (vencido, tipo raro, sin enlace)."""
    kind = (raw.get("type") or "").strip().lower()
    url = raw.get("open_giveaway_url") or raw.get("open_giveaway") or ""
    if "gamerpower" in (raw.get("title") or "").lower():  # su propia app no es un regalo de juego
        return None
    if kind not in TYPES or not str(url).startswith("https://") or (raw.get("status") or "Active").lower() != "active":
        return None
    end = parse_end(raw.get("end_date"))
    if end and end < now:
        return None
    worth = raw.get("worth") or ""
    return {"id": f"gp-{raw.get('id')}", "title": clean_title(raw.get("title")), "type": kind,
            "group": group_of(raw.get("platforms")), "platforms": raw.get("platforms") or "",
            "worth": worth if re.fullmatch(r"\$\d+(\.\d+)?", worth) else "",
            "endsOn": end.strftime("%Y-%m-%d") if end else "",
            "image": raw.get("image") or raw.get("thumbnail") or "", "url": url}


def update(fetch, previous, now):
    """Devuelve (lista activa + recientes, texto de estado). Si la fuente falla, conserva lo anterior que siga vigente."""
    old = {g["id"]: g for g in previous}
    try:
        data = fetch(API)
        if not isinstance(data, list) or not data:
            raise ValueError("respuesta vacía")
    except Exception as exc:
        keep = [g for g in previous if g.get("active") and not (g.get("endsOn") and g["endsOn"] < now.strftime("%Y-%m-%d"))]
        return keep, f"falló ({type(exc).__name__}); se mantienen {len(keep)}"
    items, seen = [], set()
    for raw in data:
        g = normalize(raw, now)
        if not g or g["id"] in seen:
            continue
        seen.add(g["id"])
        g["firstSeen"] = old.get(g["id"], {}).get("firstSeen") or now.strftime("%Y-%m-%dT%H:%M:%SZ")
        g["active"] = True
        items.append(g)
    cutoff = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for gid, g in old.items():  # los que ya terminaron se recuerdan unos días para las Novedades
        if gid not in seen and (g.get("firstSeen") or "")[:10] >= cutoff:
            items.append(dict(g, active=False))
    active = sum(1 for g in items if g["active"])
    return items, f"OK, {active} regalos activos"
