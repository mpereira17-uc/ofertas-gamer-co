"""Calendario de lanzamientos: próximos y recientes de Steam, con la fecha que publica la tienda.

No se inventan fechas: si Steam no da un día exacto se muestra "por confirmar" o solo el mes.
"""

import re
import sys
from datetime import datetime, timedelta

from .model import iso, slugify

FEATURED_URL = "https://store.steampowered.com/api/featuredcategories?cc=co&l=english"
SEARCH_URL = "https://store.steampowered.com/search/results/?json=1&filter={filter}&count={count}&cc=co&l=english"
NON_GAMES = {"Utilidades", "Diseño e ilustración", "Edición de vídeo", "Edición de fotos", "Producción de audio",
             "Desarrollo web", "Formación", "Software de entrenamiento", "Animación y modelado"}
DETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={id}&cc=co&l=spanish"
DETAILS_DATE_URL = "https://store.steampowered.com/api/appdetails?appids={id}&cc=co&l=english&filters=release_date"
MAX_GAMES = 320
MAX_REFRESH = 70  # fichas de Steam consultadas por ejecución; el resto se reutiliza
REFRESH_HOURS = 24
RECENT_DAYS = 45  # los estrenos más viejos no son "recientes"

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


def search_ids(data):
    """Saca los appid de la búsqueda de Steam (el id viene dentro de la URL de la imagen)."""
    ids = []
    for item in (data or {}).get("items", []):
        m = re.search(r"/apps/(\d+)/", item.get("logo") or "")
        if m and int(m.group(1)) not in ids:
            ids.append(int(m.group(1)))
    return ids


def popular_ids(fetch):
    """Primero los más deseados, luego los que salen pronto y los estrenos populares; si la búsqueda falla, las listas destacadas."""
    ids = []
    # popularwishlist = los más deseados (los juegos grandes que aún no salen); popularcomingsoon = los que salen pronto
    for flt, count, start in (("popularwishlist", 100, 0), ("popularwishlist", 100, 100), ("popularcomingsoon", 100, 0),
                              ("popularcomingsoon", 100, 100), ("popularnew", 50, 0)):
        try:
            url = SEARCH_URL.format(filter=flt, count=count) + f"&start={start}"
            ids += [i for i in search_ids(fetch(url)) if i not in ids]
        except Exception as exc:
            print(f"Lanzamientos: búsqueda {flt} desde {start} falló: {exc}", file=sys.stderr)
    if len(ids) < 10:
        ids += [i for i in steam_ids(fetch(FEATURED_URL)) if i not in ids]
    return ids[:MAX_GAMES]


F2P_URL = "https://store.steampowered.com/search/results/?json=1&filter=topsellers&maxprice=free&category1=998&count=48&cc=co&l=spanish"


def free_to_play(fetch, previous=()):
    """Los juegos gratis para siempre más jugados/vendidos en Steam (búsqueda oficial). Si falla, se conserva la lista.
    La portada sale de la ficha oficial (header_image): los juegos nuevos de Steam ya no tienen la ruta fija header.jpg."""
    cache = {g["id"]: g for g in previous if g.get("headerChecked") and "genres" in g}
    try:
        games, asked = [], 0
        for item in (fetch(F2P_URL) or {}).get("items", []):
            logo = item.get("logo") or ""
            m = re.search(r"/apps/(\d+)/", logo)
            name = (item.get("name") or "").strip()
            if not (m and name):
                continue
            app = m.group(1)
            game = {"id": f"steam-{app}", "title": name, "url": f"https://store.steampowered.com/app/{app}/",
                    "image": "", "imageSmall": logo if logo.startswith("https://") else ""}
            old = cache.get(game["id"])
            if old:
                game["image"], game["headerChecked"], game["genres"] = old.get("image") or "", True, old["genres"]
            elif asked < 45:
                asked += 1
                try:
                    data = (fetch(DETAILS_URL.format(id=app)) or {}).get(app) or {}
                    info = (data.get("data") or {}) if data.get("success") else {}
                    header = info.get("header_image") or ""
                    game["image"], game["headerChecked"] = (header if header.startswith("https://") else ""), True
                    game["genres"] = [g["description"] for g in info.get("genres") or [] if g.get("description")
                                      and g["description"] not in ("Free To Play", "Free to Play", "Gratuito", "Gratis")][:3]
                except Exception as exc:
                    print(f"Gratis para siempre: ficha {app} falló: {type(exc).__name__}", file=sys.stderr)
            game["image"] = game["image"] or game["imageSmall"]
            if game["image"]:
                games.append(game)
        if len(games) < 5:
            raise ValueError("muy pocos juegos")
        return games[:40], f"OK, {len(games[:40])} juegos"
    except Exception as exc:
        print(f"Gratis para siempre: Steam falló: {exc}", file=sys.stderr)
        return list(previous), f"Falló ({type(exc).__name__}); se conserva la lista anterior"


