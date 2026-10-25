"""Salud del sistema: fuentes caídas, enlaces rotos e informe mensual.

Cuando una fuente falla un día entero, se abre un aviso (issue) en GitHub, que le llega al dueño por correo;
cuando vuelve, se cierra solo. Una vez al mes se abre un informe con números reales del bot.
Usa el GITHUB_TOKEN que GitHub Actions da en cada ejecución (gratis, no hay que configurarlo).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import timedelta

from .channels import CO_TZ
from .model import iso, parse_iso

DOWN_RUNS = 6  # 6 ejecuciones seguidas = 24 horas
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def github(method, path, payload=None, env=os.environ):
    token, repo = env.get("GITHUB_TOKEN"), env.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return None
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}{path}", method=method,
                                 data=json.dumps(payload).encode() if payload is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "User-Agent": "ofertas-gamer-co-bot"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return json.loads(body) if body else {}
    except Exception as exc:  # nunca imprimir el token
        print(f"GitHub ({method} {path.split('?')[0]}) falló: {type(exc).__name__}", file=sys.stderr)
        return None


FOOTER = "\n\n---\n_Aviso automático de Ofertas Gamer CO._"


def track_sources(state, results, now, api=github):
    """results: {fuente: True si respondió bien}. Abre o cierra avisos. Devuelve el estado actualizado."""
    src = state.setdefault("sources", {})
    for name, ok in results.items():
        s = src.setdefault(name, {"fails": 0})
        if ok:
            if s.get("issue"):
                api("POST", f"/issues/{s['issue']}/comments", {"body": f"La fuente **{name}** volvió a responder el {iso(now)}." + FOOTER})
                api("PATCH", f"/issues/{s['issue']}", {"state": "closed", "state_reason": "completed"})
            src[name] = {"fails": 0, "lastOk": iso(now)}
            continue
        s["fails"] = s.get("fails", 0) + 1
        s.setdefault("since", iso(now))
        if s["fails"] >= DOWN_RUNS and not s.get("issue"):
            res = api("POST", "/issues", {"title": f"La fuente {name} no responde desde hace un día",
                                          "body": (f"La fuente **{name}** falló {s['fails']} revisiones seguidas (desde {s['since']}).\n\n"
                                                   "El sitio sigue funcionando con la última información válida, y se retiran las ofertas "
                                                   "vencidas. No tienes que hacer nada: este aviso se cierra solo cuando la fuente vuelva." + FOOTER)})
            if res and res.get("number"):
                s["issue"] = res["number"]
    return state


def check_links(state, offers, now, fetch_status, limit=30):
    """Una vez al día revisa que los enlaces oficiales abran. Solo 404/410 cuentan como rotos."""
    day = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
    if state.get("linksDay") == day:
        return state
    broken, checked = [], 0
    for o in offers:
        url = o.get("officialUrl") or ""
        if checked >= limit or "search" in url or "?" in url:
            continue
        checked += 1
        try:
            code = fetch_status(url)
        except Exception:
            code = None
        if code in (404, 410):
            broken.append({"id": o["id"], "title": o["title"], "url": url, "code": code})
    state.update(linksDay=day, linksChecked=checked, linksBroken=broken)
    return state


def head_status(url):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0 (ofertas-gamer-co link check)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def monthly_report(state, now, stats, api=github):
    """El primer día de cada mes (hora Colombia) abre un informe del mes anterior."""
    co = now.astimezone(CO_TZ)
    month = co.strftime("%Y-%m")
    if state.get("reportMonth") == month:
        return state
    if "reportMonth" not in state:  # la primera vez solo se marca el mes: el primer informe sale el mes siguiente
        state["reportMonth"] = month
        return state
    prev = (co.replace(day=1) - timedelta(days=1))
    name = f"{MESES[prev.month - 1]} de {prev.year}"
    lines = [f"Resumen automático de **{name}**:", ""] + [f"- {k}: **{v}**" for k, v in stats.items()] + [
        "", "Visitas: Cloudflare Pages → tu proyecto → Analytics (si activas Web Analytics, es gratis).",
        "No tienes que responder este informe; puedes cerrarlo cuando lo leas."]
    res = api("POST", "/issues", {"title": f"Informe de {name}", "body": "\n".join(lines) + FOOTER})
    if res is not None:
        state["reportMonth"] = month
    return state


def month_stats(now, history, epic_archive, weekly_history, alerts_status, offers):
    co = now.astimezone(CO_TZ)
    prev = co.replace(day=1) - timedelta(days=1)
    key = prev.strftime("%Y-%m")
    epic = [g for g in epic_archive.values() if (g.get("startsAt") or "")[:7] == key]
    weeks = [w for w in weekly_history if (w.get("date") or "")[:7] == key]
    seen = sum(1 for v in history.values() if any(p[0][:7] == key for p in v["points"]))
    return {"Juegos con precio seguido ese mes": seen, "Juegos gratis de Epic": len(epic),
            "Resúmenes semanales publicados": len(weeks), "Ofertas activas hoy": len(offers),
            "Alertas de Telegram": alerts_status or "sin datos"}
