"""Tráileres y capturas de Steam para las ofertas: avance al pasar el cursor y fotos en la página de cada oferta.

Se usan los tráileres que ya trae el calendario y, para el resto, la ficha pública de Steam (sin clave).
Se guardan en data/trailers.json y se piden pocos por corrida para no abusar de Steam.
"""

import html
import re
import sys
from datetime import timedelta

from .model import iso
from .releases import DETAILS_URL, steam_trailer

MAX_NEW = 100  # fichas nuevas por corrida
KEEP_DAYS = 30  # un tráiler se vuelve a revisar al mes


HEAD_RE = re.compile(r"^(?:configuraci[oó]n\s+)?(m[ií]nim[oa]s?|recomendad[oa]s?)\s*:?\s*", re.I)


def _req_lines(raw):
    """HTML de requisitos de Steam -> líneas de texto plano (sin etiquetas ni scripts)."""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw or "")
    text = re.sub(r"(?i)<br\s*/?>|</li>|</p>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    out = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip(" -•\t")
        line = HEAD_RE.sub("", line).strip()
        if line and len(line) > 2:
            out.append(line[:180])
    return out[:10]


def requirements(info):
    """Requisitos de PC (mínimos y recomendados) de la ficha de Steam, como listas de texto plano."""
    pc = (info or {}).get("pc_requirements")
    if not isinstance(pc, dict):
        return None
    mins, recs = pc.get("minimum") or "", pc.get("recommended") or ""
    # algunas fichas traen todo en «minimum», con el título «recomendada» en medio
    split = re.split(r"(?i)<strong>\s*(?:configuraci[oó]n\s+)?recomendad[oa]s?\s*:?\s*</strong>", mins, maxsplit=1)
    if len(split) == 2 and not recs:
        mins, recs = split[0], split[1]
    r = {"min": _req_lines(mins), "rec": _req_lines(recs)}
    return r if r["min"] or r["rec"] else None


def update(offers, games, cache, now, fetch):
    """Devuelve (caché nueva, estado). cache = {appid: {"trailer": {...}, "at": iso}}."""
    cache = dict(cache or {})
    for g in games or []:
        if g.get("id", "").startswith("steam-") and g.get("trailer"):
            cache[g["id"][6:]] = {"trailer": g["trailer"], "shots": g.get("shots") or [], "about": g.get("description") or "",
                                  "reqs": (cache.get(g["id"][6:]) or {}).get("reqs"),
                                  "at": g.get("verifiedAt") or iso(now)}
    stale = iso(now - timedelta(days=KEEP_DAYS))
    wanted = []
    for o in offers:
        app = str(o.get("steamAppID") or "")
        # las fichas guardadas antes sin capturas o sin descripción se vuelven a pedir una vez
        if app and app not in wanted and (app not in cache or (cache[app].get("at") or "") < stale or "reqs" not in cache[app]):
            wanted.append(app)
    asked = failed = 0
    for app in wanted[:MAX_NEW]:
        asked += 1
        try:
            entry = (fetch(DETAILS_URL.format(id=app)) or {}).get(app) or {}
            info = entry.get("data") if entry.get("success") else None
            ok = isinstance(info, dict)
            shots = [x["path_thumbnail"] for x in (info.get("screenshots") or []) if (x.get("path_thumbnail") or "").startswith("https://")][:6] if ok else []
            about = re.sub(r"<[^>]+>", "", info.get("short_description") or "").strip()[:400] if ok else ""
            cache[app] = {"trailer": steam_trailer(info) if ok else {}, "shots": shots, "about": about,
                          "reqs": requirements(info) if ok else None, "at": iso(now)}
        except Exception as exc:  # un juego que falla no tumba nada; se reintenta en otra corrida
            failed += 1
            print(f"Tráileres: Steam {app} falló: {exc}", file=sys.stderr)
    live = {str(o.get("steamAppID")) for o in offers if o.get("steamAppID")}
    cache = {k: v for k, v in cache.items() if k in live or any(g.get("id") == f"steam-{k}" for g in games or [])}
    have = sum(1 for o in offers if (cache.get(str(o.get("steamAppID") or "")) or {}).get("trailer"))
    return cache, f"OK, {have} ofertas con tráiler; {asked} fichas pedidas{f', {failed} fallaron' if failed else ''}"


def attach(offers, cache):
    """Pone en cada oferta su tráiler (si lo hay) para que la página lo muestre."""
    for o in offers:
        entry = cache.get(str(o.get("steamAppID") or "")) or {}
        t = entry.get("trailer")
        if t and (t.get("hls") or t.get("video")):
            o["trailer"] = t
        if entry.get("shots"):
            o["shots"] = entry["shots"]
        if entry.get("about"):
            o["about"] = entry["about"]
        if entry.get("reqs"):
            o["reqs"] = entry["reqs"]  # requisitos de PC de la ficha de Steam  # descripción corta oficial de la ficha de Steam (en español)
    return offers