def steam_trailer(info):
    """El primer tráiler oficial de la ficha de Steam (video y miniatura), o {} si no hay."""
    for movie in info.get("movies") or []:
        poster = movie.get("thumbnail") or ""
        video = ""
        for kind in ("mp4", "webm"):
            files = movie.get(kind) or {}
            video = files.get("max") or files.get("480") or ""
            if video:
                break
        hls = movie.get("hls_h264") or ""
        video = video.replace("http://", "https://")
        if video.startswith("https://") or hls.startswith("https://"):
            return {"name": (movie.get("name") or "")[:120], "poster": poster if poster.startswith("https://") else "",
                    "video": video if video.startswith("https://") else "", "hls": hls if hls.startswith("https://") else ""}
    return {}


def steam_game(app_id, now, fetch):
    """Ficha de un juego en Steam, o None si no es un juego o no hay datos."""
    data = (fetch(DETAILS_URL.format(id=app_id)) or {}).get(str(app_id)) or {}
    dates = (fetch(DETAILS_DATE_URL.format(id=app_id)) or {}).get(str(app_id)) or {}
    info = data.get("data") if data.get("success") else None
    if not info or info.get("type") != "game":
        return None
    if NON_GAMES & {g.get("description") for g in info.get("genres") or []}:
        return None
    raw = ((dates.get("data") or {}).get("release_date") or {}).get("date") or ""
    date, precision = parse_release(raw)
    image = info.get("header_image") or ""
    platforms = [n for k, n in (("windows", "Windows"), ("mac", "Mac"), ("linux", "Linux"))
                 if (info.get("platforms") or {}).get(k)]
    title = info.get("name", "").strip()
    if not title:
        return None
    return {
        "id": f"steam-{app_id}",
        "slug": slugify(title),
        "title": title,
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
        "trailer": steam_trailer(info),
        "shots": [x["path_thumbnail"] for x in info.get("screenshots") or [] if (x.get("path_thumbnail") or "").startswith("https://")][:6],
        "spanish": "español" in (info.get("supported_languages") or "").lower() or "spanish" in (info.get("supported_languages") or "").lower(),
        "requirements": requirements_text(info),
    }


def requirements_text(info):
    """Requisitos mínimos de PC como texto simple (sin HTML), tal como los publica Steam."""
    req = info.get("pc_requirements") or {}
    raw = req.get("minimum") if isinstance(req, dict) else ""
    text = re.sub(r"<br\s*/?>|</li>", "\n", raw or "")
    text = re.sub(r"<[^>]+>", "", text)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and ln.lower().rstrip(":") not in ("mínimo", "minimum", "requisitos mínimos")]
    return "\n".join(lines)[:700]


def steam_releases(now, fetch, previous=()):
    cache = {g["id"]: g for g in previous if g.get("id")}
    fresh_after = iso(now - timedelta(hours=REFRESH_HOURS))
    oldest = (now - timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%d")
    games, refreshed = [], 0
    for app_id in popular_ids(fetch):
        cached = cache.get(f"steam-{app_id}")
        # una ficha vieja sin el campo trailer se vuelve a pedir (así llegan los tráileres, primero los más populares)
        game = cached if cached and "shots" in cached and (cached.get("verifiedAt") or "") >= fresh_after else None
        if game is None and refreshed < MAX_REFRESH:
            refreshed += 1
            try:
                game = steam_game(app_id, now, fetch)
            except Exception as exc:  # un juego que falla no tumba el calendario
                print(f"Lanzamientos: Steam {app_id} falló: {exc}", file=sys.stderr)
                game = cached
        elif game is None:
            game = cached  # se actualizará en una próxima ejecución
        if game and not (game.get("date") and game["date"] < oldest):
            games.append(dict(game, rank=len(games) + 1))  # 1 = el más popular/esperado en Steam
    return games


def mark_date_changes(games, previous, now, keep_days=45):
    """Marca los juegos cuya fecha publicada cambió (retrasos o adelantos). La marca dura unas semanas."""
    old = {g["id"]: g for g in previous}
    cutoff = iso(now - timedelta(days=keep_days))
    out = []
    for g in games:
        prev = old.get(g["id"]) or {}
        change = prev.get("dateChanged")
        if prev and prev.get("date") and g.get("date") != prev.get("date"):
            change = {"from": prev["date"], "fromPrecision": prev.get("precision"), "at": iso(now)}
        if change and (change.get("at") or "") >= cutoff and change.get("from") != g.get("date"):
            g = dict(g, dateChanged=change)
        else:
            g = {k: v for k, v in g.items() if k != "dateChanged"}
        out.append(g)
    return out


def update(previous, now, fetch):
    """Devuelve (juegos, estado). Si Steam falla se conserva la última versión válida."""
    try:
        games = steam_releases(now, fetch, previous)
        if not games:
            raise ValueError("Steam no devolvió juegos")
        return games, f"OK, {len(games)} juegos"
    except Exception as exc:
        print(f"Lanzamientos: Steam falló: {exc}", file=sys.stderr)
        return previous, f"Falló ({type(exc).__name__}); se conserva la última versión válida"
