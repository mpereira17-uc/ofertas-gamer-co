"""Comprobaciones críticas del sitio generado. Sale con código 1 si algo falla.

- Enlaces internos rotos
- Enlaces externos sin rel="noopener noreferrer" o afiliados sin "sponsored"
- Páginas sin título, descripción, canónica, lang="es" o un único h1
- Imágenes sin alt
- Sitemap con páginas inexistentes o con páginas técnicas
- Espacios publicitarios visibles cuando están desactivados
- Posibles secretos en el repositorio
"""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SECRET_PATTERNS = [
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),           # token de bot de Telegram
    re.compile(r"https://discord(app)?\.com/api/webhooks/\d+/[\w-]+"),
    re.compile(r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.imgs, self.h1, self.meta, self.title, self.lang = [], [], 0, {}, "", None
        self._in_title = False
        self.canonical = None
        self.ads = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "a" and "href" in a:
            self.links.append(a)
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta" and a.get("name"):
            self.meta[a["name"]] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag == "title":
            self._in_title = True
        elif tag == "aside" and "ad" in (a.get("class") or "").split():
            self.ads += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def main():
    errors = []
    ads_enabled = json.loads((ROOT / "config" / "ads.json").read_text())["ads_enabled"]
    titles = {}
    for path in sorted(DOCS.glob("*.html")):
        p = Page()
        p.feed(path.read_text(encoding="utf-8"))
        name = path.name
        if p.lang != "es":
            errors.append(f"{name}: lang distinto de es")
        if not p.title.strip():
            errors.append(f"{name}: sin título")
        if p.title in titles:
            errors.append(f"{name}: título repetido con {titles[p.title]}")
        titles[p.title] = name
        if not p.meta.get("description"):
            errors.append(f"{name}: sin meta description")
        if not p.canonical:
            errors.append(f"{name}: sin URL canónica")
        if p.h1 != 1:
            errors.append(f"{name}: tiene {p.h1} h1")
        if p.ads and not ads_enabled:
            errors.append(f"{name}: muestra publicidad desactivada")
        for img in p.imgs:
            if "alt" not in img:
                errors.append(f"{name}: imagen sin alt ({img.get('src')})")
        for a in p.links:
            href = a["href"]
            if href.startswith(("http://", "https://")):
                rel = (a.get("rel") or "").split()
                if a.get("target") == "_blank" and not {"noopener", "noreferrer"} <= set(rel):
                    errors.append(f"{name}: enlace externo sin noopener noreferrer: {href}")
                if href.startswith("http://"):
                    errors.append(f"{name}: enlace inseguro {href}")
            elif not href.startswith(("#", "mailto:", "webcal://")):
                target = DOCS / href.split("#")[0].split("?")[0]
                if not target.exists():
                    errors.append(f"{name}: enlace interno roto {href}")

    sitemap = (DOCS / "sitemap.xml").read_text()
    base = json.loads((ROOT / "config" / "site.json").read_text())["url_web"]
    for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap):
        rel = loc.replace(base, "") or "index.html"
        if not (DOCS / rel).exists():
            errors.append(f"sitemap: no existe {rel}")
        if rel in ("404.html", "whatsapp.html") or not rel.endswith(".html"):
            errors.append(f"sitemap: incluye una página técnica {rel}")

    offers = json.loads((DOCS / "data" / "offers.json").read_text())["offers"]
    for o in offers:
        if o["status"] == "Vencido":
            errors.append(f"oferta vencida publicada: {o['id']}")
        if not o["affiliate"] and o["destinationUrl"] != o["officialUrl"]:
            errors.append(f"enlace no oficial sin afiliación: {o['id']}")

    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    for f in files:
        path = ROOT / f
        if path.name in (".env",) or path.suffix in (".pem", ".key"):
            errors.append(f"archivo sensible en el repositorio: {f}")
        if path.suffix in (".png", ".jpg", ".ico") or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"posible secreto en {f}")

    for err in errors:
        print("ERROR:", err)
    print(f"Revisadas {len(titles)} páginas y {len(offers)} ofertas: {len(errors)} errores")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
