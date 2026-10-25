"""Monitoreo: el sitio responde, offers.json existe y la última actualización es reciente."""

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config" / "site.json").read_text())
base = cfg["url_web"].rstrip("/") + "/"
limit = timedelta(hours=cfg["intervalo_horas"] * 3)
problems = []


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ofertas-gamer-co-monitor"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read()


for page in ("", "ofertas.html", "juegos-gratis.html", "privacidad.html", "afiliados.html"):
    try:
        status, _ = get(base + page)
        if status != 200:
            problems.append(f"{page or 'inicio'} respondió {status}")
    except Exception as exc:
        problems.append(f"{page or 'inicio'} no responde: {type(exc).__name__}")

try:
    _, body = get(base + "data/offers.json")
    data = json.loads(body)
    updated = datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - updated > limit:
        problems.append(f"la última actualización es del {data['updatedAt']}")
    if not data["offers"]:
        problems.append("offers.json no tiene ofertas")
except Exception as exc:
    problems.append(f"offers.json no se pudo leer: {type(exc).__name__}")

for p in problems:
    print("PROBLEMA:", p)
print("Monitoreo OK" if not problems else f"{len(problems)} problemas")
sys.exit(1 if problems else 0)
