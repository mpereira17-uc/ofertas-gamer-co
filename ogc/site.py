"""Genera el sitio estático (docs/), los feeds, el sitemap y el resumen de WhatsApp."""

import hashlib
import html
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import quote, urlencode
from pathlib import Path

from . import giveaways
from .channels import CO_TZ, co_time, cop_text, date_es, money, time_left
from .content import FAQ, GLOSSARY, GUIDES, LEGAL_REVIEW, LEGAL_UPDATED
from .model import parse_iso
from .releases import date_label, relative_label, MONTHS_ES

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
REPO = "https://github.com/mpereira17-uc/ofertas-gamer-co"
DISCLOSURE = ("Algunos enlaces publicados pueden ser enlaces de afiliados. Si realizas una compra mediante "
              "ellos podemos recibir una comisión sin costo adicional para ti.")

_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>'
ICONS = {k: _SVG.format(v) for k, v in {
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    "gift": '<rect x="3" y="8" width="18" height="13" rx="2"/><path d="M12 8v13M3 12h18M12 8S10 3 7.5 4.5 9 8 12 8zm0 0s2-5 4.5-3.5S15 8 12 8z"/>',
    "flame": '<path d="M12 22c4 0 7-3 7-7 0-5-4-7-5-12-3 3-4 5-4 8-1-1-2-2-2-4-2 2-3 5-3 8 0 4 3 7 7 7z"/>',
    "news": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "dice": '<rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="9" cy="9" r="1.2"/><circle cx="15" cy="15" r="1.2"/><circle cx="15" cy="9" r="1.2"/><circle cx="9" cy="15" r="1.2"/>',
    "quiz": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01"/>',
    "thermo": '<path d="M10 14.5V5a2 2 0 1 1 4 0v9.5a4 4 0 1 1-4 0z"/><path d="M12 9v7"/>',
    "sparkle": '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01"/>',
    "book": '<path d="M4 5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>',
    "chat": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "store": '<path d="M4 9l1.5-5h13L20 9M4 9v11h16V9M4 9h16"/><path d="M9 20v-6h6v6"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "star": '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>',
    "play": '<path d="M8 5v14l11-7z" fill="currentColor"/>',
    "bell": '<path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z"/><path d="M10 21h4"/>',
    "share": '<path d="M7 17L17 7M9 7h8v8"/>',
    "tick": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "depart": '<path d="M2 19h20"/><path d="M3.5 12.5l2.4-1 2.6 2.2 4.3-1.9-5-5.1 2.3-1 7.4 3.6 3-1.3a1.8 1.8 0 0 1 1.5 3.2L7.4 16.4 3.5 12.5z"/>',
    "arrive": '<path d="M2 20h20"/><path d="M4.2 7.7l2.5-.4 1.7 2.9 4.6.9-3-6.5 2.5-.4 5.8 5.9 3.3.6a1.8 1.8 0 0 1 .2 3.6L6.3 13.2z"/>',
    "ticket": '<path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z"/><path d="M14 5v14" stroke-dasharray="2 2.5"/>',
    "shield": '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "info": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 11v6M12 7.5h.01"/>',
    "speaker": '<path d="M4 10v4h4l5 4V6L8 10z"/><path d="M16.5 9a4 4 0 0 1 0 6M19 6.5a7.5 7.5 0 0 1 0 11"/>',
    "screen": '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/><path d="M10.5 8v4l3.5-2z"/>',
    "swap": '<path d="M4 8h14l-3.5-3.5M20 16H6l3.5 3.5"/>',
    "chevL": '<path d="M15 5l-7 7 7 7"/>',
    "chevR": '<path d="M9 5l7 7-7 7"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "pad": '<path d="M7 8h10a4 4 0 0 1 4 4v1a3 3 0 0 1-5.4 1.8L14.5 14h-5l-1.1 1.8A3 3 0 0 1 3 13v-1a4 4 0 0 1 4-4z"/><path d="M7.5 10.5v3M6 12h3M16 11.5h.01M18 13h.01"/>',
    "ghost": '<path d="M5 21V10a7 7 0 0 1 14 0v11l-2.3-1.6L14.4 21 12 19.4 9.6 21l-2.3-1.6z"/><path d="M9.5 10.5h.01M14.5 10.5h.01"/>',
    "trophy": '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 20h8M10 17h4"/>',
}.items()}

NAV = [
    ("Ofertas", [("index.html", "Inicio", "home"), ("juegos-gratis.html", "Juegos gratis", "gift"), ("juegos-gratis-en-todas-las-tiendas.html", "Regalos por tienda", "gift"),
                 ("ofertas.html", "Todas las ofertas", "flame"), ("favoritos.html", "Mis favoritos", "star"), ("seguidos.html", "Mis seguidos", "bell"),
                 ("oferta-del-dia.html", "Oferta del día", "sparkle"), ("noticias.html", "Novedades", "news"), ("resumen-semanal.html", "Resumen semanal", "calendar"),
                 ("juegos-baratos.html", "Baratos en pesos", "sparkle"), ("juegos-gratis-para-siempre.html", "Gratis para siempre", "gift"),
                 ("rebajas-de-steam.html", "Rebajas de Steam", "clock"), ("que-juego-me-conviene.html", "¿Qué juego me conviene?", "quiz"),
                 ("sorpresa.html", "Sorpréndeme", "dice")]),
    ("Lanzamientos", [("lanzamientos.html", "Calendario", "calendar"), ("lanzamientos.html#proximos", "Próximos", "clock"),
                      ("lanzamientos.html#recientes", "Recientes", "sparkle"), ("lanzamientos.html#por-confirmar", "Por confirmar", "question"),
                      ("lanzamientos-playstation.html", "PlayStation", "store"), ("lanzamientos-xbox.html", "Xbox", "store"),
                      ("lanzamientos-switch.html", "Nintendo Switch", "store"), ("juegos-retrasados.html", "Juegos retrasados", "clock")]),
    ("Códigos", [("codigos.html", "Códigos de juegos", "gift"), ("codigos-genshin-impact.html", "Genshin Impact", "sparkle"),
                 ("codigos-honkai-star-rail.html", "Honkai: Star Rail", "sparkle"), ("codigos-zenless-zone-zero.html", "Zenless Zone Zero", "sparkle")]),
    ("Ayuda", [("guias.html", "Guías", "book"), ("glosario.html", "Glosario gamer", "book"), ("estadisticas.html", "Estadísticas", "sparkle"), ("preguntas-frecuentes.html", "Preguntas", "chat"),
               ("como-verificamos.html", "Cómo verificamos", "check")]),
]
FOOTER = [
    ("como-verificamos.html", "Cómo verificamos"), ("quienes-somos.html", "Quiénes somos"),
    ("contacto.html", "Contacto"), ("privacidad.html", "Privacidad"), ("cookies.html", "Cookies"),
    ("afiliados.html", "Aviso de afiliados"), ("publicidad.html", "Publicidad y patrocinios"),
    ("terminos.html", "Términos de uso"), ("anunciate.html", "Anúnciate"), ("estado.html", "Estado del sistema"),
    ("fuentes.html", "Fuentes de información"),
]
CSP = ("default-src 'self'; img-src 'self' https: data:; script-src 'self'; style-src 'self'; "
       "connect-src 'self' https://*.steamstatic.com; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
       "media-src 'self' blob: https://*.steamstatic.com; frame-src https://www.youtube-nocookie.com; "
       "upgrade-insecure-requests")

e = html.escape

SW_TEMPLATE = """// Service worker de Ofertas Gamer CO: abre la página sin internet con la última copia guardada.
const CACHE = "ogc-__VERSION__";
const SHELL = __SHELL__;
self.addEventListener("install", (ev) => {
  ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (ev) => {
  ev.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (ev) => {
  const req = ev.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (req.mode === "navigate" || url.pathname.includes("/data/")) {
    // Primero internet (precios frescos); sin conexión, la copia guardada.
    ev.respondWith(fetch(req).then((res) => {
      const copy = res.clone();
      if (res.ok) caches.open(CACHE).then((c) => c.put(req, copy));
      return res;
    }).catch(() => caches.match(req).then((hit) => hit || caches.match("sin-conexion.html"))));
    return;
  }
  ev.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
"""


def asset_version(name):
    """Huella corta del archivo: cambia cuando el archivo cambia, así el navegador no usa una copia vieja."""
    return hashlib.sha256((Path(__file__).resolve().parent.parent / "assets" / name).read_bytes()).hexdigest()[:10]


def ext_link(url, text, affiliate=False, cls="btn btn-primary", label=None):
    rel = "sponsored nofollow noopener noreferrer" if affiliate else "noopener noreferrer"
    aria = f' aria-label="{e(label)}"' if label else ""
    return f'<a class="{cls}" href="{e(url)}" target="_blank" rel="{rel}"{aria}>{text}</a>'



def is_poster(url):
    """Las carátulas de Wikipedia son verticales: se muestran completas sobre una copia desenfocada."""
    return (url or "").startswith("https://upload.wikimedia.org/")


def poster_bg(g):
    return (f'<img class="poster-bg" src="{e(g["image"])}" alt="" width="460" height="215" loading="lazy" decoding="async">'
            if is_poster(g.get("image")) else "")


def no_cover(g, cls="no-cover"):
    """Tarjeta con el nombre del juego cuando no hay ninguna imagen libre (mejor que un gris vacío)."""
    plats = " · ".join(g.get("platforms", [])[:3])
    return (f'<div class="{cls}" role="img" aria-label="{e(g["title"])}"><strong>{e(g["title"])}</strong>'
            f'{f"<span>{e(plats)}</span>" if plats else ""}</div>')


def day_es(day):
    """"2026-10-25" -> "25 de octubre de 2026" (sin hora: el historial guarda días)."""
    return f"{int(day[8:10])} de {MONTHS_ES[int(day[5:7]) - 1]} de {day[:4]}"


def slugify_words(text):
    from .model import slugify
    return slugify(text).split("-")


def fallback(o):
    """Miniatura de respaldo por si la portada grande no existe (app.js la cambia al fallar)."""
    small = o.get("imageSmall") or ""
    return f' data-fallback="{e(small)}"' if small.startswith("https://") else ""


STEAM_HERO = "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{id}/library_hero.jpg"


class Site:
    def __init__(self, cfg, stores, ads, out):
        self.cfg, self.stores, self.ads, self.out = cfg, stores, ads, Path(out)
        self.base = cfg["url_web"].rstrip("/") + "/"
        self.pages = []
        self.detail = {}  # id de oferta o juego -> nombre de su página propia
        self.now = datetime.now(timezone.utc)
        self.rate = None  # pesos por dólar, deducido de las ofertas
        self.history = {}  # historial de precios propio (ogc/history.py)

    # ---------- plantilla común ----------
    HERO_KINDS = (("gratis", "free"), ("regalo", "free"), ("codigos", "free"), ("lanzamiento", "rel"), ("juegos-que-salen", "rel"),
                  ("mas-esperados", "rel"), ("retrasados", "rel"), ("guia", "guide"), ("preguntas", "guide"), ("glosario", "guide"),
                  ("como-verificamos", "guide"), ("rebajas", "steam"), ("oferta", "deal"), ("baratos", "deal"), ("minimos", "deal"),
                  ("menos-de", "deal"), ("tiendas", "deal"), ("instant", "deal"))

    def page_hero(self, name, body, crumbs):
        """Envuelve el título, la entrada y la fecha de cada página en una cabecera con su propio estilo según el tema."""
        m = re.search(r'<h1>.*?</h1>(?:\s*<p class="lead">.*?</p>)?(?:\s*<p class="meta">.*?</p>)?', body, flags=re.S)
        if not m or m.start() > 4000 or name.startswith(("oferta-", "juego-")) and name != "oferta-del-dia.html":
            return body
        kind = next((k for key, k in self.HERO_KINDS if key in name), "plain")
        pic = re.search(r'<img[^>]+src="(https://[^"]+)"', body[m.end():m.end() + 60000])
        bg = f'<img class="ph-bg" src="{pic.group(1)}" alt="" width="1280" height="600" decoding="async">' if pic else ""
        hero = (f'<header class="page-hero ph-{kind}{" has-bg" if bg else ""}">{bg}'
                f'{m.group(0)}<span class="ph-deco" aria-hidden="true"></span></header>')
        return body[:m.start()] + hero + body[m.end():]

    def layout(self, name, title, description, body, crumbs=None, jsonld=None, noindex=False, og_type="website", og_image=None):
        if name != "index.html":
            body = self.page_hero(name, body, crumbs)
        canonical = self.base + ("" if name == "index.html" else name)
        full_title = title if name == "index.html" else f"{title} | {self.cfg['nombre']}"
        if len(full_title) > 65:  # Google corta los títulos largos: primero sobra el nombre del sitio
            full_title = title
        if len(description) > 160:  # y las descripciones de más de ~160 letras
            description = description[:157].rsplit(" ", 1)[0].rstrip(",.:;") + "…"
        stores_nav = [(f"ofertas-{st['id']}.html" if getattr(self, "store_counts", {}).get(st["id"]) else f"ofertas.html?tienda={st['id']}", st["name"], "store-" + st["id"]) for st in self.stores.values() if st["active"]]
        if self.cfg.get("instant_gaming_igr"):
            stores_nav.append(("instant-gaming.html", "Instant Gaming", "store-ig"))
        groups = NAV[:1] + [("Tiendas", stores_nav)] + NAV[1:]
        nav = "".join(
            f'<div class="side-group"><p class="side-title">{e(title)}</p><ul>' + "".join(
                f'<li><a href="{href}"{" aria-current=\"page\"" if href == name else ""}>'
                f'{self.nav_icon(ico)}{e(label)}</a></li>' for href, label, ico in links) + "</ul></div>"
            for title, links in groups)
        foot = "".join(f'<li><a href="{href}">{e(label)}</a></li>' for href, label in FOOTER)
        tg = self.cfg.get("enlace_canal_telegram")
        if tg:
            foot += f'<li>{ext_link(tg, "Telegram", cls="")}</li>'
        crumb_html, ld = "", list(jsonld or [])
        if crumbs:
            items = [("index.html", "Inicio")] + crumbs
            crumb_html = '<nav class="crumbs" aria-label="Ruta"><ol>' + "".join(
                f'<li><a href="{h}">{e(t)}</a></li>' if i < len(items) - 1 else f'<li aria-current="page">{e(t)}</li>'
                for i, (h, t) in enumerate(items)) + "</ol></nav>"
            ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": t, "item": self.base + ("" if h == "index.html" else h)}
                for i, (h, t) in enumerate(items)]})
        ld_html = "".join(
            f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False).replace("</", "<\\/")}</script>'
            for x in ld)
        verif = ""
        if name == "index.html":
            google = self.cfg.get("verificacion_google") or []
            for token in [google] if isinstance(google, str) else google:  # una por dirección registrada
                verif += f'<meta name="google-site-verification" content="{e(token)}">\n'
            if self.cfg.get("verificacion_bing"):
                verif += f'<meta name="msvalidate.01" content="{e(self.cfg["verificacion_bing"])}">\n'
            if self.cfg.get("verificacion_impact"):
                verif += f"<meta name='impact-site-verification' value='{e(self.cfg['verificacion_impact'])}'>\n"
        robots = '<meta name="robots" content="noindex">\n' if noindex else ""
        page = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
{verif}{robots}<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{e(self.cfg['nombre'])}">
<meta property="og:locale" content="es_CO">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(og_image or self.base + 'assets/og-image.png')}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{e(og_image or self.base + 'assets/og-image.png')}">
<meta name="theme-color" content="#080a12">
<link rel="icon" href="assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="Ofertas Gamer CO (RSS)" href="rss.xml">
<link rel="alternate" type="application/atom+xml" title="Ofertas Gamer CO (Atom)" href="atom.xml">
<link rel="alternate" type="application/feed+json" title="Ofertas Gamer CO (JSON)" href="feed.json">
<link rel="stylesheet" href="assets/styles.css?v={asset_version("styles.css")}">
<script src="assets/app.js?v={asset_version("app.js")}" defer></script>
{ld_html}
</head>
<body{self.season_class()}>
<div class="bg-decor" aria-hidden="true"></div>
<a class="skip" href="#contenido">Saltar al contenido</a>
<header class="site"><div class="wrap">
<div class="bar"><a class="brand" href="index.html"><img src="assets/logo-72.png" alt="" width="36" height="36">Ofertas Gamer CO</a>
<div class="bar-actions"><a class="btn btn-search" href="buscar.html" aria-label="Buscar un juego en las ofertas">{ICONS['search']}<span>Buscar</span></a>
<button class="btn menu-toggle" id="menu-toggle" type="button" aria-expanded="false" aria-controls="main-nav">Menú</button></div></div>
</div></header>
<div class="shell">
<nav class="side" id="main-nav" aria-label="Principal">{nav}{self.side_channels()}{self.ig_side(name)}</nav>
<main id="contenido"><div class="wrap">
{crumb_html}
{body}
</div></main>
</div>
<footer class="site"><div class="wrap">
{self.foot_columns()}
<div class="prefs" role="group" aria-label="Opciones de lectura"><span class="meta">Opciones de lectura:</span>
<button class="chip" type="button" data-pref="big" aria-pressed="false" hidden>Letra grande</button>
<button class="chip" type="button" data-pref="contrast" aria-pressed="false" hidden>Alto contraste</button>
<button class="chip" type="button" data-pref="lite" aria-pressed="false" hidden>Ahorro de datos</button></div>
<p class="install" id="install-box" hidden><button class="btn btn-primary" type="button" id="install-app">Instalar la app en tu celular</button></p>
{self.support_box()}<p>{e(DISCLOSURE)}</p>
<nav aria-label="Pie de página"><ul>{foot}</ul></nav>
<p>Ofertas Gamer CO no vende productos ni procesa pagos. Los precios y la disponibilidad pueden cambiar sin previo aviso.</p>
<p class="foot-giant" aria-hidden="true">OFERTAS GAMER CO</p>
</div></footer>
{self.bottom_nav(name)}
</body>
</html>
"""
        self.write(name, page)
        if not noindex:
            self.pages.append(name)

    def write(self, name, text):
        path = self.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # ---------- componentes ----------
    def ad_slot(self, slot_id):
        """Los espacios desactivados no generan nada (ni espacio reservado)."""
        if not self.ads.get("ads_enabled"):
            return ""
        slot = next((s for s in self.ads["slots"] if s["id"] == slot_id and s["enabled"]), None)
        if not slot or not slot.get("destination", "").startswith("https://"):
            return ""
        w, h = (slot.get("desktopSize") or "728x90").split("x")
        img = f'<img src="{e(slot["image"])}" alt="{e(slot["alt"])}" width="{w}" height="{h}" loading="lazy">' if slot.get("image") else e(slot["alt"])
        return (f'<aside class="ad" aria-label="{e(slot["label"])}"><p class="meta">{e(slot["label"])}</p>'
                f'{ext_link(slot["destination"], img, affiliate=True, cls="")}</aside>')

    # ---------- piezas de las tarjetas ----------
    def nav_icon(self, key):
        if key.startswith("store-"):
            return f'<span class="side-ico store-dot {e(key)}" aria-hidden="true"></span>'
        return f'<span class="side-ico">{ICONS.get(key, "")}</span>'

    def bottom_nav(self, name):
        items = [("index.html", "Inicio", "home"), ("juegos-gratis.html", "Gratis", "gift"),
                 ("ofertas.html#filters", "Buscar", "search"), ("favoritos.html", "Favoritos", "star"), ("alertas.html", "Alertas", "bell")]
        links = "".join(f'<a href="{h}"{" aria-current=\"page\"" if h.split("#")[0] == name else ""}>{ICONS[i]}<span>{t}</span></a>'
                        for h, t, i in items)
        return f'<nav class="bottom-nav" aria-label="Accesos rápidos">{links}</nav>'

    def is_search(self, o):
        """True si no hay enlace directo al producto y el botón lleva a la búsqueda de la tienda."""
        tpl = (self.stores.get(o["storeId"]) or {}).get("searchUrl") or ""
        prefix = tpl.split("{")[0]
        return bool(prefix) and (o.get("officialUrl") or "").startswith(prefix)

    def rate_for(self, o):
        if o.get("copApproximation") and o.get("currentPrice"):
            return o["copApproximation"] / o["currentPrice"]
        return self.rate

    def cop_value(self, amount, o):
        if amount is None:
            return None
        if o["currency"] == "COP":
            return amount
        rate = self.rate_for(o)
        return amount * rate if rate else None

    @staticmethod
    def pesos(value):
        return "$" + f"{round(value, -2):,.0f}".replace(",", ".")

    def saving_text(self, o):
        if not o.get("originalPrice"):
            return ""
        saved = self.cop_value((o["originalPrice"] or 0) - (o.get("currentPrice") or 0), o)
        return f"Ahorras ≈ {self.pesos(saved)} COP" if saved and saved >= 100 else ""

    def price_stats(self, o):
        from . import history
        return history.stats(self.history, o, self.now) if self.history else None

    def value_score(self, o):
        """Puntaje "Vale la pena" de 0 a 100: descuento (50), nota de la crítica (30) y precio en pesos (20).
        Se calcula solo con datos reales de la oferta; sin nota de la crítica esa parte cuenta a la mitad."""
        if not o.get("currentPrice"):
            return None
        disc = (o.get("discountPercentage") or 0) / 100
        mc = o.get("metacritic")
        critic = (mc / 100) if mc else 0.5
        cop = self.cop_value(o["currentPrice"], o)
        cheap = max(0.0, 1 - cop / 120000) if cop else 0.5
        return round(50 * disc + 30 * critic + 20 * cheap)

    def cop_saved(self, o):
        if not o.get("originalPrice"):
            return 0
        return round(self.cop_value((o["originalPrice"] or 0) - (o.get("currentPrice") or 0), o) or 0)

    def trust_chips(self, o, full=False):
        chips = []
        ps = self.price_stats(o)
        if ps and ps["isLow"]:
            chips.append(f'<span class="st low" title="El más bajo que hemos visto desde el {e(day_es(ps["first"]))}">Mínimo histórico</span>')
        if o.get("metacritic") and full:
            chips.append(f'<span class="st mc" title="Nota de la crítica en Metacritic">Crítica {int(o["metacritic"])}</span>')
        if len(o.get("otherStores") or []) and full:
            n = len(o["otherStores"])
            chips.append(f'<span class="st muted">+{n} {"tienda" if n == 1 else "tiendas"}</span>')
        if "CO" in (o.get("regions") or []):
            chips.append('<span class="st ok">Precio para Colombia</span>')
        elif o["currency"] == "USD":
            chips.append('<span class="st ref">Precio de referencia en USD</span>')
        else:
            chips.append('<span class="st warn">Región por confirmar</span>')
        if not o.get("expiresAt") and full:
            chips.append('<span class="st muted">Vigencia por confirmar</span>')
        if o.get("status") == "Vencido":
            chips.append('<span class="st bad">Oferta terminada</span>')
        if full and o.get("drm"):
            chips.append(f'<span class="st muted">Se activa en {e(o["drm"])}</span>')
        if o.get("affiliate"):
            chips.append('<span class="st aff">Enlace de afiliado</span>')
        if o.get("sponsored"):
            chips.append('<span class="st aff">Patrocinado</span>')
        return '<div class="chips-st">' + "".join(chips) + "</div>"

    def countdown(self, o, cls="left"):
        if not o.get("expiresAt"):
            return ""
        txt = time_left(o["expiresAt"], self.now)
        soon = (parse_iso(o["expiresAt"]) - self.now).total_seconds() < 86400
        return (f'<p class="{cls}{" urgent" if soon else ""}" data-countdown="{e(o["expiresAt"])}" '
                f'title="Hasta el {e(date_es(o["expiresAt"]))}">{ICONS["clock"]}<span>{e(txt)}</span></p>')

    def action_label(self, o):
        if self.is_search(o):
            return "Buscar en la tienda"
        return "Reclamar gratis" if o.get("currentPrice") == 0 else "Ver oferta"

    def offer_button(self, o, cls="btn btn-primary"):
        free = o.get("currentPrice") == 0
        label = self.action_label(o)
        return ext_link(o["destinationUrl"], label, o.get("affiliate"), cls=cls + (" btn-free" if free and not self.is_search(o) else ""),
                        label=f"{label}: {o['title']} en {o['store']} (abre en otra pestaña)")

    def price_html(self, o, big=False):
        free = o.get("currentPrice") == 0
        now = "Gratis" if free else money(o["currentPrice"], o["currency"])
        old = f'<s>Antes {e(money(o["originalPrice"], o["currency"]))}</s>' if o.get("originalPrice") else ""
        cop = "" if free or o["currency"] == "COP" or not cop_text(o) else f'<span class="cop">{e(cop_text(o))}</span>'
        save = self.saving_text(o)
        return (f'<div class="pricebox{" big" if big else ""}"><span class="now{" free" if free else ""}">{e(now)}</span>{old}</div>'
                + (f'<p class="cop-line">{cop}</p>' if cop else "")
                + (f'<p class="save">{e(save)}</p>' if save else ""))

    def store_chip(self, o):
        return f'<span class="store-chip"><span class="store-dot store-{e(o["storeId"])}" aria-hidden="true"></span>{e(o["store"])}</span>'

    def badge(self, o):
        if o.get("currentPrice") == 0:
            return '<span class="badge free">GRATIS</span>'
        return f'<span class="badge">-{o["discountPercentage"]}%</span>' if o.get("discountPercentage") else ""

    def card(self, o):
        free = o.get("currentPrice") == 0
        img = o.get("image") or "assets/placeholder.svg"
        alt = f"Imagen de {o['title']}" if o.get("image") else ""
        cop_now = 0 if free else (self.cop_value(o.get("currentPrice"), o) or 0)
        return f"""<li class="card{' is-free' if free else ''}" data-id="{e(o['id'])}" data-title="{e(o['title'].lower())}" data-store="{e(o['storeId'])}" data-type="{'gratis' if free else 'descuento'}" data-discount="{100 if free else (o.get('discountPercentage') or 0)}" data-expires="{e(o.get('expiresAt') or '')}" data-price="{o.get('currentPrice') or 0}" data-cop="{round(cop_now)}" data-saved="{self.cop_saved(o)}" data-score="{self.value_score(o) or 0}"{' data-low="1"' if (self.price_stats(o) or {}).get('isLow') else ''}>
<div class="thumb"{self.preview_attrs(o.get("trailer"))}><img src="{e(img)}"{fallback(o)} alt="{e(alt)}" width="460" height="215" loading="lazy" decoding="async">{self.badge(o)}{self.store_chip(o)}{f'<button type="button" class="trailer-chip preview-btn" aria-label="Ver avance del tráiler de {e(o["title"])}">{ICONS["play"]}</button>' if self.preview_attrs(o.get("trailer")) else ''}{self.ribbon(o)}</div>
<div class="body"><h3 class="clamp2">{self.title_link(o)}</h3>
<p class="card-meta"><span class="cm-store"><span class="store-dot store-{e(o["storeId"])}" aria-hidden="true"></span>{e(o["store"])}</span>{f'<span class="mc-score" title="Nota de la crítica en Metacritic">{int(o["metacritic"])}</span>' if o.get("metacritic") else ''}</p>
{self.price_html(o)}
{self.countdown(o) or '<p class="left none" title="La tienda no publicó la fecha de fin">Sin fecha de fin</p>'}
{self.trust_chips(o)}
<div class="actions">{self.offer_button(o)}{f'<button class="btn icon-btn claim-btn" type="button" data-claim="{e(o["id"])}" data-value="{self.cop_saved(o)}" aria-pressed="false" aria-label="Marcar {e(o["title"])} como reclamado" title="Ya lo reclamé" hidden>{ICONS['tick']}</button>' if free and self.cop_saved(o) else ''}<button class="btn icon-btn" type="button" data-fav="{e(o['id'])}" aria-pressed="false" aria-label="Guardar {e(o['title'])} en favoritos" hidden>{ICONS['star']}</button><button class="btn icon-btn" type="button" data-share="{e(self.base + self.detail[o['id']] if o['id'] in self.detail else o['destinationUrl'])}" data-title="{e(o['title'])}" aria-label="Compartir {e(o['title'])}" hidden>{ICONS['share']}</button></div>
</div></li>"""

    def card_caption(self, o):
        """Línea corta tipo ficha: tienda, sistema y fecha de fin (solo datos reales)."""
        bits = [o.get("store") or ""]
        if o.get("metacritic"):
            bits.append(f"Metacritic {o['metacritic']}")
        end = parse_iso(o.get("expiresAt")) if o.get("expiresAt") else None
        if end:
            bits.append("hasta el " + end.astimezone(CO_TZ).strftime("%d/%m"))
        return " · ".join(b for b in bits if b)

    def offer_list(self, offers, with_filters=True, list_id="offers", bento=False, poster=False):
        if not offers:
            return '<p class="notice">No hay ofertas disponibles en este momento. Vuelve en unas horas.</p>'
        cards = []
        for i, o in enumerate(offers, 1):
            cards.append(self.card(o))
            if i in (6, 12):
                slot = self.ad_slot(f"inline_after_card_{i}")
                if slot:
                    cards.append(f"<li>{slot}</li>")
        filters = ""
        if with_filters:
            store_opts = "".join(f'<option value="{e(s["id"])}">{e(s["name"])}</option>'
                                 for s in self.stores.values() if s["active"] and any(o["storeId"] == s["id"] for o in offers))
            filters = f"""<form class="filters" id="filters" role="search" aria-label="Buscar y filtrar ofertas" hidden>
<label>Buscar<input type="search" name="q" placeholder="Nombre del juego" autocomplete="off"></label>
<label>Tienda<select name="store"><option value="">Todas</option>{store_opts}</select></label>
<label>Tipo<select name="type"><option value="">Todos</option><option value="gratis">Gratis</option><option value="descuento">Descuento</option></select></label>
<label>Descuento mínimo<select name="min"><option value="0">Cualquiera</option><option value="50">50% o más</option><option value="75">75% o más</option><option value="90">90% o más</option></select></label>
<label>Precio máximo<select name="max"><option value="">Cualquiera</option><option value="20000">Menos de $20.000</option><option value="40000">Menos de $40.000</option></select></label>
<label>Ordenar por<select name="sort"><option value="discount">Mayor descuento</option><option value="score">Vale la pena</option><option value="saved">Más ahorro en pesos</option><option value="expires">Vence primero</option><option value="price">Menor precio</option><option value="title">Nombre</option></select></label>
<label><span>Favoritos</span><span><input type="checkbox" name="favs"> Solo mis favoritos</span></label>
<label><span>Precio</span><span><input type="checkbox" name="low"> Solo mínimos históricos</span></label>
</form>
<nav class="chips quick-chips" aria-label="Atajos"><a class="chip hot" href="?tipo=gratis">Solo gratis</a><a class="chip" href="?orden=score">Vale la pena</a><a class="chip" href="?orden=saved">Más ahorro</a><a class="chip" href="?min=90">-90% o más</a><a class="chip" href="?max=20000">Menos de $20.000</a></nav>
<h2 class="sr-only">Lista de ofertas</h2><p class="count" id="count" aria-live="polite">{len(offers)} ofertas</p>"""
        cols = ('' if poster else '<div class="board-cols" aria-hidden="true"><span>Juego</span><span>Precio</span><span>Termina</span><span></span></div>')
        return filters + cols + f'<ul class="grid{" poster" if poster else " board"}" id="{list_id}">' + "".join(cards) + "</ul>"

    def support_box(self):
        url = self.cfg.get("enlace_kofi")
        if not url:
            return ""
        return ('<div class="support"><p><strong>¿Te ahorramos plata?</strong> El sitio es gratis y sin anuncios. '
                'Si quieres, invítanos un café para mantenerlo.</p>' + ext_link(url, "Apóyanos en Ko-fi", cls="btn btn-kofi") + "</div>")

    def side_channels(self):
        links = [ext_link(self.cfg[k], label, cls=f"btn {cls}") for k, label, cls in
                 (("enlace_canal_telegram", "Canal de Telegram", "btn-tg"), ("enlace_canal_whatsapp", "Canal de WhatsApp", "btn-wa"),
                  ("enlace_discord", "Servidor de Discord", "btn-dc"), ("enlace_kofi", "Apóyanos en Ko-fi", "btn-kofi"))
                 if self.cfg.get(k)]
        return '<div class="side-group side-cta">' + "".join(links) + "</div>" if links else ""

    def channels_cta(self):
        parts = []
        if self.cfg.get("enlace_canal_telegram"):
            parts.append(ext_link(self.cfg["enlace_canal_telegram"], "Recibe las ofertas en Telegram", cls="btn btn-tg"))
        if self.cfg.get("enlace_canal_whatsapp"):
            parts.append(ext_link(self.cfg["enlace_canal_whatsapp"], "Canal de WhatsApp", cls="btn btn-wa"))
        if self.cfg.get("enlace_discord"):
            parts.append(ext_link(self.cfg["enlace_discord"], "Únete al Discord", cls="btn btn-dc"))
        return '<div class="cta">' + "".join(parts) + "</div>"

    def feature(self, offers):
        """Portada: una oferta principal grande y tres secundarias."""
        seen, picks = set(), []
        for o in offers:
            if o["id"] not in seen and o.get("image"):
                seen.add(o["id"])
                picks.append(o)
        picks = picks[:4]
        if not picks:
            return ""
        m = picks[0]
        main = f"""<article class="f-main{' is-free' if m.get('currentPrice') == 0 else ''}">
<img src="{e(m['image'])}"{fallback(m)} alt="" width="1280" height="600" fetchpriority="high" decoding="async">
{self.float_tags(m)}<div class="f-info"><div class="f-top">{self.store_chip(m)}{self.badge(m)}</div>
<h2 class="f-title">{self.title_link(m)}</h2>
{self.price_html(m, big=True)}
{self.countdown(m, "left f-left")}
<div class="cta">{self.offer_button(m)}<button class="btn icon-btn" type="button" data-fav="{e(m['id'])}" aria-pressed="false" aria-label="Guardar {e(m['title'])} en favoritos" hidden>{ICONS['star']}</button></div></div></article>"""
        side = "".join(f"""<li class="f-item"><img src="{e(o['image'])}"{fallback(o)} alt="" width="460" height="215" loading="lazy" decoding="async">
<div class="f-item-info">{self.badge(o)}<h3 class="clamp2">{self.title_link(o)}</h3><p class="f-price{' free' if o.get('currentPrice') == 0 else ''}">{'Gratis' if o.get('currentPrice') == 0 else e(money(o['currentPrice'], o['currency']))}</p>{self.countdown(o)}</div></li>"""
                       for o in picks[1:])
        return f'<section class="feature" aria-label="Ofertas destacadas">{main}<ul class="f-side">{side}</ul></section>'

    def float_tags(self, o):
        """Etiquetas flotantes sobre la imagen principal (datos reales de la oferta)."""
        bits = [o["store"]]
        if o.get("discountPercentage") and o.get("currentPrice"):
            bits.append(f"-{o['discountPercentage']}%")
        if o.get("expiresAt"):
            end = parse_iso(o["expiresAt"])
            if end:
                bits.append("hasta el " + end.astimezone(CO_TZ).strftime("%d/%m"))
        meta = f'<span class="ft ft-bottom">{" · ".join(e(b) for b in bits)}</span>'
        kind = "Gratis hoy" if o.get("currentPrice") == 0 else "Oferta destacada"
        return f'<span class="ft ft-top">{kind}</span>{meta}'

    def deal_of_day(self, live):
        """Una oferta por día (hora Colombia), la que más vale la pena. Se guarda para que no cambie en el día."""
        today = self.now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        prev = getattr(self, "daily", None) or {}
        by_id = {o["id"]: o for o in live}
        if prev.get("date") == today and prev.get("id") in by_id:
            return by_id[prev["id"]]
        recent = set(prev.get("recent", []))
        cands = [o for o in live if o.get("currentPrice") and o.get("image") and o["id"] in self.detail and o["id"] not in recent]
        if not cands:
            return None
        pick = max(cands, key=lambda o: (self.value_score(o) or 0, "CO" in (o.get("regions") or [])))
        self.daily = {"date": today, "id": pick["id"], "title": pick["title"], "recent": ([pick["id"]] + prev.get("recent", []))[:30],
                      **({"sentDate": prev["sentDate"]} if prev.get("sentDate") else {})}
        return pick

    def dotd_block(self, o, page=False):
        if not o:
            return ""
        score = self.value_score(o)
        bg = f'<img class="dotd-bg" src="{e(o["image"])}"{fallback(o)} alt="" width="460" height="215" loading="lazy" decoding="async">' if page else ""
        return f"""<section class="dotd{' dotd-page' if page else ''}" aria-labelledby="dotd-h">{bg}<div class="dotd-media"><img src="{e(o['image'])}"{fallback(o)} alt="" width="460" height="215" loading="lazy" decoding="async">{self.badge(o)}</div>
<div class="dotd-info"><p class="dotd-kicker">{ICONS['depart']} Oferta del día</p><h2 id="dotd-h" class="dotd-title">{self.title_link(o)}</h2>
{self.price_html(o)}{self.countdown(o)}<p class="meta">{self.store_chip(o)} · Vale la pena: <strong>{score}/100</strong></p>
<div class="cta">{self.offer_button(o)}{'' if page else '<a class="btn" href="oferta-del-dia.html">¿Por qué esta?</a>'}</div></div></section>"""

    def soon_strip(self, offers):
        """Franja horizontal con lo que termina en las próximas 72 horas."""
        soon = sorted((o for o in offers if o.get("expiresAt") and
                       0 < (parse_iso(o["expiresAt"]) - self.now).total_seconds() < 72 * 3600),
                      key=lambda o: o["expiresAt"])[:12]
        if not soon:
            return ""
        items = "".join(f"""<li class="soon-item"><img src="{e(o.get('image') or 'assets/placeholder.svg')}"{fallback(o)} alt="" width="460" height="215" loading="lazy" decoding="async">
<div>{self.badge(o)}<p class="soon-title clamp2">{self.title_link(o)}</p>{self.countdown(o)}</div></li>""" for o in soon)
        return (f'<section class="soon" aria-labelledby="soon-h"><h2 id="soon-h">{ICONS["clock"]} Última llamada: terminan pronto</h2>'
                f'<ul class="soon-strip">{items}</ul></section>')

    def quick_search(self):
        stores = "".join(f'<a class="chip" href="ofertas.html?tienda={e(st["id"])}"><span class="store-dot store-{e(st["id"])}" aria-hidden="true"></span>{e(st["name"])}</a>'
                         for st in self.stores.values() if st["active"])
        return f"""<section class="quick" aria-label="Buscar ofertas">
<form class="quick-form" action="ofertas.html" method="get" role="search"><label class="sr-only" for="qs">Buscar un juego</label>
<input id="qs" name="q" type="search" placeholder="Busca un juego…" autocomplete="off"><button class="btn btn-primary" type="submit">{ICONS['search']} Buscar</button></form>
<nav class="chips quick-chips" aria-label="Filtros rápidos"><a class="chip hot" href="juegos-gratis.html">Gratis</a><a class="chip" href="ofertas.html?orden=vence">Terminan pronto</a><a class="chip" href="ofertas.html?max=20000">Menos de $20.000</a><a class="chip" href="ofertas.html?min=75">-75% o más</a>{stores}</nav>
</section>"""

    @staticmethod
    def sec_head(eyebrow, title, lede="", icon="", hid=""):
        """Encabezado de sección como letrero de aeropuerto: pictograma y título, con el texto o enlace al lado."""
        ida = f' id="{hid}"' if hid else ""
        ico = f'<span class="sign-ico" aria-hidden="true">{ICONS[icon]}</span>' if icon in ICONS else ""
        return (f'<div class="sec-big sign">{ico}<h2{ida}>{title}</h2>'
                + (f'<p class="sec-lede">{lede}</p>' if lede else "") + "</div>")

    def tools_grid(self):
        tools = [("bell", "Alertas de precio", "Te avisamos por Telegram cuando un juego baje.", "alertas.html"),
                 ("calendar", "Calendario de estrenos", "Cientos de juegos ordenados por fecha de salida.", "lanzamientos.html"),
                 ("gift", "Juegos gratis", "Epic, Steam, GOG y más, con la hora en que terminan.", "juegos-gratis.html"),
                 ("clock", "Rebajas de Steam", "Cuenta regresiva para la próxima gran rebaja.", "rebajas-de-steam.html"),
                 ("thermo", "Mínimos históricos", "Ofertas que están en su precio más bajo registrado.", "minimos-historicos.html"),
                 ("store", "Comparar tiendas", "El mismo juego en varias tiendas, del más barato al más caro.", "tiendas.html"),
                 ("quiz", "¿Qué juego me conviene?", "Responde 4 preguntas y te recomendamos uno.", "que-juego-me-conviene.html"),
                 ("news", "Resumen semanal", "Lo mejor de la semana, todos los viernes.", "resumen-semanal.html"),
                 ("dice", "Sorpréndeme", "Un juego al azar de las ofertas de hoy.", "sorpresa.html")]
        cards = "".join(f'<li><a href="{href}"><span class="tool-ico">{ICONS[ic]}</span><strong>{e(t)}</strong><span>{e(d)}</span><span class="tool-go" aria-hidden="true">{ICONS["arrow"]}</span></a></li>'
                        for ic, t, d, href in tools)
        return (f'<section class="tools" aria-labelledby="tools-h">'
                + self.sec_head("", 'Servicios para ahorrar',
                                "Todo es gratis y funciona sin crear cuenta.", "info", "tools-h")
                + f'<ul class="tool-grid">{cards}</ul></section>')

    def store_marquee(self):
        names = [s for s in self.stores.values() if s["active"]]
        if len(names) < 3:
            return ""
        row = "".join(f'<li><span class="store-dot store-{e(s["id"])}" aria-hidden="true"></span>{e(s["name"])}'
                      f'<small>{self.store_counts.get(s["id"], 0)} ofertas</small></li>' for s in names)
        return (f'<section class="store-marquee" aria-label="Tiendas oficiales que revisamos"><h2 class="sm-h">Tiendas oficiales que revisamos</h2>'
                f'<div class="sm-track"><ul>{row}</ul></div></section>')

    def journal(self):
        kinds = {"guia-tienda-oficial": "Seguridad", "guia-juegos-gratis-temporales": "Juegos gratis",
                 "guia-reclamar-juegos-gratis-epic": "Paso a paso", "guia-comprar-juegos-baratos-colombia": "Ahorro",
                 "guia-clave-regional-global": "Claves", "guia-que-es-drm": "Explicado", "guia-enlaces-afiliados": "Transparencia"}
        cards = "".join(
            f'<li><a href="{g["slug"]}.html"><span class="jr-kind">{e(kinds.get(g["slug"], "Guía"))}</span>'
            f'<strong>{e(g["title"])}</strong><span class="jr-text">{e(g["description"])}</span><span class="jr-more">Leer la guía {ICONS["arrow"]}</span></a></li>'
            for g in GUIDES[:3])
        return (f'<section class="journal" aria-labelledby="jr-h">'
                + self.sec_head("", 'Antes de comprar: guías',
                                '<a href="guias.html">Ver todas las guías</a>', "book", "jr-h")
                + f'<ul class="jr-grid">{cards}</ul></section>')

    def cta_band(self, item):
        img = (f'<img src="{e(item["image"])}"{fallback(item)} alt="" width="1280" height="600" loading="lazy" decoding="async">'
               if item and item.get("image") else "")
        return (f'<section class="cta-band" aria-labelledby="cta-h">{img}<div class="cta-band-in">'
                f'<h2 id="cta-h">Que las ofertas <span class="grad">te busquen a ti</span></h2>'
                f'<p class="lead">Las mejores ofertas llegan solas a Telegram, Discord y Bluesky. Gratis, sin cuenta, cada 4 horas.</p>{self.channels_cta()}</div></section>')

    def duel_box(self, live):
        """Duelo de tiendas: el mismo juego en dos tiendas oficiales, gana la más barata (precios reales)."""
        cop = lambda x: self.cop_value(x.get("currentPrice"), x)
        rows = []
        for o in live:
            others = [x for x in (o.get("otherStores") or []) if x.get("currentPrice") and cop(x)]
            if not o.get("currentPrice") or not cop(o) or not others:
                continue
            b = max(others, key=cop) if cop(min(others, key=cop)) >= cop(o) else min(others, key=cop)
            if round(cop(b), -2) == round(cop(o), -2):
                continue
            rows.append((abs(cop(o) - cop(b)), o, b))
        rows = sorted(rows, key=lambda r: -r[0])[:4]
        if len(rows) < 2:
            return ""
        def side(x, win):
            return (f'<div class="duel-side{" win" if win else ""}"><span class="store-chip"><span class="store-dot store-{e(x["storeId"])}" aria-hidden="true"></span>{e(x["store"])}</span>'
                    f'<strong>{self.pesos(cop(x))}</strong><small>-{x.get("discountPercentage") or 0}%</small>{"<em>Más barato</em>" if win else ""}</div>')
        items = "".join(
            f'<li><img src="{e(o["image"])}"{fallback(o)} alt="" width="460" height="215" loading="lazy" decoding="async">'
            f'<p class="duel-name">{self.title_link(o)}</p><div class="duel-row">{side(o, cop(o) < cop(b))}<span class="duel-vs" aria-hidden="true">VS</span>{side(b, cop(b) < cop(o))}</div>'
            f'<p class="meta">Diferencia: {self.pesos(diff)} aprox.</p></li>'
            for diff, o, b in rows if o.get("image"))
        return (f'<section class="duels" aria-labelledby="duel-h">'
                + self.sec_head("", 'Comparador: mismo juego, distinta tienda',
                                "El precio del mismo juego en tiendas oficiales. Valores aproximados en pesos.", "swap", "duel-h")
                + f'<ul class="duel-list">{items}</ul></section>')

    def trailers_box(self, games, count=6):
        """Tráileres de los juegos más esperados (pasa el cursor para verlos)."""
        picks = sorted([g for g in games if g.get("trailer") and g.get("image")], key=self.rank)[:count]
        if len(picks) < 3:
            return ""
        items = "".join(
            f'<li><a href="{e(self.detail.get(g["id"]) or g["url"])}"{"" if self.detail.get(g["id"]) else " target=\"_blank\" rel=\"noopener noreferrer\""}>'
            f'<span class="tv-img"{self.preview_attrs(g.get("trailer"))}><img src="{e(g["image"])}"{fallback(g)} alt="" width="460" height="215" loading="lazy" decoding="async">'
            f'<span class="tv-play" aria-hidden="true">{ICONS["play"]}</span><span class="tv-live">Tráiler</span></span>'
            f'<span class="tv-name">{e(g["title"])}</span><span class="tv-date">{e(date_label(g.get("date"), g.get("precision")) if g.get("date") else "Fecha por confirmar")}</span></a></li>'
            for g in picks)
        return (f'<section class="tv" aria-labelledby="tv-h">'
                + self.sec_head("", 'Sala de espera: tráileres',
                                'Pasa el cursor para verlos. <a href="lanzamientos.html">Ver el calendario completo</a>', "screen", "tv-h")
                + f'<ul class="tv-grid">{items}</ul></section>')

    def ribbon(self, o):
        """Etiqueta de estado de la tarjeta, solo con datos reales."""
        end = parse_iso(o.get("expiresAt")) if o.get("expiresAt") else None
        if end and 0 < (end - self.now).total_seconds() < 24 * 3600:
            return '<span class="ribbon r-time">Últimas horas</span>'
        if (self.price_stats(o) or {}).get("isLow"):
            return '<span class="ribbon r-low">Mínimo histórico</span>'
        return ""

    def tide_stage(self, offers, count=4):
        """Portada por capítulos: al bajar, la escena se queda fija y pasa por las ofertas destacadas (datos reales).
        Sin JavaScript o con «menos movimiento» se ve como una cuadrícula normal."""
        seen, picks = set(), []
        for o in offers:
            if o["id"] not in seen and o.get("image"):
                seen.add(o["id"])
                picks.append(o)
        picks = picks[:count]
        if not picks:
            return ""
        chapters, ticks = [], []
        for i, o in enumerate(picks):
            free = o.get("currentPrice") == 0
            pct = o.get("discountPercentage") or 0
            app = o.get("steamAppID")
            # el arte ancho de la biblioteca de Steam se ve nítido a pantalla completa; si no existe, vuelve a la portada
            wide = STEAM_HERO.format(id=app) if app and "steamstatic.com" in o["image"] else o["image"]
            page = self.detail.get(o["id"])
            more = f'<a class="btn btn-ghost" href="{page}">Ver ficha</a>' if page else ""
            words = " ".join(f'<span class="td-w">{e(w)}</span>' for w in o["title"].split())
            big = ('<span class="td-big free">GRATIS</span>' if free else
                   f'<span class="td-big">-<b data-to="{pct}">{pct}</b>%</span>' if pct else "")
            lazy = ' fetchpriority="high"' if i == 0 else ' loading="lazy"'
            chapters.append(
                f'<li class="td-ch{" is-free" if free else ""}" data-i="{i}">'
                f'<img class="td-bg" src="{e(wide)}" data-fallback="{e(o["image"])}" alt="" width="1920" height="620"{lazy} decoding="async">'
                f'<div class="td-art"><img src="{e(o["image"])}"{fallback(o)} alt="" width="920" height="430"{lazy} decoding="async">{big}</div>'
                f'<div class="td-copy"><p class="td-store">{self.store_chip(o)}<span>{"Gratis por tiempo limitado" if free else f"-{pct}% de descuento"}</span></p>'
                f'<p class="td-title">{words}</p>{self.price_html(o, big=True)}{self.countdown(o, "left td-left")}'
                f'<div class="cta">{self.offer_button(o)}{more}</div></div></li>')
            ticks.append(f'<li><button type="button" data-go="{i}"><span class="td-tn">{i + 1}</span><span class="td-tt">{e(o["title"])}</span></button></li>')
        return (f'<section class="tide" data-n="{len(picks)}" aria-label="Ofertas destacadas">'
                f'<div class="td-stage"><ol class="td-list">{"".join(chapters)}</ol>'
                f'<ol class="td-rail" aria-label="Ir a una oferta destacada" hidden>{"".join(ticks)}</ol>'
                f'<div class="td-bar" aria-hidden="true"><span></span></div>'
                f'<p class="td-cue" aria-hidden="true" hidden>Baja para ver las {len(picks)} destacadas</p>'
                '<span class="td-grain" aria-hidden="true"></span></div></section>')

    def foot_columns(self):
        cols = [("Ofertas", [("juegos-gratis.html", "Juegos gratis"), ("ofertas.html", "Todas las ofertas"), ("oferta-del-dia.html", "Oferta del día"),
                             ("minimos-historicos.html", "Mínimos históricos"), ("rebajas-de-steam.html", "Rebajas de Steam")]),
                ("Lanzamientos", [("lanzamientos.html", "Calendario"), ("juegos-retrasados.html", "Juegos retrasados"),
                                  ("lanzamientos-playstation.html", "PlayStation"), ("lanzamientos-xbox.html", "Xbox"), ("lanzamientos-switch.html", "Nintendo Switch")]),
                ("Aprende", [("guias.html", "Guías"), ("preguntas-frecuentes.html", "Preguntas frecuentes"), ("glosario.html", "Glosario"),
                             ("como-verificamos.html", "Cómo verificamos"), ("tiendas.html", "Tiendas oficiales")])]
        html = "".join(f'<div class="fc"><p class="fc-title">{e(t)}</p><ul>' + "".join(f'<li><a href="{h}">{e(l)}</a></li>' for h, l in links) + "</ul></div>"
                       for t, links in cols)
        social = [(self.cfg.get(k), label) for k, label in (("enlace_canal_telegram", "Telegram"), ("enlace_discord", "Discord"),
                                                             ("enlace_bluesky", "Bluesky"), ("enlace_canal_whatsapp", "WhatsApp"), ("enlace_kofi", "Ko-fi"))]
        follow = "".join(f'<li>{ext_link(u, label, cls="")}</li>' for u, label in social if u)
        about = ('<div class="fc fc-about"><p class="foot-brand"><img src="assets/logo-72.png" alt="" width="32" height="32"> Ofertas Gamer CO</p>'
                 '<p>Juegos gratis y ofertas de PC en tiendas oficiales, con precios aproximados en pesos colombianos. Se actualiza solo cada 4 horas.</p>'
                 + (f'<p class="fc-title">Síguenos</p><ul class="fc-social">{follow}</ul>' if follow else "") + "</div>")
        return f'<div class="foot-cols">{about}{html}</div>'

    def savings_box(self, deals):
        """Comparación precio normal contra precio de hoy, con las ofertas que más ahorran en pesos."""
        rows = []
        for o in deals:
            was, now = self.cop_value(o.get("originalPrice"), o), self.cop_value(o.get("currentPrice"), o)
            if was and now and was > now:
                rows.append((was - now, was, now, o))
        rows = sorted(rows, key=lambda r: -r[0])[:3]
        if len(rows) < 3:
            return ""
        was_t, now_t = sum(r[1] for r in rows), sum(r[2] for r in rows)
        items = "".join(
            f'<li><span class="sv-name">{self.title_link(o)}<small>{e(o["store"])} · -{o.get("discountPercentage") or 0}%</small></span>'
            f'<s>{self.pesos(was)}</s><strong>{self.pesos(now)}</strong></li>' for _, was, now, o in rows)
        return (f'<section class="savings" aria-labelledby="sv-h"><div>'
                f'<h2 id="sv-h">Las 3 ofertas que más te ahorran</h2>'
                f'<p class="lead">Si compraras estos tres juegos a precio normal pagarías <s>{self.pesos(was_t)}</s>. Hoy cuestan '
                f'<strong>{self.pesos(now_t)}</strong>: te ahorras <strong class="sv-total">{self.pesos(was_t - now_t)}</strong>.</p>'
                f'<p class="meta">Valores aproximados en pesos colombianos. Confirma el precio final en la tienda.</p></div>'
                f'<ul class="sv-list">{items}</ul></section>')

    def how_we_verify(self):
        steps = [("Buscamos", "Tiendas oficiales", "Solo Steam, Epic, GOG, Humble, Green Man Gaming y Fanatical. Nada de claves de reventa."),
                 ("Verificamos", "Revisión cada 4 horas", "Un sistema automático consulta los precios y retira las ofertas que ya terminaron."),
                 ("Convertimos", "Precio en pesos", "Mostramos el valor aproximado en pesos colombianos y el precio original de la tienda."),
                 ("Avisamos", "Directo a tu celular", "Las mejores ofertas llegan solas a Telegram, Discord y Bluesky.")]
        lis = "".join(f'<li><span class="hs-num">{i}</span><strong>{e(t)}</strong><span>{e(d)}</span></li>'
                      for i, (k, t, d) in enumerate(steps, 1))
        return f"""<section class="how" aria-labelledby="how-h"><h2 id="how-h">{ICONS["shield"]} Control: cómo verificamos los precios</h2><ol class="how-steps big">{lis}</ol>
<p class="how-states"><span class="st ok">Precio para Colombia</span> <span class="st ref">Referencia en USD</span> <span class="st muted">Vigencia por confirmar</span></p>
<p><a href="como-verificamos.html">Leer el método completo</a></p></section>"""

    # ---------- páginas propias por oferta y por juego (para buscadores) ----------
    def assign_pages(self, offers, games):
        used = set()
        for prefix, items in (("oferta", offers), ("juego", games)):
            for it in items:
                base = f"{prefix}-{it.get('slug') or 'x'}"
                name = base + ".html"
                if name in used:
                    name = f"{base}-{it['id'].split('-')[1] if '-' in it['id'] else len(used)}.html"
                used.add(name)
                self.detail[it["id"]] = name

    def title_link(self, it):
        page = self.detail.get(it["id"])
        return f'<a class="title-link" href="{page}">{e(it["title"])}</a>' if page else e(it["title"])

    def alert_button(self, item, kind):
        """Botón "Avísame" que abre el bot de Telegram con la alerta ya armada."""
        bot = getattr(self, "bot", "")
        if not bot:
            return ""
        from .alerts import short_id
        ref = ("o_" if kind == "offer" else "j_") + short_id(item["id"])
        label = "Avísame si baja de precio" if kind == "offer" else "Avísame cuando salga"
        return ext_link(f"https://t.me/{bot}?start={ref}", f"{ICONS['bell']} {label}", cls="btn",
                        label=f"{label}: {item['title']} (abre Telegram)")

    def compare_block(self, o):
        """El mismo juego en otras tiendas, del más barato al más caro (solo ofertas verificadas)."""
        same = list(o.get("otherStores") or [])
        if not same:
            return ""
        price = lambda x: x.get("copApproximation") if x.get("currency") == "USD" else x.get("currentPrice")
        rows = "".join(self.note_row(x, "offer", self.now) for x in sorted(same + [o], key=lambda x: price(x) or 0))
        return (f'<section class="compare" aria-labelledby="cmp-h"><h2 id="cmp-h">{ICONS["store"]} Compara tiendas</h2>'
                f'<p class="meta">El mismo juego en otras tiendas oficiales, del más barato al más caro.</p>'
                f'<div class="note"><section class="n-sec"><ul>{rows}</ul></section></div></section>')

    def ig_url(self, title=None):
        igr = self.cfg.get("instant_gaming_igr")
        if not igr:
            return ""
        if title:
            return "https://www.instant-gaming.com/es/busquedas/?" + urlencode({"q": title, "igr": igr})
        return "https://www.instant-gaming.com/es/?" + urlencode({"igr": igr})

    def offer_buy(self, o):
        if not o.get("currentPrice"):
            return ""
        same = sorted([o] + list(o.get("otherStores") or []), key=lambda x: (x.get("copApproximation") if x.get("currency") == "USD" else x.get("currentPrice")) or 0)
        return self.buy_block(o["title"], [(x["store"], money(x["currentPrice"], x["currency"]), x.get("destinationUrl")) for x in same])

    @staticmethod
    def eneba_url(title):
        return "https://www.eneba.com/store/all?" + urlencode({"text": title})

    def steam_sales(self, games, now, listed=()):
        """Juegos del calendario que Steam Colombia tiene en descuento ahora (precio revisado en cada corrida)."""
        sale = sorted([g for g in games if (self.live_price(g, now) or {}).get("discount") and g["title"].lower() not in listed],
                      key=lambda g: (-g["price"]["discount"], self.rank(g)))[:24]
        if not sale:
            return ""
        rows = "".join(
            f'<li class="spot-card"><div class="spot-img"><img class="spot-fg" src="{e(g.get("image") or "assets/placeholder.svg")}"{fallback(g)} alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async">'
            f'<span class="badge">-{g["price"]["discount"]}%</span></div><div class="spot-body"><h3 class="clamp2">{self.title_link(g)}</h3>'
            f'<p class="meta"><s>{e(money(g["price"]["initial"], "COP"))}</s> <strong>{e(money(g["price"]["final"], "COP"))}</strong> en Steam</p>'
            f'<div class="rel-actions">{self.game_link(g, "Ver en Steam")}</div></div></li>' for g in sale)
        return (f'<section class="spot" id="steam-ahora"><div class="sec-head"><h2>{ICONS["flame"]} También en oferta en Steam ahora</h2>'
                f'<p class="meta">Juegos nuevos y esperados que Steam Colombia tiene con descuento. Precios revisados cada 4 horas directo en Steam.</p></div>'
                f'<ul class="spot-grid small">{rows}</ul></section>')

    # ---------- ideas nuevas: rebajas de Steam, termómetro, ahorro, test, sorpresa, retrasos, mapa de calor ----------
    def season_class(self):
        """Temporadas de la interfaz: Halloween del 15 de octubre al 2 de noviembre (hora Colombia). Se quita sola."""
        now = getattr(self, "now", None)
        if not now:
            return ""
        md = now.astimezone(CO_TZ).strftime("%m-%d")
        return ' class="halloween"' if "10-15" <= md <= "11-02" else ""

    def halloween_box(self, games, live):
        """Especial de terror en la portada durante la temporada de Halloween: juegos reales del tema."""
        if not self.season_class():
            return ""
        ev = {"tipo": "fest", "buscar": next((x.get("buscar") for x in (getattr(self, "steam_cfg", {}) or {}).get("eventos", []) if "Halloween" in x["nombre"]), [])}
        if not ev["buscar"]:
            return ""
        # ofertas de hoy cuyo texto oficial de Steam habla de terror
        kw = [k for k in ev["buscar"] if k[:1].islower()]
        scary = [o for o in live if o.get("image") and o.get("about") and any(re.search(r"\b" + re.escape(k) + r"\b", o["about"].lower()) for k in kw)]
        scary.sort(key=lambda o: -(o.get("discountPercentage") or 0))
        cards = "".join(self.card(o) for o in scary[:6])
        coming = self.event_covers(ev, games, [], set(), 4)
        soon = "".join(f'<li class="spot-card"><div class="spot-img"><img class="spot-fg" src="{e(img)}" alt="" width="460" height="215" loading="lazy" decoding="async"></div>'
                       f'<div class="spot-body"><h3 class="clamp2"><a class="title-link" href="{e(url)}">{e(t)}</a></h3></div></li>' for t, img, url in coming)
        if not cards and not soon:
            return ""
        return (f'<section class="halloween-box"><h2>{ICONS["ghost"]} Especial de terror</h2><p class="meta">Es octubre: juegos de miedo en oferta hoy y los de terror que vienen. '
                'Elegidos por su descripción oficial en Steam.</p>'
                + (f'<ul class="grid">{cards}</ul>' if cards else '')
                + (f'<h3>Los de terror que vienen</h3><ul class="spot-grid small">{soon}</ul>' if soon else '') + '</section>')

    def steam_events(self, now):
        """Eventos oficiales de Steam (config/steam_eventos.json) que no han terminado, con su estado."""
        today = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        out = []
        for ev in (getattr(self, "steam_cfg", {}) or {}).get("eventos", []):
            if ev["fin"] < today:
                continue
            start = datetime.strptime(ev["inicio"], "%Y-%m-%d").date()
            days = (start - now.astimezone(CO_TZ).date()).days
            out.append(dict(ev, live=ev["inicio"] <= today, days=days))
        return out

    def steam_strip(self, now):
        evs = self.steam_events(now)
        live = [x for x in evs if x["live"]]
        sale = next((x for x in evs if x["tipo"] == "rebaja"), None)
        pick = live[0] if live else sale
        if not pick:
            return ""
        if pick["live"]:
            txt = f'<strong>Ahora en Steam:</strong> {e(pick["nombre"])} hasta el {e(day_es(pick["fin"]))}.'
        else:
            txt = f'<strong>Faltan {pick["days"]} días</strong> para las {e(pick["nombre"])} ({e(day_es(pick["inicio"]))}).'
        return f'<p class="steam-strip">{ICONS["clock"]}<span>{txt}</span><a href="rebajas-de-steam.html">Ver calendario de rebajas →</a></p>'

    def event_covers(self, ev, games, live, used, count=3):
        """Portadas reales para ilustrar un evento: juegos del tema (por género o palabras), o las mejores ofertas."""
        if ev["tipo"] == "rebaja":
            pool = [(o["title"], o.get("image"), self.detail.get(o["id"]) or o["destinationUrl"])
                    for o in sorted(live, key=lambda o: -(o.get("discountPercentage") or 0)) if o.get("image") and o.get("currentPrice")]
        else:
            ranked = sorted([g for g in games if g.get("image") and g["id"] in self.detail], key=self.rank)
            if ev["tipo"] == "next":
                ranked = [g for g in ranked if g.get("comingSoon")]
            kw = ev.get("buscar") or []
            def hit(g):  # en mayúscula = género de Steam; en minúscula = palabra completa del título o la descripción
                text = (g["title"] + " " + (g.get("description") or "")).lower()
                return any(k in g.get("genres", []) if k[:1].isupper() else re.search(r"\b" + re.escape(k) + r"\b", text) for k in kw)
            themed = [g for g in ranked if hit(g)] if kw else ranked
            pool = [(g["title"], g["image"], self.detail[g["id"]]) for g in themed + ranked]
        out = []
        for t, img, url in pool:
            if t not in used and t not in {x[0] for x in out}:
                out.append((t, img, url))
            if len(out) == count:
                break
        used.update(t for t, *_ in out)
        return out

    def steam_sales_page(self, now, updated_line, live=(), games=()):
        cfg = getattr(self, "steam_cfg", {}) or {}
        evs = self.steam_events(now)
        if not evs:
            return
        used = set()
        sale = next((x for x in evs if x["tipo"] == "rebaja" and not x["live"]), None)
        hero = ""
        if sale:
            mosaic = "".join(f'<img src="{e(img)}" alt="" width="460" height="215" loading="lazy" decoding="async">' for _, img, _ in self.event_covers(sale, games, live, used, 8))
            hero = (f'<section class="countdown-hero" data-steam-countdown="{e(sale["inicio"])}"><div class="cd-mosaic" aria-hidden="true">{mosaic}</div>'
                    f'<div class="cd-inner"><h2><span class="cd-pre">Próxima gran rebaja:</span> {e(sale["nombre"])}</h2>'
                    f'<p class="cd-date">Del {e(day_es(sale["inicio"]))} al {e(day_es(sale["fin"]))}</p>'
                    f'<p class="cd-clock" aria-live="off"><span><b data-cd="d">{sale["days"]}</b>días</span><span><b data-cd="h">–</b>horas</span><span><b data-cd="m">–</b>min</span><span><b data-cd="s">–</b>seg</span></p></div></section>')
        kinds = {"rebaja": "Gran rebaja", "next": "Demos gratis", "fest": "Festival temático"}
        rows = []
        for x in evs:
            covers = self.event_covers(x, games, live, used)
            bg = f'<img class="ev-bg" src="{e(covers[0][1])}" alt="" width="460" height="215" loading="lazy" decoding="async">' if covers else ""
            thumbs = "".join(f'<a href="{e(url)}" title="{e(t)}"><img src="{e(img)}" alt="{e(t)}" width="460" height="215" loading="lazy" decoding="async"></a>' for t, img, url in covers)
            left = "En curso ahora" if x["live"] else ("Empieza mañana" if x["days"] == 1 else f"Faltan {x['days']} días")
            rows.append(f'<li class="ev ev-{e(x["tipo"])}{" live" if x["live"] else ""}">{bg}'
                        f'<div class="ev-info"><span class="ev-kind">{e(kinds.get(x["tipo"], "Evento"))}</span><strong>{e(x["nombre"])}</strong>'
                        f'<span class="ev-dates">{e(day_es(x["inicio"]))} – {e(day_es(x["fin"]))}</span><span class="ev-left">{left}</span></div>'
                        f'<div class="ev-covers">{thumbs}</div></li>')
        rows = "".join(rows)
        faq = ('<section class="prose"><h2>Preguntas sobre las rebajas de Steam</h2>'
               '<h3>¿A qué hora empiezan?</h3><p>Valve publica el día, no la hora. Normalmente empiezan a las 10 a. m. hora del Pacífico, que en Colombia es a las 12 del mediodía (en diciembre, por el cambio de horario de EE. UU., suele ser a la 1 p. m.).</p>'
               '<h3>¿Qué es un "Fest"?</h3><p>Son semanas temáticas: Steam junta juegos de un tipo (carreras, peleas, estrategia…) y muchos bajan de precio. No son tan grandes como las rebajas de temporada.</p>'
               '<h3>¿Qué es el Steam Next Fest?</h3><p>Una semana con cientos de demos gratis de juegos que todavía no salen.</p>'
               '<h3>¿Las imágenes son de los eventos?</h3><p>Son portadas de juegos reales del tema de cada evento que están en nuestra página (o de las mejores ofertas de hoy). Valve publica el póster oficial de cada evento pocos días antes de que empiece.</p>'
               '<h3>¿Cómo me entero de los descuentos?</h3><p>El bot revisa los precios de Steam Colombia cada 4 horas y los publica en <a href="ofertas.html">Ofertas</a> y en nuestro canal de Telegram.</p></section>')
        self.layout("rebajas-de-steam.html", "Rebajas de Steam 2026 y 2027: fechas oficiales y cuenta regresiva",
                    "Cuándo son las próximas rebajas de Steam: invierno 2026, primavera y verano 2027, fests temáticos y Next Fest, con cuenta regresiva y hora en Colombia.",
                    f'<h1>Rebajas de <span class="grad">Steam</span>: fechas oficiales</h1><p class="lead">Todas las rebajas y festivales que Valve ya anunció, con cuenta regresiva. '
                    f'Fechas tomadas de la <a href="{e(cfg.get("fuente", ""))}" target="_blank" rel="noopener noreferrer">página oficial de eventos de Steam</a> (revisada el {e(day_es(cfg.get("revisado", "")))}).</p>'
                    f'{hero}<ul class="ev-list">{rows}</ul>{faq}',
                    crumbs=[("rebajas-de-steam.html", "Rebajas de Steam")])

    def thermometer(self, live, free):
        """Termómetro de ofertas de hoy (0 a 10) con una fórmula sencilla y pública, solo con datos reales."""
        deals = sorted([o for o in live if o.get("currentPrice")], key=lambda o: -(o.get("discountPercentage") or 0))[:50]
        if len(deals) < 10:
            return ""
        avg = sum(o.get("discountPercentage") or 0 for o in deals) / len(deals)
        lows = sum(1 for o in live if (self.price_stats(o) or {}).get("isLow"))
        score = round(min(10, avg / 10 * 0.6 + min(lows, 20) / 20 * 2 + min(len(free), 5) / 5 * 2), 1)
        word = "¡Día buenísimo para comprar!" if score >= 8 else "Buen día para comprar" if score >= 6 else "Día normal" if score >= 4 else "Mejor espera"
        arc = round(score / 10 * 125.6, 1)  # media circunferencia de radio 40
        return (f'<section class="thermo" aria-labelledby="thermo-h"><svg viewBox="0 0 100 58" class="gauge" aria-hidden="true">'
                f'<path d="M10 50 A40 40 0 0 1 90 50" class="g-bg"/><path d="M10 50 A40 40 0 0 1 90 50" class="g-val" stroke-dasharray="{arc} 200"/></svg>'
                f'<div><h2 id="thermo-h">Termómetro de hoy: <span class="t-score">{score}</span>/10</h2><p class="t-word">{e(word)}</p>'
                f'<p class="meta">Descuento promedio de las 50 mejores: {round(avg)}% · {lows} en su mínimo histórico · {len(free)} gratis ahora. '
                f'<a href="como-verificamos.html#termometro">Cómo se calcula</a></p></div></section>')

    def saved_box(self):
        return (f'<p class="saved-box" id="saved-box" hidden>{ICONS["trophy"]} <span>Has ahorrado <strong data-saved-total>$0</strong> reclamando '
                '<strong data-saved-count>0</strong> juegos gratis.</span> <span class="meta">Marca el visto en cada juego que reclames. Se guarda solo en este navegador.</span></p>')

    def heatmap(self, games, now):
        """Mapa de calor de estrenos: cada día de los próximos meses, más brillante cuantos más juegos salen."""
        today = now.astimezone(CO_TZ).date()
        counts = {}
        for g in games:
            if g.get("precision") == "day" and g.get("date"):
                counts[g["date"]] = counts.get(g["date"], 0) + 1
        months, y, m = [], today.year, today.month
        for i in range(6):
            yy, mm = y + (m - 1 + i) // 12, (m - 1 + i) % 12 + 1
            first = datetime(yy, mm, 1).date()
            nxt = datetime(yy + (mm == 12), mm % 12 + 1, 1).date()
            page = f"juegos-que-salen-en-{MONTHS_ES[mm - 1]}-{yy}.html"
            has_page = page in self.pages
            cells = ['<span class="hm-pad"></span>'] * first.weekday()
            d = first
            while d < nxt:
                k = d.isoformat()
                n = counts.get(k, 0)
                lvl = 0 if not n else 1 if n == 1 else 2 if n <= 3 else 3 if n <= 6 else 4
                tip = f'{d.day} de {MONTHS_ES[mm - 1]}: {n} {"juego" if n == 1 else "juegos"}'
                cls = f'hm-d l{lvl}{" past" if d < today else ""}{" today" if d == today else ""}'
                cells.append(f'<a class="{cls}" href="{page}#dia-{k}" title="{e(tip)}" aria-label="{e(tip)}">{d.day}</a>' if n and has_page
                             else f'<span class="{cls}" title="{e(tip)}">{d.day}</span>')
                d += timedelta(days=1)
            months.append(f'<div class="hm-month"><p class="hm-name">{MONTHS_ES[mm - 1].capitalize()} {yy}</p><div class="hm-grid">'
                          + "".join(f'<span class="hm-wd">{x}</span>' for x in "LMMJVSD") + "".join(cells) + '</div></div>')
        if not counts:
            return ""
        return (f'<section class="heatmap" aria-labelledby="hm-h"><div class="sec-head"><h2 id="hm-h">{ICONS["flame"]} Mapa de calor de estrenos</h2>'
                f'<p class="meta">Cuanto más brilla el día, más juegos salen. Toca un día para ver cuáles.</p></div>'
                f'<div class="hm-wrap">{"".join(months)}</div><p class="hm-legend meta">Menos <i class="l1"></i><i class="l2"></i><i class="l3"></i><i class="l4"></i> Más</p></section>')

    def fun_pages(self, live, free, games, now, updated_line):
        """Páginas nuevas: rebajas de Steam, test de recomendación, sorpresa y juegos retrasados."""
        import json as _json
        self.steam_sales_page(now, updated_line, live, games)
        # datos para el test y para «Sorpréndeme» (solo lo que ya está publicado en la página)
        by_title = {g["title"].lower(): g for g in games}
        items = []
        for o in live:
            gm = by_title.get(o["title"].lower()) or {}
            items.append({"t": o["title"], "u": self.detail.get(o["id"]) or o["destinationUrl"], "i": o.get("imageSmall") or o.get("image") or "",
                          "g": gm.get("genres") or [], "k": "gratis" if o.get("currentPrice") == 0 else "oferta",
                          "p": round(self.cop_value(o.get("currentPrice"), o) or 0), "d": o.get("discountPercentage") or 0})
        for g in getattr(self, "f2p", []) or []:
            items.append({"t": g["title"], "u": g["url"], "i": g.get("imageSmall") or g.get("image") or "", "g": g.get("genres") or [], "k": "f2p", "p": 0, "d": 0})
        for g in games:
            if g["id"] not in self.detail:
                continue
            lp = self.live_price(g, now)
            if g.get("comingSoon"):
                items.append({"t": g["title"], "u": self.detail[g["id"]], "i": g.get("image") or "", "g": g.get("genres") or [], "k": "pronto", "p": -1, "d": 0, "r": self.rank(g)})
            elif lp and lp.get("discount") and g["title"].lower() not in {o["title"].lower() for o in live}:
                items.append({"t": g["title"], "u": self.detail[g["id"]], "i": g.get("image") or "", "g": g.get("genres") or [], "k": "oferta", "p": round(lp["final"]), "d": lp["discount"]})
        self.write("data/test-juegos.json", _json.dumps({"items": items}, ensure_ascii=False, separators=(",", ":")))
        surprise = [x["u"] for x in items if not x["u"].startswith("http")]
        self.write("data/sorpresa.json", _json.dumps(surprise, ensure_ascii=False, separators=(",", ":")))
        genres = ["Acción", "Aventura", "Rol", "Estrategia", "Simuladores", "Deportes", "Carreras", "Casual", "Indie", "Multijugador masivo"]
        opt = lambda q, v, label: f'<button type="button" class="quiz-opt" data-q="{q}" data-v="{e(v)}" aria-pressed="false">{e(label)}</button>'
        self.layout("que-juego-me-conviene.html", "¿Qué juego me conviene? Test rápido de juegos gratis y en oferta",
                    "Responde 3 preguntas y te recomendamos juegos gratis, en oferta o por salir según tu presupuesto y lo que te gusta. Con precios reales de hoy.",
                    f'<h1>¿Qué juego me <span class="grad">conviene</span>?</h1><p class="lead">Responde 3 preguntas y te mostramos juegos que existen hoy en la página: gratis, en oferta o por salir.</p>'
                    f'<div class="quiz" id="quiz"><section class="quiz-step"><h2>1. ¿Cuánto quieres gastar?</h2><div class="quiz-opts">{opt("p", "0", "Nada, solo gratis")}{opt("p", "50000", "Hasta $50.000")}{opt("p", "any", "Me da igual")}</div></section>'
                    f'<section class="quiz-step"><h2>2. ¿Qué te gusta jugar?</h2><div class="quiz-opts">{"".join(opt("g", x, x) for x in genres)}{opt("g", "any", "De todo")}</div></section>'
                    f'<section class="quiz-step"><h2>3. ¿Lo quieres ya?</h2><div class="quiz-opts">{opt("w", "now", "Sí, para jugar hoy")}{opt("w", "soon", "Me sirve uno que sale pronto")}</div></section>'
                    f'<p><button type="button" class="btn btn-primary" id="quiz-go" disabled>Ver mis juegos</button> <button type="button" class="btn" id="quiz-again" hidden>Otra vez</button></p>'
                    f'<div id="quiz-out" aria-live="polite"></div></div>'
                    '<noscript><p class="notice">El test necesita JavaScript. Mira los <a href="juegos-gratis.html">juegos gratis</a> o <a href="ofertas.html">todas las ofertas</a>.</p></noscript>',
                    crumbs=[("que-juego-me-conviene.html", "¿Qué juego me conviene?")])
        self.layout("sorpresa.html", "Sorpréndeme: un juego al azar", "Te llevamos a una oferta, un juego gratis o un estreno al azar.",
                    '<h1>Sorpréndeme</h1><p class="lead" id="surprise-msg">Buscando un juego al azar…</p>'
                    '<p><a class="btn btn-primary" href="sorpresa.html" data-surprise>Otro al azar</a> <a class="btn" href="ofertas.html">Ver todas las ofertas</a></p>',
                    crumbs=[("sorpresa.html", "Sorpréndeme")], noindex=True)
        # juegos retrasados (la fecha cambió en las últimas semanas, según Steam o Wikipedia)
        moved = []
        for g in games:
            ch = g.get("dateChanged") or {}
            if ch.get("from") and g.get("date") and g["id"] in self.detail:
                day = lambda v: datetime.strptime((v + "-01-01")[:10] if len(v) < 10 else v[:10], "%Y-%m-%d")
                try:
                    shift = (day(g["date"]) - day(ch["from"])).days
                except ValueError:
                    continue
                moved.append((shift, g, ch))
        moved.sort(key=lambda t: (-t[0], self.rank(t[1])))
        rows = "".join(
            f'<li class="delay"><a href="{self.detail[g["id"]]}"><img src="{e(g.get("image") or "assets/placeholder.svg")}"{fallback(g)} alt="" width="460" height="215" loading="lazy" decoding="async"></a>'
            f'<div><h3>{self.title_link(g)}</h3><p><s>{e(date_label(ch["from"], ch.get("fromPrecision")))}</s> → <strong>{e(date_label(g.get("date"), g.get("precision")))}</strong></p>'
            f'<p class="{"late" if shift > 0 else "early"}">{"Se retrasó" if shift > 0 else "Se adelantó"} {abs(shift)} días · cambio visto el {e(date_es(ch["at"]))}</p></div></li>'
            for shift, g, ch in moved)
        self.layout("juegos-retrasados.html", "Juegos retrasados y adelantados: cambios de fecha de lanzamiento",
                    "Los juegos que cambiaron su fecha de lanzamiento en las últimas semanas: cuánto se retrasaron o adelantaron, según Steam y Wikipedia.",
                    f'<h1>Juegos <span class="grad">retrasados</span> (y adelantados)</h1><p class="lead">Cuando un juego cambia su fecha en Steam o Wikipedia, el bot lo nota y lo anota aquí durante unas semanas.</p>{updated_line}'
                    + (f'<ul class="delays">{rows}</ul>' if rows else '<p class="notice">En las últimas semanas no hemos visto cambios de fecha. Esta página se actualiza sola.</p>')
                    + '<p><a class="btn" href="lanzamientos.html">Ver el calendario</a></p>',
                    crumbs=[("lanzamientos.html", "Lanzamientos"), ("juegos-retrasados.html", "Juegos retrasados")])

    def price_text(self, g, now):
        p = self.live_price(g, now)
        if not p:
            return ""
        return money(p["final"], p["currency"]) + (f' (-{p["discount"]}%)' if p.get("discount") else "")

    def price_line(self, g, now):
        """En la ficha del juego: el precio actual en Steam Colombia y el descuento, con la hora en que lo revisamos."""
        p = self.live_price(g, now)
        if not p:
            return ""
        sale = (f'<span class="badge">-{p["discount"]}%</span> <s>{e(money(p["initial"], p["currency"]))}</s> ' if p.get("discount") else "")
        return (f'<p class="detail-price">{sale}<strong>{e(money(p["final"], p["currency"]))}</strong> en Steam Colombia'
                f'{" · en oferta ahora" if p.get("discount") else ""}<span class="meta price-at">Precio revisado: {e(date_es(p["at"]))}. Se revisa cada 4 horas.</span></p>')

    def buy_block(self, title, official):
        """«Dónde comprarlo»: primero las tiendas oficiales (con precio verificado si lo hay) y luego tiendas de claves.
        official: lista de (tienda, precio o "", url). En las tiendas de claves no mostramos precio: no tenemos fuente."""
        rows = [(e(name), "Oficial", price, url, False, "") for name, price, url in official if url]
        if self.ig_url(title):
            rows.append(('<img src="assets/brands/ig-icon.png" alt="" width="18" height="19"> Instant Gaming', "Claves", "", self.ig_url(title), True, "btn-ig"))
        rows.append(("Eneba", "Claves", "", self.eneba_url(title), False, "btn-eneba"))
        html_rows = "".join(
            f'<li class="buy-row"><span class="buy-store">{name}</span><span class="buy-tag{" off" if tag == "Oficial" else ""}">{e(tag)}</span>'
            + (f'<span class="buy-price">{e(price)}</span>' if price else '<span class="buy-price none">Ver precio</span>')
            + ext_link(url, "Ir →", affiliate=aff, cls=f"btn btn-sm {cls or 'btn-primary'}", label=f"Ver {title} en {name.split('> ')[-1]} (abre en otra pestaña)")
            + "</li>" for name, tag, price, url, aff, cls in rows)
        return (f'<section class="buy" aria-labelledby="buy-h"><h2 id="buy-h">{ICONS["store"]} Dónde comprarlo</h2><ul class="buy-list">{html_rows}</ul>'
                '<p class="meta">Las tiendas de claves venden códigos de terceros: revisa la región y la plataforma antes de pagar. '
                'Instant Gaming es enlace de afiliado (recibimos una pequeña comisión sin costo para ti). <a href="instant-gaming.html">Cómo comprar claves seguro</a>.</p></section>')

    def ig_side(self, name):
        """Banner vertical de Instant Gaming al final del menú lateral (solo en pantallas grandes), según la página."""
        url = self.ig_url()
        if not url or name == "instant-gaming.html":
            return ""
        pick = {"lanzamientos-indie.html": "indie", "lanzamientos-carreras.html": "carreras", "lanzamientos-simuladores.html": "simulacion",
                "lanzamientos.html": "lanzamientos", "lanzamientos-pc.html": "lanzamientos"}.get(name)
        if not pick:
            pick = "generic-" + str(int(hashlib.md5(name.encode()).hexdigest(), 16) % 4 + 1)
        return (f'<div class="side-ad"><a href="{e(url)}" target="_blank" rel="sponsored nofollow noopener noreferrer">'
                f'<img src="assets/brands/ig-v-{pick}.webp" alt="Instant Gaming: hasta -80% en videojuegos" width="320" height="450" loading="lazy" decoding="async"></a>'
                '<p class="meta">Enlace de afiliado</p></div>')

    def ig_banner(self, which="rpg"):
        url = self.ig_url()
        if not url:
            return ""
        alt = {"rpg": "Instant Gaming: hasta 90% de descuento en RPGs", "sim": "Instant Gaming: hasta 90% de descuento en simulación",
               "deportes": "Instant Gaming: hasta 90% de descuento en deportes"}[which]
        return (f'<aside class="ig-banner"><a href="{e(url)}" target="_blank" rel="sponsored nofollow noopener noreferrer">'
                f'<img src="assets/brands/ig-banner-{which}.webp" alt="{e(alt)}" width="900" height="276" loading="lazy" decoding="async"></a>'
                '<p class="meta">Enlace de afiliado de Instant Gaming</p></aside>')

    def ig_page(self, live):
        url = self.ig_url()
        if not url:
            return
        top = sorted([o for o in live if o.get("currentPrice")], key=lambda o: -(o.get("discountPercentage") or 0))[:12]
        rows = "".join(
            f'<li class="spot-card"><div class="spot-img"><img class="spot-fg" src="{e(o.get("image") or "assets/placeholder.svg")}"{fallback(o)} alt="Imagen de {e(o["title"])}" width="460" height="215" loading="lazy" decoding="async">'
            f'<span class="badge">-{o.get("discountPercentage") or 0}%</span></div>'
            f'<div class="spot-body"><h3 class="clamp2">{self.title_link(o)}</h3>'
            f'<p class="meta">Oficial en {e(o["store"])}: <strong>{e(money(o["currentPrice"], o["currency"]))}</strong></p><div class="rel-actions">'
            + ext_link(self.ig_url(o["title"]), "Comparar en Instant Gaming", affiliate=True, cls="btn btn-sm btn-ig", label=f"Comparar {o['title']} en Instant Gaming (enlace de afiliado)")
            + '</div></div></li>' for o in top)
        self.layout("instant-gaming.html", "Instant Gaming: comprar claves de juegos más baratas de forma segura",
                    "Qué es Instant Gaming, cómo comparar el precio de un juego como clave y qué revisar antes de pagar desde Colombia.",
                    f"""<div class="prose"><p class="ig-hero"><img src="assets/brands/ig-logo.png" alt="Instant Gaming" width="320" height="91"></p><h1>Instant Gaming</h1>
<p class="lead">Instant Gaming vende <strong>claves</strong> (códigos) que se activan en Steam, Epic, Xbox, PlayStation o Nintendo. A veces un juego sale más barato ahí que en la tienda oficial.</p>
<p>{ext_link(url, "Ir a Instant Gaming →", affiliate=True, cls="btn btn-primary btn-ig")}</p>
<h2>Antes de pagar, revisa</h2><ul>
<li><strong>Plataforma:</strong> que la clave sea para donde juegas (Steam, Xbox, PlayStation…).</li>
<li><strong>Región:</strong> que diga «Global», «Latinoamérica» o que funcione en Colombia.</li>
<li><strong>Edición:</strong> estándar, deluxe o solo un DLC.</li>
<li><strong>Precio final:</strong> compáralo con el de la oferta oficial en nuestro sitio.</li></ul>
</div>{self.ig_banner("rpg")}{self.ig_banner("sim")}{self.ig_banner("deportes")}<div class="prose"><h2>Compara las mejores ofertas de hoy</h2><p>Estas son nuestras ofertas oficiales con más descuento. Toca «Comparar» para buscarlas en Instant Gaming.</p>
</div><ul class="spot-grid small ig-grid">{rows}</ul><div class="prose">
<p class="meta">Instant Gaming no es una tienda oficial de los juegos, sino un vendedor de claves. Los enlaces de esta página son de afiliado: si compras, recibimos una pequeña comisión sin costo para ti. No mostramos sus precios porque no tenemos una fuente oficial para verificarlos.</p></div>""",
                    crumbs=[("tiendas.html", "Tiendas"), ("instant-gaming.html", "Instant Gaming")])

    def share_whatsapp(self, o, name):
        import urllib.parse
        what = "gratis" if o.get("currentPrice") == 0 else f"-{o.get('discountPercentage') or 0}%"
        text = f"🎮 {o['title']} {what} en {o['store']}: {self.base + name}"
        return ('<p class="share-row">' + ext_link("https://wa.me/?text=" + urllib.parse.quote(text), "Compartir por WhatsApp", cls="btn btn-wa btn-sm",
                                                    label=f"Compartir {o['title']} por WhatsApp (abre WhatsApp)") + "</p>")

    def score_block(self, o):
        score = self.value_score(o)
        if score is None:
            return ""
        word = "Excelente" if score >= 75 else "Muy buena" if score >= 60 else "Buena" if score >= 45 else "Normal"
        mc = f"nota de la crítica {o['metacritic']}" if o.get("metacritic") else "sin nota de la crítica"
        return (f'<section class="score-box" aria-labelledby="score-h"><div class="score-num" aria-hidden="true">{score}</div>'
                f'<div><h2 id="score-h">Vale la pena: {word} ({score}/100)</h2><p class="meta">Nuestro puntaje combina el descuento '
                f'({o.get("discountPercentage") or 0}%), la {mc} y el precio en pesos. Es una guía rápida, no una reseña.</p></div></section>')

    def history_block(self, o):
        from . import history
        ps = self.price_stats(o)
        if not ps:
            return ""
        fmt = lambda v, cur: "Gratis" if v == 0 else money(v, cur)
        chart = history.chart_svg(ps["points"], o["currency"], fmt)
        since = day_es(ps["first"])
        if ps["days"] < history.MIN_DAYS_FOR_LOW:
            text = (f"Empezamos a seguir este precio el {e(since)}. En unas semanas aquí verás si el precio de hoy es bueno "
                    f"comparado con lo que hemos visto.")
        else:
            text = (f"Lo seguimos desde el {e(since)}. El precio más bajo que hemos visto en {e(o['store'])} es "
                    f"<strong>{e(fmt(ps['low'], o['currency']))}</strong> (el {e(day_es(ps['lowDate']))})."
                    + (" <strong>Hoy está en ese mínimo.</strong>" if ps["isLow"] else ""))
        return (f'<section class="history" aria-labelledby="hist-h"><h2 id="hist-h">{ICONS["clock"]} Historial de precio</h2>'
                f'<p>{text}</p>{chart}<p class="meta">Datos propios: guardamos el precio en cada revisión (cada 4 horas). '
                f'Antes de esa fecha no tenemos datos.</p></section>')

    def similar_offers(self, o, offers):
        """Otras ofertas parecidas: misma tienda o descuento parecido, con imagen (enlaces internos)."""
        words = {w for w in slugify_words(o["title"]) if len(w) > 3}
        def score(x):
            common = len(words & set(slugify_words(x["title"])))
            return (-common, x["storeId"] != o["storeId"], abs((x.get("discountPercentage") or 0) - (o.get("discountPercentage") or 0)))
        picks = sorted((x for x in offers if x["id"] != o["id"] and x["id"] in self.detail and x.get("image")), key=score)[:4]
        if not picks:
            return ""
        return (f'<section aria-labelledby="sim-h"><h2 id="sim-h">{ICONS["sparkle"]} También te puede interesar</h2>'
                f'<ul class="grid">{"".join(self.card(x) for x in picks)}</ul></section>')

    def offer_pages(self, offers, notice):

        for o in offers:
            name = self.detail.get(o["id"])
            if not name:
                continue
            free = o.get("currentPrice") == 0
            what = "gratis" if free else f"con {o.get('discountPercentage') or 0}% de descuento"
            until = f"Hasta el {date_es(o['expiresAt'])}" if o.get("expiresAt") else ""
            img = f'<img src="{e(o["image"])}"{fallback(o)} alt="Imagen de {e(o["title"])}" width="920" height="430" decoding="async">' if o.get("image") else ""
            btn = self.offer_button(o)
            search_note = ('<p class="meta">La tienda no da un enlace directo a este juego: el botón abre su buscador con el nombre.</p>'
                           if self.is_search(o) else "")
            ld = {"@context": "https://schema.org", "@type": "Product", "name": o["title"], "image": o.get("image") or None,
                  "offers": {"@type": "Offer", "price": o.get("currentPrice"), "priceCurrency": o["currency"],
                             "url": o["officialUrl"], "availability": "https://schema.org/InStock",
                             "seller": {"@type": "Organization", "name": o["store"]},
                             **({"priceValidUntil": o["expiresAt"][:10]} if o.get("expiresAt") else {})}}
            ld = {k: v for k, v in ld.items() if v is not None}
            self.layout(name, f"{o['title']} {what} en {o['store']}",
                        f"{o['title']} está {what} en {o['store']}. Precio, vigencia y enlace oficial verificados por Ofertas Gamer CO.",
                        f"""<article class="detail">
<div class="detail-media" id="trailer">{img}{self.badge(o)}{self.trailer_link(dict(o, url=f"https://store.steampowered.com/app/{o['steamAppID']}/" if o.get("steamAppID") else o["officialUrl"]))}</div>
<div class="detail-info">{self.store_chip(o)}
<h1>{e(o['title'])}</h1>
{f'<p class="lead about">{e(html.unescape(o["about"]))}</p>' if o.get("about") else ''}
{self.price_html(o, big=True)}
{self.countdown(o)}{f'<p class="meta">{e(until)}</p>' if until else ''}
{self.trust_chips(o, full=True)}
<div class="cta">{btn}<button class="btn icon-btn" type="button" data-fav="{e(o['id'])}" aria-pressed="false" aria-label="Guardar {e(o['title'])} en favoritos" hidden>{ICONS['star']}</button><a class="btn" href="ofertas.html">Ver más ofertas</a>{self.alert_button(o, "offer")}</div>
{search_note}<p class="meta">Verificado el {e(date_es(o['verifiedAt']))}.</p>
{self.share_whatsapp(o, name)}
{notice}</div></article>{self.shots_block(o)}{self.offer_buy(o)}{self.score_block(o)}{self.history_block(o)}{self.compare_block(o)}{self.similar_offers(o, offers)}""",
                        crumbs=[("ofertas.html", "Ofertas"), (name, o["title"])], jsonld=[ld], og_image=o.get("image"))

    @staticmethod
    def shots_block(g):
        """Capturas oficiales de Steam (la miniatura abre la imagen grande)."""
        shots = "".join(f'<li><a href="{e(u.replace(".600x338", ".1920x1080"))}" target="_blank" rel="noopener noreferrer">'
                        f'<img src="{e(u)}" alt="Captura {i + 1} de {e(g["title"])}" width="600" height="338" loading="lazy" decoding="async"></a></li>'
                        for i, u in enumerate(g.get("shots") or []) if u.startswith("https://"))
        return f'<section class="shots"><h2>{ICONS["sparkle"]} Capturas oficiales</h2><ul class="shot-grid">{shots}</ul></section>' if shots else ""

    @staticmethod
    def trailer_link(g):
        """Botón de play sobre la portada. Sin JavaScript abre el tráiler en Steam o YouTube."""
        t = g.get("trailer") or {}
        if t.get("video") or t.get("hls"):
            attrs = f'data-video="{e(t.get("video", ""))}" data-hls="{e(t.get("hls", ""))}" data-poster="{e(t.get("poster", ""))}"'
            href = g["url"]
        elif g.get("youtube"):
            attrs = f'data-yt="{e(g["youtube"])}"'
            href = f"https://www.youtube.com/watch?v={g['youtube']}"
        else:
            return ""
        return (f'<a class="play-btn" href="{e(href)}" target="_blank" rel="noopener noreferrer" {attrs} '
                f'aria-label="Ver el tráiler de {e(g["title"])}"><span class="play-ico">{ICONS["play"]}</span><span>Ver tráiler</span></a>')

    def game_pages(self, games, now):
        for g in games:
            name = self.detail.get(g["id"])
            if not name:
                continue
            src = "Steam" if g.get("source") != "wikidata" else "Wikidata"
            consoles = any(p in g.get("platforms", []) for p in ("PlayStation", "Xbox", "Switch"))
            when = date_label(g.get("date"), g.get("precision"))
            rel = relative_label(g.get("date"), g.get("precision"), now)
            img = (poster_bg(g) + f'<img{" class=\"poster\"" if is_poster(g["image"]) else ""} src="{e(g["image"])}"{fallback(g)} alt="Imagen de {e(g["title"])}" width="920" height="430" decoding="async">') if g.get("image") else no_cover(g, "no-cover big")
            tags = "".join(f'<span class="tag">{e(x)}</span>' for x in g.get("platforms", [])) + \
                "".join(f'<span class="tag genre">{e(x)}</span>' for x in g.get("genres", [])) + \
                ('<span class="tag es">En español</span>' if g.get("spanish") else "")
            extra = self.shots_block(g)
            if g.get("requirements"):
                extra += (f'<section class="reqs"><h2>{ICONS["check"]} Requisitos mínimos de PC</h2><ul>'
                          + "".join(f"<li>{e(ln)}</li>" for ln in g["requirements"].splitlines()) + '</ul><p class="meta">Según Steam. Pueden cambiar antes del lanzamiento.</p></section>')
            extra += self.similar_games(g, games)
            ld = {"@context": "https://schema.org", "@type": "VideoGame", "name": g["title"], "url": g["url"],
                  "gamePlatform": g.get("platforms"), "genre": g.get("genres")}
            if g.get("image"):
                ld["image"] = g["image"]
            if g.get("precision") == "day":
                ld["datePublished"] = g["date"]
            faq = self.game_faq(g, when)
            faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
            faq_html = ('<section class="faq game-faq"><h2>Preguntas sobre ' + e(g["title"]) + '</h2>'
                        + "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq) + "</section>")
            launch = ""
            if g.get("precision") == "day" and g["date"] >= now.astimezone(CO_TZ).strftime("%Y-%m-%d"):
                start = g["date"] + "T05:00:00Z"  # medianoche en Colombia
                gcal = ("https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + quote(f"Sale {g['title']}")
                        + f"&dates={g['date'].replace('-', '')}/{(datetime.strptime(g['date'], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y%m%d')}"
                        + "&details=" + quote(self.base + name))
                launch = (f'<div class="launch" data-launch="{start}" hidden><span class="launch-label">Faltan</span>'
                          f'<span class="launch-num" data-u="d">0</span><small>días</small><span class="launch-num" data-u="h">0</span><small>h</small>'
                          f'<span class="launch-num" data-u="m">0</span><small>min</small><span class="launch-num" data-u="s">0</span><small>s</small></div>'
                          + ext_link(gcal, f"{ICONS['calendar']} Agregar a Google Calendar", cls="btn btn-sm", label=f"Agregar el lanzamiento de {g['title']} a Google Calendar"))
            moved = ""
            if (g.get("dateChanged") or {}).get("from"):
                ch = g["dateChanged"]
                moved = f'<p class="notice moved">{ICONS["clock"]} <strong>Cambió la fecha.</strong> Antes: {e(date_label(ch["from"], ch.get("fromPrecision")))}. Ahora: {e(when)}.</p>'
            self.layout(name, f"{g['title']}: fecha de lanzamiento" + ("" if consoles else " en PC"),
                        f"Fecha de lanzamiento de {g['title']} ({', '.join(g.get('platforms', []))}): {when}. Plataformas, géneros y enlace.",
                        f"""<article class="detail">
<div class="detail-media" id="trailer">{img}{f'<span class="badge rel">{e(rel)}</span>' if rel else ''}{self.trailer_link(g)}</div>
<div class="detail-info">
<h1>{e(g['title'])}</h1>
<p class="detail-date">{ICONS["calendar"]} {e(when)}</p>
{launch}{moved}{self.price_line(g, now)}
<div class="tags">{tags}</div>
{f'<p class="lead">{e(g["description"])}</p>' if g.get("description") else ''}
<div class="cta">{self.game_link(g, cls="btn btn-primary")}<a class="btn" href="lanzamientos.html">Ver calendario</a>{self.alert_button(g, "game") if g.get("comingSoon") else ""}
<button class="btn icon-btn" type="button" data-follow="{e(g['id'])}" aria-pressed="false" aria-label="Seguir {e(g['title'])}" hidden>{ICONS["bell"]} Seguir</button></div>
<p class="meta">La fecha es la que publica {src} y puede cambiar.{' Resumen e imagen: Wikipedia en español (CC BY-SA 4.0).' if src == "Wikidata" and g.get("description") else ''} Verificado: {e(date_es(g.get('verifiedAt')))}.</p></div></article>{self.buy_block(g['title'], [(g.get('store') or 'Steam', self.price_text(g, now), g.get('url'))])}{extra}{faq_html}""",
                        crumbs=[("lanzamientos.html", "Lanzamientos"), (name, g["title"])], jsonld=[ld, faq_ld], og_image=g.get("image"))

    def similar_games(self, g, games):
        """Juegos parecidos: comparten género y plataforma; primero los más esperados."""
        gens, plats = set(g.get("genres", [])), set(g.get("platforms", []))
        if not gens:
            return ""
        pool = [x for x in games if x["id"] != g["id"] and x["id"] in self.detail and set(x.get("genres", [])) & gens]
        sale = lambda x: not (self.live_price(x, self.now) or {}).get("discount")  # primero los que están en oferta en Steam
        pool.sort(key=lambda x: (-len(set(x.get("genres", [])) & gens), sale(x), -len(set(x.get("platforms", [])) & plats), self.rank(x)))
        picks = pool[:4]
        if not picks:
            return ""
        return (f'<section class="similar"><h2>{ICONS["sparkle"]} Si te gusta {e(g["title"])}, mira estos</h2>'
                f'<ul class="spot-grid small">{"".join(self.spot_card(x, self.now) for x in picks)}</ul></section>')

    def game_faq(self, g, when):
        """Preguntas frecuentes de un juego, respondidas solo con los datos que tenemos."""
        t = g["title"]
        plats = g.get("platforms", [])
        names = {"Windows": "PC (Windows)", "PlayStation": "PlayStation", "Xbox": "Xbox", "Switch": "Nintendo Switch", "Mac": "Mac", "Linux": "Linux"}
        nice = [names.get(p, p) for p in plats]
        src = "Steam" if g.get("source") != "wikidata" or g.get("store") == "Steam" else "Wikipedia"
        out = [(f"¿Cuándo sale {t}?", (f"La fecha publicada es: {when}. " if g.get("date") else "Todavía no tiene una fecha exacta confirmada. ")
                + f"Dato de {src}; las fechas pueden cambiar y aquí se actualizan cada 4 horas.")]
        if nice:
            out.append((f"¿En qué plataformas sale {t}?", f"Según los datos publicados: {', '.join(nice)}."))
            out.append((f"¿{t} sale en PC?", "Sí, aparece para PC (Windows)." if "Windows" in plats else
                        "Por ahora no aparece una versión para PC en los datos publicados. Si se anuncia, se verá aquí."))
        if g.get("genres"):
            out.append((f"¿Qué tipo de juego es {t}?", f"Es un juego de {', '.join(x.lower() for x in g['genres'])}."))
        if "spanish" in g:
            out.append((f"¿{t} está en español?", "Sí: Steam lo lista con idioma español." if g["spanish"] else
                        "Por ahora Steam no lo lista con idioma español. Puede cambiar cuando salga."))
        t2 = g.get("trailer") or {}
        if t2 or g.get("youtube"):
            out.append((f"¿Dónde veo el tráiler de {t}?", "Arriba en esta página: toca el botón de play sobre la imagen."))
        return out

    # ---------- calendario de lanzamientos ----------
    @staticmethod
    def split_releases(games, now):
        today = now.strftime("%Y-%m-%d")
        dated = [g for g in games if g.get("date")]
        upcoming = sorted([g for g in dated if g["date"] >= today or g.get("precision") == "month" and g["date"][:7] >= today[:7]],
                          key=lambda g: (g["date"], g.get("precision") != "day", g["title"]))
        recent = sorted([g for g in dated if g not in upcoming], key=lambda g: g["date"], reverse=True)
        tba = sorted([g for g in games if not g.get("date")], key=lambda g: g["title"])
        return upcoming, recent, tba

    @staticmethod
    def game_link(g, text=None, cls="btn btn-primary btn-sm"):
        where = g.get("store") or "Steam"
        label = text or f"Ver en {where}"
        return ext_link(g["url"], label, cls=cls, label=f"Ver {g['title']} en {where} (abre en otra pestaña)")

    @staticmethod
    def preview_attrs(t):
        """Atributos para el avance al pasar el cursor (solo tráileres de Steam: HLS o MP4)."""
        t = t or {}
        hls = t.get("hls") if (t.get("hls") or "").startswith("https://") else ""
        video = t.get("video") if (t.get("video") or "").startswith("https://") else ""
        if not (hls or video):
            return ""
        return f' data-preview="1"' + (f' data-hls="{e(hls)}"' if hls else "") + (f' data-video="{e(video)}"' if video else "")

    def trailer_chip(self, g):
        page = self.detail.get(g["id"])
        if not page or not ((g.get("trailer") or {}).get("video") or (g.get("trailer") or {}).get("hls") or g.get("youtube")):
            return ""
        return f'<a class="trailer-chip" href="{page}#trailer" aria-label="Tráiler de {e(g["title"])}">{ICONS["play"]}</a>'

    def rank(self, g):
        return getattr(self, "ranks", {}).get(g["id"], 9999)

    @staticmethod
    def live_price(g, now):
        """Precio de Steam Colombia revisado en las últimas 12 horas (si es más viejo no se muestra)."""
        p = g.get("price") or {}
        if not p.get("final") or not p.get("at"):
            return None
        return p if p["at"] >= (now - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ") else None

    def release_card(self, g, now, compact=True, big=False):
        hot = self.rank(g) <= 25
        img = g.get("image") or "assets/placeholder.svg"
        alt = f"Imagen de {g['title']}" if g.get("image") else ""
        plats = "".join(f'<span class="ver">{e(p)}</span>' for p in g.get("platforms", []))
        genres = "".join(f'<span class="tag genre">{e(x)}</span>' for x in g.get("genres", [])[:2])
        rel = relative_label(g.get("date"), g.get("precision"), now)
        when = date_label(g.get("date"), g.get("precision"))
        link = self.game_link(g, g.get("store") or "Steam")
        return f"""<li class="rel-card{' is-hot' if hot else ''}{' is-big' if big else ''}" data-id="{e(g['id'])}" data-title="{e(g['title'].lower())}" data-date="{e(g.get('date') or '')}" data-precision="{e(g.get('precision') or '')}" data-platforms="{e('|'.join(g.get('platforms', [])))}" data-genres="{e('|'.join(g.get('genres', [])))}">
<div class="rel-img"{self.preview_attrs(g.get("trailer"))}>{(poster_bg(g) + f'<img{" class=\"poster\"" if is_poster(img) else ""} src="{e(img)}"{fallback(g)} alt="{e(alt)}" width="460" height="215" loading="lazy" decoding="async">') if g.get("image") else no_cover(g)}{f'<span class="badge rel">{e(rel)}</span>' if rel and not compact else ''}{f'<span class="hot-tag">{ICONS["flame"]} Muy esperado</span>' if hot else ''}{self.trailer_chip(g)}{f'<span class="badge sale-tag">-{self.live_price(g, now)["discount"]}%</span>' if (self.live_price(g, now) or {}).get("discount") else ''}</div>
<p class="rel-name">{self.title_link(g)}</p>
<p class="rel-vers"><span class="rel-type" aria-hidden="true">{ICONS["pad"]}</span>{plats}</p>
{'' if compact else f'<p class="meta">{e(when)}</p>'}
<div class="tags">{genres}</div>
<div class="rel-actions">{link}<button class="btn btn-sm icon-btn" type="button" data-follow="{e(g['id'])}" aria-pressed="false" aria-label="Seguir {e(g['title'])}" hidden>{ICONS["bell"]}</button></div></li>"""

    def is_big(self, g, pos, count):
        """Estilo calendario de releases: el más esperado de cada día va en grande (y el segundo si es muy esperado)."""
        return (pos == 0 and (count >= 3 or self.rank(g) <= 150)) or (pos == 1 and self.rank(g) <= 60)

    def release_groups(self, games, now, title, anchor, compact=True):
        if not games:
            return ""
        groups, order = {}, []
        for g in games:
            key = g.get("date") if g.get("precision") == "day" else (g.get("date") or "")[:7] or "tba"
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(g)
        out = []
        for key in order:
            items = sorted(groups[key], key=self.rank)  # dentro del día, primero los más esperados
            if key == "tba":
                big, label, rel = "Por confirmar", "Fecha por confirmar", ""
            elif len(key) == 7:
                y, m = int(key[:4]), int(key[5:7])
                big = f"{MONTHS_ES[m - 1].capitalize()} {y}"
                label, rel = f"{MONTHS_ES[m - 1].capitalize()} de {y}", "día por confirmar"
            else:
                d, m = int(key[8:10]), int(key[5:7])
                big = f"{d} {MONTHS_ES[m - 1][:3]}"
                label, rel = date_label(key, "day"), relative_label(key, "day", now)
            kind = "past" if rel.startswith("hace") or rel == "ayer" else "today" if rel == "hoy" else "future"
            out.append(f'<section class="rel-day {kind}"{f' id="dia-{key}"' if len(key) == 10 and not compact else ''} aria-label="{e(label)}"><h3 class="rel-head">'
                       f'<span class="rel-dot" aria-hidden="true"></span><span class="rel-big">{e(big)}</span>'
                       f'<span class="rel-sub">{e(rel)}</span><span class="rel-line" aria-hidden="true"></span>'
                       f'<span class="rel-crumb">Juegos · {len(items)}</span></h3>'
                       f'<ul class="rel-grid">{"".join(self.release_card(g, now, compact, big=self.is_big(g, i, len(items))) for i, g in enumerate(items))}</ul></section>')
        return f'<div class="rel-block" id="{anchor}"><h2>{e(title)}</h2>' + "".join(out) + "</div>"

    def spot_card(self, g, now, main=False):
        img = g.get("image") or "assets/placeholder.svg"
        rel = relative_label(g.get("date"), g.get("precision"), now)
        when = date_label(g.get("date"), g.get("precision"))
        genres = "".join(f'<span class="tag genre">{e(x)}</span>' for x in g.get("genres", [])[:3])
        desc = g.get("description") or ""
        if len(desc) > (260 if main else 120):
            desc = desc[:(257 if main else 117)].rsplit(" ", 1)[0] + "…"
        link = self.game_link(g)
        bg = (f'<img class="spot-bg" src="{e(img)}"{fallback(g)} alt="" width="460" height="215" loading="lazy" decoding="async">' if main and g.get("image")
              else poster_bg(g))
        fg = (f'<img class="spot-fg{' poster' if is_poster(img) else ''}" src="{e(img)}"{fallback(g)} alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async">'
              if g.get("image") else no_cover(g, "no-cover spot-fg"))
        return f"""<li class="spot-card{' spot-main' if main else ''}"><div class="spot-img"{self.preview_attrs(g.get("trailer"))}>{bg}{fg}<span class="spot-rank">#{self.rank(g)}</span>{self.trailer_chip(g)}{f'<span class="badge rel">{e(rel)}</span>' if rel else ''}</div>
<div class="spot-body"><p class="spot-date">{ICONS['calendar']}{e(when)}</p><h3 class="clamp2">{self.title_link(g)}</h3>{f'<p class="spot-desc">{e(desc)}</p>' if desc else ''}<div class="tags">{genres}</div>
<div class="rel-actions">{link}<button class="btn btn-sm icon-btn" type="button" data-follow="{e(g['id'])}" aria-pressed="false" aria-label="Seguir {e(g['title'])}" hidden>{ICONS['bell']}</button></div></div></li>"""

    @staticmethod
    def mega(words, reverse=False):
        """Letras gigantes de fondo que se deslizan al bajar (solo decoración)."""
        line = " · ".join(words) + " · "
        return (f'<div class="mega{" rev" if reverse else ""}" aria-hidden="true"><div class="mega-track">'
                f'<span>{e(line)}</span><span>{e(line)}</span><span class="out">{e(line)}</span></div></div>')

    def curve_carousel(self, games, now, count=12):
        """Carrusel 3D curvo con los juegos más esperados (se arrastra o se mueve con las flechas)."""
        soon = sorted([g for g in games if g.get("comingSoon") and g.get("image")], key=self.rank)[:count]
        if len(soon) < 5:
            return ""
        items = "".join(
            f'<li class="curve-item"><a href="{e(self.detail.get(g["id"]) or g["url"])}"{"" if self.detail.get(g["id"]) else " target=\"_blank\" rel=\"noopener noreferrer\""}>'
            f'<span class="curve-img"{self.preview_attrs(g.get("trailer"))}><img src="{e(g["image"])}"{fallback(g)} alt="" width="460" height="215" loading="lazy" decoding="async"></span>'
            f'<span class="curve-name">{e(g["title"])}</span><span class="curve-date">{e(date_label(g.get("date"), g.get("precision")) if g.get("date") else "Fecha por confirmar")}</span></a></li>'
            for g in soon)
        return (f'<section class="curve" aria-labelledby="curve-h"><div class="sec-head"><h2 id="curve-h">{ICONS["arrive"]} Llegadas: los más esperados</h2>'
                f'<p class="meta">Arrastra o usa las flechas. <a href="lanzamientos.html">Ver el calendario</a></p></div>'
                f'<div class="curve-stage"><ul class="curve-track">{items}</ul>'
                f'<button type="button" class="curve-nav prev" aria-label="Anterior">{ICONS["chevL"]}</button><button type="button" class="curve-nav next" aria-label="Siguiente">{ICONS["chevR"]}</button></div></section>')

    def spotlight(self, games, now, days=30, count=8):
        """Los más esperados que salen en los próximos días (popularidad de Steam y Wikidata)."""
        today = now.strftime("%Y-%m-%d")
        limit = (now + timedelta(days=days)).strftime("%Y-%m-%d")
        soon = sorted([g for g in games if g.get("date") and g.get("precision") == "day" and today <= g["date"] <= limit],
                      key=self.rank)[:count]
        if not soon:
            return ""
        return (f'<section class="spot" aria-labelledby="spot-h"><div class="sec-head"><h2 id="spot-h">{ICONS["flame"]} Lo más esperado del mes</h2>'
                f'<p class="meta">Los {len(soon)} lanzamientos más populares de los próximos {days} días (PC y consolas).</p></div>'
                f'<ul class="spot-grid">{"".join(self.spot_card(g, now, i == 0) for i, g in enumerate(soon))}</ul></section>')

    def anticipated(self, games, now, count=8):
        """Los grandes que vienen después de este mes (o sin fecha exacta), por popularidad."""
        limit = (now + timedelta(days=30)).strftime("%Y-%m-%d")
        later = sorted([g for g in games if g.get("comingSoon") and (not g.get("date") or g["date"] > limit)], key=self.rank)[:count]
        if not later:
            return ""
        return (f'<section class="spot" aria-labelledby="ant-h"><div class="sec-head"><h2 id="ant-h">{ICONS["star"]} Los más esperados que vienen</h2>'
                f'<p class="meta">Los juegos más populares de los próximos meses. Algunos aún no tienen fecha exacta.</p></div>'
                f'<ul class="spot-grid small">{"".join(self.spot_card(g, now) for g in later)}</ul></section>')

    def releases_page(self, games, now, updated_line):
        upcoming, recent, tba = self.split_releases(games, now)
        credit = ('<p class="meta">Fuentes: Steam y <a href="https://www.wikidata.org/" target="_blank" rel="noopener noreferrer">Wikidata</a> '
                  '(la base de datos de Wikipedia).</p>') if any(g.get("source") == "wikidata" for g in games) else ""
        genres = sorted({x for g in games for x in g.get("genres", [])})
        chip = lambda kind, v: f'<button type="button" class="chip" data-{kind}="{e(v)}" aria-pressed="false">{e(v)}</button>'
        toolbar = f"""<div class="rel-toolbar" id="rel-toolbar" hidden>
<div class="tabs" role="group" aria-label="Periodo">
<button type="button" class="tab" data-view="hot" aria-pressed="true">{ICONS["flame"]} Destacados</button>
<button type="button" class="tab" data-view="week" aria-pressed="false">Esta semana</button>
<button type="button" class="tab" data-view="month" aria-pressed="false">Este mes</button>
<button type="button" class="tab" data-view="all" aria-pressed="false">Todo</button>
<button type="button" class="tab" data-view="follow" aria-pressed="false">{ICONS["bell"]} Siguiendo</button>
</div>
<label class="rel-search"><span class="sr-only">Buscar juego</span><input type="search" id="rel-q" placeholder="Buscar juego…" autocomplete="off"></label>
<div class="chips" role="group" aria-label="Sistema">{''.join(chip('platform', x) for x in ('Windows', 'PlayStation', 'Xbox', 'Switch', 'Mac', 'Linux') if any(x in g.get('platforms', []) for g in games))}</div>
<div class="chips" role="group" aria-label="Género">{''.join(chip('genre', x) for x in genres)}</div>
</div>"""
        body = (self.release_groups(upcoming, now, "Próximos lanzamientos", "proximos") +
                self.release_groups(recent, now, "Lanzados recientemente", "recientes") +
                self.release_groups(tba, now, "Fecha por confirmar", "por-confirmar"))
        ld = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": g["title"], "url": g["url"]} for i, g in enumerate(upcoming[:30])]}
        self.layout("lanzamientos.html", "Calendario de lanzamientos de juegos de PC",
                    "Próximos lanzamientos y estrenos recientes de juegos de PC y consolas, con la fecha que publica la tienda, plataformas y géneros.",
                    self.mega(["ESTRENOS", "PC", "PLAYSTATION", "XBOX", "SWITCH"]) + f"""<div class="rel-top"><div><h1>Calendario de <span class="grad">lanzamientos</span></h1>
<p class="lead">Los próximos juegos de PC y consolas y los estrenos recientes, día por día. Las fechas son las que publica cada tienda y pueden cambiar.</p>
{updated_line}</div></div>
{self.spotlight(games, now)}
{self.anticipated(games, now)}
{self.calendar_links()}
{self.heatmap(games, now)}
<h2 class="all-rel">Calendario completo</h2>
{toolbar}
<p class="count" id="rel-count" aria-live="polite">{len(games)} juegos</p>
<div id="rel-list">{body or '<p class="notice">Todavía no hay lanzamientos cargados. Vuelve en unas horas.</p>'}</div>
<div class="rel-more" id="rel-more" hidden><p class="meta" id="rel-more-txt"></p><button type="button" class="btn btn-primary" id="rel-more-btn">Cargar más juegos</button></div>
<p class="notice" id="rel-empty" hidden>No hay juegos con estos filtros. Prueba con «Todo» o quita algún filtro.</p>
<section class="rel-end" id="rel-end"><h2>{ICONS["calendar"]} Sigue explorando</h2><p class="meta">Cada mes tiene su propia página con todos sus estrenos, y puedes pasar de un mes al siguiente.</p>
<nav class="chips" aria-label="Más calendarios">{"".join(f'<a class="chip" href="{n}">{e(label)} <span class="meta">({c})</span></a>' for n, label, c in getattr(self, "release_links", []))}</nav></section>{credit}""",
                    crumbs=[("lanzamientos.html", "Lanzamientos")], jsonld=[ld])

    def today_releases(self, games, now):
        today = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        hoy = sorted([g for g in games if g.get("precision") == "day" and g.get("date") == today], key=self.rank)[:8]
        if not hoy:
            return ""
        return (f'<section class="today-rel"><h2>{ICONS["arrive"]} Aterrizan hoy</h2><ul class="spot-grid small">'
                + "".join(self.spot_card(g, now) for g in hoy) + "</ul></section>")

    def note_row(self, it, kind, now):
        """Una línea de las notas de novedades: miniatura, nombre, etiqueta y enlace."""
        img = it.get("imageSmall") or it.get("image") or "assets/placeholder.svg"
        if kind == "game":
            tag = '<span class="n-tag rel">Estreno</span>' if it["date"] <= now.strftime("%Y-%m-%d") else '<span class="n-tag soon">Próximamente</span>'
            sub = e(" · ".join(it.get("platforms", [])[:3] + it.get("genres", [])[:2]))
            go = self.game_link(it, cls="btn btn-sm")
        else:
            free = it.get("currentPrice") == 0
            tag = '<span class="n-tag free">GRATIS</span>' if free else f'<span class="n-tag">-{it.get("discountPercentage") or 0}%</span>'
            price = "Gratis" if free else money(it["currentPrice"], it["currency"])
            sub = f'{e(it["store"])} · <strong>{e(price)}</strong>' + (f' <s>{e(money(it["originalPrice"], it["currency"]))}</s>' if it.get("originalPrice") and not free else "")
            go = ext_link(it["destinationUrl"], self.action_label(it), it.get("affiliate"), cls="btn btn-sm" + (" btn-free" if free else ""),
                          label=f"{self.action_label(it)}: {it['title']} (abre en otra pestaña)")
        return (f'<li class="n-row"><img src="{e(img)}" alt="" width="120" height="56" loading="lazy" decoding="async">'
                f'<div class="n-main"><p class="n-title">{tag}{self.title_link(it)}</p><p class="n-sub">{sub}</p></div>{go}</li>')

    def gift_row(self, g):
        img = g.get("image") if (g.get("image") or "").startswith("https://") else "assets/placeholder.svg"
        name = dict((k, n) for k, n, _ in giveaways.GROUPS).get(g["group"], "")
        sub = " · ".join(x for x in (name if g["group"] != "otros" else g.get("platforms", ""), giveaways.TYPES.get(g["type"], ""),
                                      f"hasta el {day_es(g['endsOn'])}" if g.get("endsOn") else "") if x)
        go = (ext_link(g["url"], "Reclamar", cls="btn btn-sm btn-free", label=f"Reclamar {g['title']} gratis (abre en otra pestaña)")
              if g.get("active") else '<span class="n-tag">Terminó</span>')
        return (f'<li class="n-row"><img src="{e(img)}" alt="" width="120" height="56" loading="lazy" decoding="async">'
                f'<div class="n-main"><p class="n-title"><span class="n-tag free">GRATIS</span>{e(g["title"])}</p><p class="n-sub">{e(sub)}</p></div>{go}</li>')

    def news_page(self, live, games, now, updated_line):
        def co_day(value):
            dt = parse_iso(value) if value else None
            return dt.astimezone(CO_TZ).strftime("%Y-%m-%d") if dt else ""

        def day_name(key):
            y, m, d = (int(x) for x in key.split("-"))
            return f"{d} de {MONTHS_ES[m - 1]} de {y}"
        today = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        days = {}
        for o in live:
            days.setdefault(co_day(o.get("createdAt")), {"free": [], "deals": [], "games": []})[
                "free" if o.get("currentPrice") == 0 else "deals"].append(o)
        for g in games:
            if g.get("precision") == "day" and g.get("date") and g["date"] <= today:
                days.setdefault(g["date"], {"free": [], "deals": [], "games": []})["games"].append(g)
        for g in getattr(self, "giveaways", []):
            days.setdefault(co_day(g.get("firstSeen")), {"free": [], "deals": [], "games": []}).setdefault("gifts", []).append(g)
        notes = []
        for key in sorted((k for k in days if k), reverse=True)[:10]:
            d = days[key]
            deals = sorted(d["deals"], key=lambda o: -(o.get("discountPercentage") or 0))
            rel = sorted(d["games"], key=self.rank)
            parts = []
            if d["free"]:
                parts.append(f'<section class="n-sec"><h3>{ICONS["gift"]} Juegos gratis nuevos</h3><ul>' +
                             "".join(self.note_row(o, "offer", now) for o in d["free"]) + "</ul></section>")
            gifts = d.get("gifts", [])
            if gifts:
                parts.append(f'<section class="n-sec"><h3>{ICONS["gift"]} Regalos en otras tiendas</h3><ul>' +
                             "".join(self.gift_row(g) for g in gifts[:10]) + "</ul></section>")
            if rel:
                parts.append(f'<section class="n-sec"><h3>{ICONS["sparkle"]} Estrenos</h3><ul>' +
                             "".join(self.note_row(g, "game", now) for g in rel[:8]) + "</ul></section>")
            if deals:
                more = f'<p class="n-more"><a href="ofertas.html">Y {len(deals) - 10} ofertas más</a></p>' if len(deals) > 10 else ""
                parts.append(f'<section class="n-sec"><h3>{ICONS["flame"]} Nuevas ofertas</h3><ul>' +
                             "".join(self.note_row(o, "offer", now) for o in deals[:10]) + f"</ul>{more}</section>")
            counts = " · ".join(x for x in (
                f"{len(d['free']) + len(gifts)} gratis" if d["free"] or gifts else "", f"{len(rel)} estrenos" if rel else "",
                f"{len(deals)} ofertas" if deals else "") if x)
            label = "Hoy" if key == today else day_name(key)
            notes.append(f'<article class="note"><header class="note-head"><span class="note-ver">{ICONS["news"]}</span>'
                         f'<div><h2>{e(label)}</h2><p class="meta">{e(day_name(key)) if key == today else ""}{" · " if key == today else ""}{e(counts)}</p></div></header>{"".join(parts)}</article>')
        week_end = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        coming = sorted([g for g in games if g.get("precision") == "day" and g.get("date") and today < g["date"] <= week_end], key=self.rank)[:6]
        coming_html = (f'<section class="spot" aria-labelledby="coming-h"><div class="sec-head"><h2 id="coming-h">{ICONS["calendar"]} Llegan esta semana</h2>'
                       f'<p class="meta">Los más esperados de los próximos 7 días. <a href="lanzamientos.html">Ver el calendario</a></p></div>'
                       f'<ul class="spot-grid small">{"".join(self.spot_card(g, now) for g in coming)}</ul></section>') if coming else ""
        self.layout("noticias.html", "Novedades: juegos gratis, ofertas nuevas y estrenos de PC",
                    "Las novedades de cada día en Ofertas Gamer CO: juegos gratis nuevos, estrenos de PC y las ofertas que acaban de aparecer.",
                    f'<h1>Novedades</h1><p class="lead">Cada día, como unas notas de parche: juegos gratis nuevos, estrenos y las ofertas que acaban de aparecer.</p>{updated_line}'
                    f'{coming_html}<div class="notes">{"".join(notes) or "<p>Todavía no hay novedades registradas.</p>"}</div>',
                    crumbs=[("noticias.html", "Novedades")])

    def collection_pages(self, live, games, now, updated_line, notice):
        """Páginas de temas que la gente busca en Google, armadas solo con datos reales del día."""
        deals = [o for o in live if o.get("currentPrice")]
        cop = lambda o: o.get("copApproximation") if o.get("currency") == "USD" else o.get("currentPrice")
        cheap = sorted([o for o in deals if cop(o) and cop(o) < 20000], key=lambda o: -(o.get("discountPercentage") or 0))
        huge = sorted([o for o in deals if (o.get("discountPercentage") or 0) >= 90], key=lambda o: -(o.get("discountPercentage") or 0))
        soon_limit = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ending = sorted([o for o in live if o.get("expiresAt") and o["expiresAt"] <= soon_limit], key=lambda o: o["expiresAt"])
        under = lambda limit: sorted([o for o in deals if cop(o) and cop(o) < limit], key=lambda o: -(self.value_score(o) or 0))
        rated = sorted([o for o in deals if (o.get("metacritic") or 0) >= 75], key=lambda o: (-(o.get("metacritic") or 0), -(o.get("discountPercentage") or 0)))
        lows = [o for o in deals if (self.price_stats(o) or {}).get("isLow")]
        pages = [
            ("juegos-baratos.html", "Juegos de PC baratos en pesos colombianos", "Juegos de PC por menos de $20.000 COP",
             "Juegos de PC en oferta que cuestan menos de $20.000 pesos colombianos (valor aproximado), en tiendas oficiales.", cheap),
            ("juegos-menos-de-5000-pesos.html", "Juegos de PC por menos de $5.000 pesos", "Juegos por menos de $5.000 COP",
             "Juegos de PC en oferta por menos de $5.000 pesos colombianos (valor aproximado), en tiendas oficiales.", under(5000)),
            ("juegos-menos-de-10000-pesos.html", "Juegos de PC por menos de $10.000 pesos", "Juegos por menos de $10.000 COP",
             "Juegos de PC en oferta por menos de $10.000 pesos colombianos (valor aproximado), en tiendas oficiales.", under(10000)),
            ("juegos-menos-de-40000-pesos.html", "Juegos de PC por menos de $40.000 pesos", "Juegos por menos de $40.000 COP",
             "Juegos de PC en oferta por menos de $40.000 pesos colombianos (valor aproximado), ordenados por los que más valen la pena.", under(40000)),
            ("ofertas-mejor-valoradas.html", "Ofertas de juegos con mejor nota de la crítica", "Ofertas con mejor nota de la crítica",
             "Juegos en oferta con nota de Metacritic de 75 o más: buenos juegos a buen precio.", rated),
            ("minimos-historicos.html", "Juegos en su precio más bajo", "Juegos en su precio más bajo visto",
             "Ofertas que hoy están en el precio más bajo que hemos visto desde que las seguimos (con al menos dos semanas de datos propios).", lows),
            ("ofertas-90-por-ciento.html", "Juegos con 90% de descuento o más", "Juegos con 90% de descuento o más",
             "Los descuentos más grandes del día en tiendas oficiales de PC: 90% o más.", huge),
            ("ofertas-terminan-pronto.html", "Ofertas de juegos que terminan pronto", "Ofertas que terminan esta semana",
             "Juegos gratis y descuentos con fecha de fin en los próximos 7 días. Aprovecha antes de que terminen.", ending),
        ]
        for st in self.stores.values():
            mine = [o for o in live if o["storeId"] == st["id"]]
            if st["active"] and mine:
                extra = " Los juegos de GOG no tienen DRM: el instalador es tuyo para siempre." if st["id"] == "gog" else ""
                # Título según búsquedas reales (vidIQ, 2026-10-27: "mejores ofertas steam" +80% en el mes).
                title = "Mejores ofertas de Steam hoy" if st["id"] == "steam" else f"Ofertas de {st['name']} hoy"
                pages.append((f"ofertas-{st['id']}.html", title, f"Ofertas de {st['name']}",
                              f"Juegos gratis y descuentos de {st['name']} verificados, con precio en pesos aproximado.{extra}", mine))
        for name, title, h1, desc, items in pages:
            body = (f'<h1>{e(h1)}</h1><p class="lead">{e(desc)}</p>{updated_line}{notice}'
                    + (self.offer_list(items) if items else '<p class="notice">Hoy no hay ofertas en esta categoría. Se revisa cada 4 horas.</p>')
                    + '<p><a href="ofertas.html">Ver todas las ofertas</a></p>')
            self.layout(name, title, desc, body, crumbs=[(name, h1)], jsonld=[self.item_list_ld(items)] if items else None)

        today = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        upcoming = [g for g in games if g.get("comingSoon") or (g.get("date") or "") >= today]
        for slug, plat, label in (("playstation", "PlayStation", "PlayStation (PS5 y PS4)"), ("xbox", "Xbox", "Xbox (Series X|S y One)"),
                                  ("switch", "Switch", "Nintendo Switch"), ("pc", "Windows", "PC")):
            mine = [g for g in upcoming if plat in g.get("platforms", [])]
            dated = sorted([g for g in mine if g.get("date")], key=lambda g: (g["date"], self.rank(g)))
            tba = sorted([g for g in mine if not g.get("date")], key=self.rank)
            name = f"lanzamientos-{slug}.html"
            top = sorted(mine, key=self.rank)[:8]
            spot = (f'<section class="spot"><div class="sec-head"><h2>{ICONS["flame"]} Los más esperados de {e(label)}</h2></div>'
                    f'<ul class="spot-grid small">{"".join(self.spot_card(g, now) for g in top)}</ul></section>') if top else ""
            body = (f'<h1>Próximos lanzamientos de {e(label)}</h1><p class="lead">Los juegos que salen para {e(label)}, día por día. '
                    f'Las fechas son las que publican las tiendas y Wikipedia, y pueden cambiar.</p>{updated_line}{spot}'
                    + self.release_groups(dated, now, "Calendario", f"cal-{slug}", compact=False)
                    + self.release_groups(tba, now, "Fecha por confirmar", f"tba-{slug}", compact=False)
                    + '<p><a class="btn" href="lanzamientos.html">Ver el calendario completo</a></p>')
            self.layout(name, f"Próximos lanzamientos de {label}: calendario {now.year}",
                        f"Calendario de próximos juegos para {label}: fechas de lanzamiento, géneros y tráileres.",
                        body, crumbs=[("lanzamientos.html", "Lanzamientos"), (name, label)])

    def release_extra_pages(self, games, now, updated_line):
        """Páginas por mes, por año y por género, y el calendario para el celular (.ics). Solo fechas publicadas."""
        from .model import slugify
        today = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        links = []
        # por mes: el anterior, el actual y los siguientes (hasta 18), encadenados con «mes anterior / siguiente»
        y, m = int(today[:4]), int(today[5:7])
        months = []
        for i in range(-1, 18):
            yy, mm = y + (m - 1 + i) // 12, (m - 1 + i) % 12 + 1
            key = f"{yy}-{mm:02d}"
            mine = [g for g in games if (g.get("date") or "")[:7] == key]
            if mine:
                months.append((yy, mm, key, mine, f"juegos-que-salen-en-{MONTHS_ES[mm - 1]}-{yy}.html"))
        for idx, (yy, mm, key, mine, name) in enumerate(months):
            month = MONTHS_ES[mm - 1]
            links.append((name, f"{month.capitalize()} {yy}", len(mine)))
            pager = ""
            for side, j in (("prev", idx - 1), ("next", idx + 1)):
                if 0 <= j < len(months):
                    py, pm, _, pmine, pname = months[j]
                    arrow = "← " if side == "prev" else ""
                    tail = " →" if side == "next" else ""
                    pager += (f'<a class="month-{side}" href="{pname}"><span class="meta">{"Mes anterior" if side == "prev" else "Sigue explorando"}</span>'
                              f'<strong>{arrow}{MONTHS_ES[pm - 1].capitalize()} {py}{tail}</strong><span class="meta">{len(pmine)} juegos</span></a>')
            pager = f'<nav class="month-pager" aria-label="Otros meses">{pager}</nav>' if pager else ""
            dated = sorted([g for g in mine if g.get("precision") == "day"], key=lambda g: (g["date"], self.rank(g)))
            undated = sorted([g for g in mine if g.get("precision") != "day"], key=self.rank)
            top = sorted(mine, key=self.rank)[:8]
            spot = (f'<section class="spot"><div class="sec-head"><h2>{ICONS["flame"]} Los más esperados de {e(month)}</h2></div>'
                    f'<ul class="spot-grid small">{"".join(self.spot_card(g, now) for g in top)}</ul></section>')
            body = (f'<h1>Juegos que salen en {e(month)} de {yy}</h1><p class="lead">{len(mine)} lanzamientos de PC y consolas en {e(month)}, '
                    f'día por día, con tráiler cuando lo hay. Las fechas son las que publican las tiendas y Wikipedia, y pueden cambiar.</p>'
                    f'{updated_line}{spot}' + self.release_groups(dated, now, f"Calendario de {month}", f"cal-{key}", compact=False)
                    + self.release_groups(undated, now, f"En {month}, día por confirmar", f"mes-{key}", compact=False)
                    + pager + '<p><a class="btn" href="lanzamientos.html">Ver el calendario completo</a></p>')
            self.layout(name, f"Juegos que salen en {month} de {yy}: lanzamientos de PC y consolas",
                        f"Todos los juegos que salen en {month} de {yy} para PC, PlayStation, Xbox y Nintendo Switch: fechas, tráileres y los más esperados.",
                        body, crumbs=[("lanzamientos.html", "Lanzamientos"), (name, f"{month.capitalize()} {yy}")],
                        jsonld=[self.games_list_ld(top)])
        # por año: los más esperados de este año y del siguiente
        for yy in (y, y + 1):
            mine = [g for g in games if (g.get("date") or "")[:4] == str(yy) or (not g.get("date") and str(yy) in (g.get("releaseText") or ""))]
            mine = [g for g in mine if (g.get("date") or "9999") >= today]
            if len(mine) < 4:
                continue
            name = f"juegos-mas-esperados-{yy}.html"
            links.append((name, f"Más esperados de {yy}", len(mine)))
            top = sorted(mine, key=self.rank)[:40]
            self.layout(name, f"Los juegos más esperados de {yy} (PC y consolas)",
                        f"Los juegos más esperados que salen en {yy}: GTA, Nintendo, PlayStation, Xbox y PC, con fecha y tráiler.",
                        f'<h1>Los juegos más esperados de {yy}</h1><p class="lead">Ordenados por cuánta gente los espera (listas de deseos de Steam '
                        f'y cuántas Wikipedias hablan de ellos). Con fecha, plataformas y tráiler.</p>{updated_line}'
                        f'<ul class="spot-grid">{"".join(self.spot_card(g, now, main=(i == 0)) for i, g in enumerate(top))}</ul>'
                        '<p><a class="btn" href="lanzamientos.html">Ver el calendario día por día</a></p>',
                        crumbs=[("lanzamientos.html", "Lanzamientos"), (name, f"Más esperados {yy}")], jsonld=[self.games_list_ld(top)])
        # por género
        upcoming = [g for g in games if g.get("comingSoon") or (g.get("date") or "") >= today]
        counts = {}
        for g in upcoming:
            for gen in g.get("genres", []):
                counts[gen] = counts.get(gen, 0) + 1
        for gen, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            name = f"lanzamientos-{slugify(gen)}.html"
            if n < 6 or name in self.pages:
                continue
            mine = [g for g in upcoming if gen in g.get("genres", [])]
            links.append((name, gen, n))
            dated = sorted([g for g in mine if g.get("date")], key=lambda g: (g["date"], self.rank(g)))
            tba = sorted([g for g in mine if not g.get("date")], key=self.rank)
            self.layout(name, f"Próximos juegos de {gen.lower()}: calendario de lanzamientos",
                        f"Los próximos juegos de {gen.lower()} para PC y consolas: fechas de lanzamiento, tráileres y los más esperados.",
                        f'<h1>Próximos juegos de {e(gen.lower())}</h1><p class="lead">{n} juegos de {e(gen.lower())} que vienen, del más cercano al más lejano.</p>'
                        f'{updated_line}' + self.release_groups(dated, now, "Calendario", "cal-gen", compact=False)
                        + self.release_groups(tba, now, "Fecha por confirmar", "tba-gen", compact=False),
                        crumbs=[("lanzamientos.html", "Lanzamientos"), (name, gen)])
        es = [g for g in upcoming if g.get("spanish")]
        if es:
            name = "lanzamientos-en-espanol.html"
            links.append((name, "En español", len(es)))
            dated = sorted([g for g in es if g.get("date")], key=lambda g: (g["date"], self.rank(g)))
            self.layout(name, "Próximos juegos de PC en español", "Próximos lanzamientos de Steam que vienen con idioma español (textos o voces).",
                        f'<h1>Próximos juegos en español</h1><p class="lead">Juegos que Steam lista con idioma español. {len(es)} en camino.</p>{updated_line}'
                        + self.release_groups(dated, now, "Calendario", "cal-es", compact=False)
                        + self.release_groups(sorted([g for g in es if not g.get("date")], key=self.rank), now, "Fecha por confirmar", "tba-es", compact=False),
                        crumbs=[("lanzamientos.html", "Lanzamientos"), (name, "En español")])
        self.release_links = links
        self.calendar_ics(games, now)

    def games_list_ld(self, games):
        return {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": g["title"], "url": self.base + self.detail[g["id"]]}
            for i, g in enumerate(games[:30]) if g["id"] in self.detail]}

    def calendar_ics(self, games, now):
        """calendario.ics: los próximos lanzamientos con día exacto, para suscribirse desde Google Calendar o el celular."""
        today = now.astimezone(CO_TZ).strftime("%Y-%m-%d")
        esc = lambda t: t.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", " ")
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        events = []
        for g in sorted((g for g in games if g.get("precision") == "day" and g.get("date", "") >= today), key=lambda g: g["date"])[:300]:
            d = g["date"].replace("-", "")
            nxt = (datetime.strptime(g["date"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
            url = self.base + self.detail.get(g["id"], "lanzamientos.html")
            plats = ", ".join(g.get("platforms", []))
            events.append("\r\n".join([
                "BEGIN:VEVENT", f"UID:{g['id']}@ofertas-gamer-co", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{d}", f"DTEND;VALUE=DATE:{nxt}",
                f"SUMMARY:{esc('🎮 Sale ' + g['title'])}", f"DESCRIPTION:{esc((plats + '. ' if plats else '') + 'La fecha puede cambiar. ' + url)}",
                f"URL:{url}", "TRANSP:TRANSPARENT", "END:VEVENT"]))
        self.write("calendario.ics", "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Ofertas Gamer CO//Lanzamientos//ES",
                                                   "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Lanzamientos de juegos (Ofertas Gamer CO)",
                                                   "X-WR-TIMEZONE:America/Bogota", "REFRESH-INTERVAL;VALUE=DURATION:PT12H"] + events + ["END:VCALENDAR"]) + "\r\n")

    def calendar_links(self):
        links = getattr(self, "release_links", [])
        chips = "".join(f'<a class="chip" href="{n}">{e(label)} <span class="meta">({c})</span></a>' for n, label, c in links)
        webcal = self.base.replace("https://", "webcal://") + "calendario.ics"
        return (f'<section class="cal-links"><h2>{ICONS["calendar"]} Explora el calendario</h2><nav class="chips" aria-label="Calendario por mes, año y género">{chips}</nav>'
                f'<div class="cta"><a class="btn" href="{e(webcal)}">{ICONS["calendar"]} Agregar a mi calendario</a>'
                f'<a class="btn" href="calendario.ics" download>Descargar .ics</a></div>'
                f'<p class="meta">Con «Agregar a mi calendario» los estrenos aparecen solos en el calendario de tu celular o en Google Calendar '
                f'(en Google: Otros calendarios → Desde URL → pega <code>{e(self.base)}calendario.ics</code>).</p></section>')

    def stats_page(self, live, games, updated_line):
        """Estadísticas públicas con datos propios: nada inventado, todo sale de los archivos del bot."""
        hist = self.history or {}
        tracked = len(hist)
        points = sum(len(v["points"]) for v in hist.values())
        first = min((v["points"][0][0] for v in hist.values() if v["points"]), default="")
        arch = list((getattr(self, "epic_archive", {}) or {}).values())
        epic_value = sum(self.cop_value(g["originalPrice"], {"currency": g.get("currency") or "USD", "copApproximation": None, "currentPrice": None}) or 0
                         for g in arch if g.get("originalPrice"))
        saved_now = sum(self.cop_saved(o) for o in live)
        by_store = sorted(((st["name"], sum(1 for o in live if o["storeId"] == sid)) for sid, st in self.stores.items() if st["active"]), key=lambda kv: -kv[1])
        top = max(live, key=lambda o: o.get("discountPercentage") or 0, default=None)
        lows = sum(1 for o in live if (self.price_stats(o) or {}).get("isLow"))
        cards = [(len(live), "ofertas activas hoy"), (sum(1 for o in live if o.get("currentPrice") == 0), "juegos gratis ahora"),
                 (self.pesos(saved_now) if saved_now else "$0", "de ahorro sumando todas las ofertas de hoy (aprox.)"),
                 (tracked, "juegos con historial de precio"), (len(arch), "juegos gratis de Epic registrados"),
                 (self.pesos(epic_value) if epic_value else "$0", "en juegos que regaló Epic (precio normal, aprox.)"),
                 (len(games), "lanzamientos en el calendario"), (lows, "ofertas en su mínimo histórico")]
        tiles = "".join(f'<li><strong>{e(str(v))}</strong><span>{e(t)}</span></li>' for v, t in cards)
        stores = "".join(f"<tr><td>{e(n)}</td><td>{c}</td></tr>" for n, c in by_store)
        self.layout("estadisticas.html", "Estadísticas de ofertas de juegos en Colombia",
                    "Cuántas ofertas hay hoy, cuánto se ahorra, cuántos juegos regaló Epic y más, con datos propios de Ofertas Gamer CO.",
                    f'<h1>Estadísticas</h1><p class="lead">Números reales sacados de nuestras propias revisiones (cada 4 horas)'
                    + (f', desde el {e(day_es(first))}' if first else "") + f'. {points} precios guardados hasta hoy.</p>{updated_line}'
                    f'<ul class="stats">{tiles}</ul>'
                    + (f'<p>El descuento más grande de hoy: <strong>{self.title_link(top)}</strong> con -{top.get("discountPercentage") or 0}%.</p>' if top else "")
                    + f'<h2>Ofertas activas por tienda</h2><table><thead><tr><th scope="col">Tienda</th><th scope="col">Ofertas</th></tr></thead><tbody>{stores}</tbody></table>',
                    crumbs=[("estadisticas.html", "Estadísticas")])

    def alerts_page(self):
        bot = getattr(self, "bot", "")
        start = (ext_link(f"https://t.me/{bot}?start=ayuda", f"{ICONS['bell']} Abrir el bot de alertas", cls="btn btn-primary",
                          label="Abrir el bot de alertas en Telegram") if bot else
                 '<p class="notice">El bot de alertas se está activando. Mientras tanto, únete al canal de Telegram.</p>')
        tg = self.cfg.get("enlace_canal_telegram", "")
        self.layout("alertas.html", "Alertas de precio y de lanzamientos por Telegram",
                    "Recibe un aviso en Telegram cuando un juego que quieres baje de precio, esté gratis o salga a la venta.",
                    f"""<h1>Alertas personales</h1>
<p class="lead">Dile al bot qué juego quieres y te avisa por Telegram cuando baje de precio, esté gratis o salga a la venta. Gratis y sin registrarte.</p>
<div class="cta">{start}{ext_link(tg, "Canal con todas las ofertas", cls="btn") if tg else ""}</div>
<ol class="how-steps">
<li><strong>Abre el bot</strong><span>Toca el botón y luego «Iniciar» en Telegram.</span></li>
<li><strong>Escribe tu alerta</strong><span><code>/alerta hollow knight</code> o <code>/alerta elden ring 50000</code> (precio máximo en pesos). Para estrenos: <code>/estreno fable</code>.</span></li>
<li><strong>Listo</strong><span>Revisamos cada 4 horas y te escribimos solo cuando se cumple. <code>/misalertas</code> y <code>/borrar</code> para administrarlas.</span></li>
</ol>
<p>También puedes tocar <strong>«Avísame»</strong> en la página de cualquier oferta o lanzamiento.</p>
<p class="meta">Privacidad: solo guardamos tu número de chat de Telegram y tus alertas, cifrados, para poder escribirte. No guardamos tu nombre ni tu teléfono. Escribe <code>/borrar todo</code> para eliminar tus datos.</p>""",
                    crumbs=[("alertas.html", "Alertas")])

    def epic_countdown(self, free):
        epic = sorted([o for o in free if o["storeId"] == "epic" and o.get("expiresAt")], key=lambda o: o["expiresAt"])
        if not epic:
            return ""
        o = epic[0]
        names = " y ".join(x["title"] for x in epic if x["expiresAt"] == o["expiresAt"])
        return (f'<section class="epic-timer"><p class="dotd-kicker">{ICONS["gift"]} Gratis en Epic ahora: {e(names)}</p>'
                f'<div class="launch" data-launch="{e(o["expiresAt"])}" data-done="Terminó" hidden><span class="launch-label">Termina en</span>'
                f'<span class="launch-num" data-u="d">0</span><small>días</small><span class="launch-num" data-u="h">0</span><small>h</small>'
                f'<span class="launch-num" data-u="m">0</span><small>min</small><span class="launch-num" data-u="s">0</span><small>s</small></div>'
                f'<p class="meta">Hasta el {e(date_es(o["expiresAt"]))}. Una vez lo reclamas, es tuyo para siempre.</p></section>')

    def epic_next_block(self):
        nxt = getattr(self, "epic_next", []) or []
        if not nxt:
            return ""
        items = "".join(
            f'<li class="spot-card"><div class="spot-img">'
            + (f'<img class="spot-fg" src="{e(g["image"])}" alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async">' if g.get("image") else no_cover({"title": g["title"]}, "no-cover spot-fg"))
            + f'<span class="badge free">PRONTO</span></div><div class="spot-body"><h3 class="clamp2">{e(g["title"])}</h3>'
            f'<p class="spot-date">{ICONS["calendar"]}Gratis desde el {e(day_es(g["startsAt"][:10]))}</p>'
            + (f'<p class="meta">Hasta el {e(day_es(g["expiresAt"][:10]))}</p>' if g.get("expiresAt") else "")
            + f'<div class="rel-actions">{ext_link(g["url"], "Ver en Epic", cls="btn btn-sm", label=f"Ver {g["title"]} en Epic Games Store (abre en otra pestaña)")}</div></div></li>'
            for g in nxt)
        return (f'<section class="epic-next"><h2>{ICONS["clock"]} Próximos juegos gratis en Epic</h2>'
                f'<p class="meta">Anunciados por Epic Games Store. Todavía no se pueden reclamar: te avisamos en Telegram el día que empiecen.</p>'
                f'<ul class="spot-grid small">{items}</ul></section>')

    def epic_archive_page(self, updated_line):
        arch = sorted((getattr(self, "epic_archive", {}) or {}).values(), key=lambda g: g.get("startsAt") or "", reverse=True)
        rows = "".join(
            f'<li class="spot-card"><div class="spot-img">'
            + (f'<img class="spot-fg" src="{e(g["image"])}" alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async">' if (g.get("image") or "").startswith("https://") else no_cover({"title": g["title"]}, "no-cover spot-fg"))
            + f'</div><div class="spot-body"><h3 class="clamp2">{e(g["title"])}</h3><p class="spot-date">{ICONS["calendar"]}'
            + (f'Del {e(day_es(g["startsAt"][:10]))} al {e(day_es(g["expiresAt"][:10]))}' if g.get("startsAt") and g.get("expiresAt") else "Fechas no informadas")
            + "</p>" + (f'<p class="meta">Precio normal: {e(money(g["originalPrice"], g.get("currency") or "USD"))}</p>' if g.get("originalPrice") else "")
            + "</div></li>" for g in arch)
        total = sum(self.cop_value(g["originalPrice"], {"currency": g.get("currency") or "USD", "copApproximation": None, "currentPrice": None}) or 0
                    for g in arch if g.get("originalPrice"))
        self.layout("todos-los-juegos-gratis-de-epic.html", "Todos los juegos gratis que ha regalado Epic Games",
                    "Lista de los juegos que Epic Games Store ha regalado, con fechas y precio normal, según nuestro propio registro.",
                    f'<h1>Juegos que ha regalado Epic</h1><p class="lead">Nuestro registro de los juegos gratis de Epic Games Store desde que empezamos a revisar '
                    f'(octubre de 2026). {len(arch)} juegos' + (f', que costaban en total unos {self.pesos(total)} COP' if total else "") + '.</p>'
                    f'{updated_line}<ul class="spot-grid small">{rows}</ul><p><a class="btn btn-primary" href="juegos-gratis.html">Ver los juegos gratis de hoy</a></p>',
                    crumbs=[("juegos-gratis.html", "Juegos gratis"), ("todos-los-juegos-gratis-de-epic.html", "Archivo de Epic")])

    # ---------- códigos de canje (ogc/codes.py) ----------
    def code_card(self, gid, item, now):
        from .codes import GAMES, is_new
        g = GAMES[gid]
        rewards = ", ".join(item.get("rewards") or []) or "Recompensas no informadas por la fuente"
        new = '<span class="badge free code-new">NUEVO</span>' if is_new(item, now) else ""
        return (f'<li class="code-card">{new}<p class="code-text"><code>{e(item["code"])}</code></p>'
                f'<p class="code-rewards">{ICONS["gift"]}{e(rewards)}</p><div class="rel-actions">'
                f'<button class="btn btn-sm" type="button" data-copy="{e(item["code"])}" hidden>Copiar</button>'
                + ext_link(g["redeem"].format(code=quote(item["code"])), "Canjear", cls="btn btn-primary btn-sm btn-free",
                           label=f"Canjear el código {item['code']} en la página oficial (abre en otra pestaña)") + "</div></li>")

    def codes_pages(self, state, now):
        from .codes import GAMES, active_codes, expired_codes
        month = f"{MONTHS_ES[now.astimezone(CO_TZ).month - 1]} {now.astimezone(CO_TZ).year}"
        checked = co_time(now)
        hub = []
        for gid, g in GAMES.items():
            live, gone = active_codes(state, gid), expired_codes(state, gid)
            last = ((state.get("games") or {}).get(gid) or {}).get("lastOk")
            hub.append((g, len(live), ((state.get("games") or {}).get(gid) or {}).get("image") or ""))
            when = (f'<p class="meta">Revisado el <time datetime="{e(last)}">{e(co_time(parse_iso(last)))}</time> · se revisa cada {self.cfg["intervalo_horas"]} horas</p>'
                    if last else '<p class="notice">Todavía no se pudo revisar la lista. Vuelve en unas horas.</p>')
            cards = (f'<ul class="code-grid">{"".join(self.code_card(gid, it, now) for it in live)}</ul>' if live else
                     '<p class="notice">No encontramos códigos activos en este momento. HoYoverse suele sacar códigos nuevos en las transmisiones '
                     'de cada versión: te avisamos en Telegram y Discord apenas salga uno.</p>')
            steps = "".join(f"<li>{e(x)}</li>" for x in g["steps"])
            old = ('<h2>Códigos vencidos</h2><p>Estos ya no funcionan. Los dejamos para que no pierdas tiempo probándolos.</p><p class="code-old">'
                   + " ".join(f"<code>{e(it['code'])}</code>" for it in gone) + "</p>") if gone else ""
            faq = [(f"¿Cuántos códigos de {g['name']} hay activos hoy?",
                    f"Hoy hay {len(live)} códigos activos según nuestra última revisión ({checked}). La lista se actualiza sola cada {self.cfg['intervalo_horas']} horas."),
                   (f"¿Cómo canjeo un código de {g['name']}?", " ".join(g["steps"]) + " " + g["ingame"]),
                   ("¿Por qué un código no me funciona?",
                    "Puede que ya haya vencido, que ya lo hayas usado en esa cuenta o que no tengas el nivel mínimo. Cada código se puede usar una sola vez por cuenta."),
                   ("¿Los códigos sirven en Colombia y Latinoamérica?",
                    "Sí. Elige el servidor América al canjear. Casi todos los códigos funcionan en todos los servidores.")]
            faq_html = '<div class="faq">' + "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq) + "</div>"
            faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
            img = ((state.get("games") or {}).get(gid) or {}).get("image") or ""
            img = img if img.startswith("https://") else ""
            icon = f'<img class="code-game-icon" src="{e(img)}" alt="Ícono de {e(g["name"])}" width="96" height="96">' if img else ""
            others = " · ".join(f'<a href="{o["page"]}">Códigos de {e(o["name"])}</a>' for k, o in GAMES.items() if k != gid)
            self.layout(g["page"], f"Códigos de {g['name']} activos hoy ({month})",
                        f"Todos los códigos de {g['name']} que funcionan hoy, con sus recompensas ({g['currency']} y más) y botón para canjear en la página oficial. Revisados cada {self.cfg['intervalo_horas']} horas.",
                        f'<div class="code-head">{icon}<h1>Códigos de {e(g["name"])} activos</h1></div><p class="lead">Los códigos que funcionan hoy para conseguir {e(g["currency"])} y otras recompensas gratis. '
                        f'Copia el código o toca <strong>Canjear</strong> para abrir la página oficial de HoYoverse con el código ya puesto.</p>{when}'
                        f'<h2>{ICONS["gift"]} Códigos activos ({len(live)})</h2>{cards}{self.ad_slot("article_middle")}'
                        f'<h2>Cómo canjear los códigos</h2><ol class="steps">{steps}</ol><p>{e(g["ingame"])}</p>{old}'
                        f'<h2>Preguntas frecuentes</h2>{faq_html}<p>{others}</p>'
                        f'<p class="meta">Los códigos son de HoYoverse; aquí solo los reunimos. Revisamos dos listas públicas de códigos y mostramos como activo solo '
                        f'lo que ninguna da por vencido. Un código puede dejar de funcionar antes de nuestra próxima revisión.</p>'
                        f'<section class="channels"><h2>{ICONS["bell"]} Recibe los códigos nuevos al instante</h2><p class="lead">Cuando sale un código nuevo lo publicamos en Telegram y Discord.</p>{self.channels_cta()}</section>',
                        crumbs=[("codigos.html", "Códigos"), (g["page"], g["name"])], jsonld=[faq_ld], og_image=img or None)
        rows = "".join(f'<li class="code-hub"><a href="{g["page"]}">'
                       + (f'<img src="{e(im)}" alt="" width="64" height="64" loading="lazy">' if im.startswith("https://") else "")
                       + f'<span><strong>Códigos de {e(g["name"])}</strong><span class="meta">{n} activos hoy</span></span></a></li>' for g, n, im in hub)
        self.layout("codigos.html", f"Códigos de juegos gratis activos ({month})",
                    "Códigos de canje que funcionan hoy para Genshin Impact, Honkai: Star Rail y Zenless Zone Zero, revisados automáticamente cada 4 horas.",
                    f'<h1>Códigos de juegos</h1><p class="lead">Códigos de canje que funcionan hoy, con sus recompensas y un botón para canjearlos en la página oficial. '
                    f'La lista se revisa sola cada {self.cfg["intervalo_horas"]} horas.</p><ul class="stores">{rows}</ul>',
                    crumbs=[("codigos.html", "Códigos")])

    def giveaway_card(self, g):
        kind = giveaways.TYPES.get(g["type"], "Juego")
        bits = [kind] + ([f"Valía US{g['worth']}"] if g.get("worth") else []) + ([f"Hasta el {day_es(g['endsOn'])}"] if g.get("endsOn") else [])
        img = (f'<img class="spot-fg" src="{e(g["image"])}" alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async">'
               if g.get("image", "").startswith("https://") else "")
        return (f'<li class="spot-card"><div class="spot-img">{img}</div><div class="spot-body"><h3 class="clamp2">{e(g["title"])}</h3>'
                f'<p class="meta">{e(" · ".join(bits))}</p><div class="rel-actions">'
                f'{ext_link(g["url"], "Reclamar gratis", cls="btn btn-primary btn-sm btn-free", label=f"Reclamar {g["title"]} gratis (abre en otra pestaña)")}</div></div></li>')

    def giveaways_page(self, items, updated_line):
        active = [g for g in items if g.get("active")]
        secs = []
        for key, name, _ in giveaways.GROUPS:
            rows = [g for g in active if g["group"] == key and g["type"] == "game"]
            if rows:
                secs.append(f'<section class="spot" id="{key}"><div class="sec-head"><h2>{ICONS["gift"]} Gratis en {e(name)}</h2>'
                            f'<p class="meta">{len(rows)} {"juego" if len(rows) == 1 else "juegos"}</p></div><ul class="spot-grid small">{"".join(self.giveaway_card(g) for g in rows)}</ul></section>')
        betas = [g for g in active if g["type"] != "game"]
        if betas:
            secs.append(f'<section class="spot" id="betas"><div class="sec-head"><h2>{ICONS["sparkle"]} Betas, pruebas y acceso anticipado</h2>'
                        f'<p class="meta">Para probar juegos antes de que salgan.</p></div><ul class="spot-grid small">{"".join(self.giveaway_card(g) for g in betas)}</ul></section>')
        body = "".join(secs) or '<p class="notice">Ahora mismo no hay regalos registrados. Vuelve en unas horas.</p>'
        jump = " ".join(f'<a class="chip" href="#{k}">{e(n)}</a>' for k, n, _ in giveaways.GROUPS
                        if any(g["group"] == k and g["type"] == "game" for g in active)) + (' <a class="chip" href="#betas">Betas</a>' if betas else "")
        self.layout("juegos-gratis-en-todas-las-tiendas.html", "Juegos gratis hoy en Steam, Epic, GOG y Amazon Prime Gaming",
                    "Todos los juegos que puedes reclamar gratis hoy en Steam, Epic Games, GOG, Amazon Prime Gaming y Luna, itch.io y más, más betas abiertas. Se actualiza cada 4 horas.",
                    f'<h1>Juegos gratis en todas las tiendas</h1><p class="lead">Lo que puedes reclamar gratis hoy, tienda por tienda, más betas y pruebas abiertas. '
                    f'Lo que reclamas mientras dura la promoción queda tuyo (en Amazon Luna y Prime Gaming puede pedir suscripción).</p>{updated_line}'
                    f'<nav class="chips" aria-label="Ir a una tienda">{jump}</nav>{body}'
                    f'<p class="meta">Datos de regalos: <a href="{giveaways.SOURCE_URL}" rel="noopener noreferrer" target="_blank">GamerPower</a>. '
                    f'Los botones abren la página oficial del regalo; confirma ahí las condiciones antes de reclamar.</p>',
                    crumbs=[("juegos-gratis.html", "Juegos gratis"), ("juegos-gratis-en-todas-las-tiendas.html", "En todas las tiendas")])

    def f2p_page(self, f2p, updated_line):
        if f2p:
            cards = "".join(
                f'<li class="spot-card" data-genres="{e("|".join(g.get("genres", [])))}"><div class="spot-img"><img class="spot-fg" src="{e(g["image"])}"{fallback(g)} alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async"></div>'
                f'<div class="spot-body"><h3 class="clamp2">{e(g["title"])}</h3><div class="rel-actions">'
                f'{ext_link(g["url"], "Jugar gratis en Steam", cls="btn btn-primary btn-sm btn-free", label=f"Jugar {g["title"]} gratis en Steam (abre en otra pestaña)")}</div></div></li>'
                for g in f2p)
            gens = []
            for g in f2p:
                for x in g.get("genres", []):
                    if x not in gens:
                        gens.append(x)
            chips = ('<nav class="chips" id="f2p-genres" aria-label="Filtrar por género" hidden><button class="chip" type="button" aria-pressed="true" data-g="">Todos</button>'
                     + "".join(f'<button class="chip" type="button" aria-pressed="false" data-g="{e(x)}">{e(x)}</button>' for x in gens) + "</nav>") if gens else ""
            listing = chips + f'<ul class="spot-grid small" id="f2p-list">{cards}</ul>'
        else:
            listing = '<p class="notice">Todavía no se cargó la lista. Vuelve en unas horas.</p>'
        self.layout("juegos-gratis-para-siempre.html", "Juegos de Steam gratis para siempre (free to play)",
                    "Los juegos de Steam gratis para siempre más jugados ahora mismo: free to play para PC que puedes descargar sin pagar.",
                    f'<h1>Juegos gratis para siempre</h1><p class="lead">Juegos <em>free to play</em> que no cuestan nada, ordenados por los más jugados en Steam. '
                    f'Pueden tener compras dentro del juego. ¿Buscas juegos de pago gratis por tiempo limitado? Mira <a href="juegos-gratis.html">Juegos gratis</a>.</p>'
                    f'{updated_line}{listing}', crumbs=[("juegos-gratis-para-siempre.html", "Gratis para siempre")])

    def weekly_pages(self, history, live, games, now, updated_line):
        from . import weekly
        current = history[0] if history and history[0]["week"] == weekly.week_key(now) else None
        snap = current or weekly.snapshot(now, *weekly.pick(live, games, now))

        def render(sn):
            parts = []
            for key, title, icon, kind in (("free", "Gratis esta semana", "gift", "offer"), ("deals", "Mejores descuentos", "flame", "offer"),
                                           ("games", "Salen esta semana", "calendar", "game")):
                if sn.get(key):
                    rows = "".join(self.note_row(dict(x, platforms=x.get("platforms", []), genres=x.get("genres", [])), kind, now) for x in sn[key])
                    parts.append(f'<section class="n-sec"><h3>{ICONS[icon]} {title}</h3><ul>{rows}</ul></section>')
            return f'<article class="note">{"".join(parts) or "<p class=n-sec>No hubo novedades esta semana.</p>"}</article>'

        poll_html = ""
        polls = getattr(self, "poll", {}) or {}
        for p in [polls.get("current")] + list(polls.get("previous") or []):
            if p and p.get("total"):
                total = p["total"]
                bars = "".join(f'<li><span class="pv-name">{e(t)}</span><span class="pv-bar"><span class="pv-fill pv-{min(100, round(100 * v / total)) // 5 * 5}"></span></span>'
                               f'<span class="pv-num">{round(100 * v / total)}%</span></li>'
                               for t, v in sorted(p.get("votes", {}).items(), key=lambda kv: -kv[1]))
                poll_html = (f'<section class="poll-res"><h2>{ICONS["chat"]} Lo que votó la comunidad</h2><p class="meta">{e(p["question"])} · '
                             f'{total} votos en Telegram{"" if p.get("closed") else " (la encuesta sigue abierta)"}</p><ul class="poll-bars">{bars}</ul></section>')
                break
        archive = "".join(f'<li><a href="{weekly.page_name(h)}">Resumen del {e(h["label"])}</a></li>' for h in history)
        archive_html = f'<h2>Resúmenes anteriores</h2><ul class="archive">{archive}</ul>' if archive else ""
        lead = ("Lo mejor de la semana: juegos gratis, los descuentos más grandes y los estrenos. Sale solo cada viernes en "
                '<a href="' + e(self.cfg.get("enlace_canal_telegram", "")) + '" target="_blank" rel="noopener noreferrer">Telegram</a>, Discord y Bluesky.')
        title = f"Resumen semanal del {snap['label']}" if current else "Lo mejor de esta semana (hasta ahora)"
        self.layout("resumen-semanal.html", "Resumen semanal de ofertas gamer para Colombia",
                    "Cada viernes: juegos gratis, los mejores descuentos de PC y los estrenos de la semana, en un solo lugar.",
                    f'<h1>Resumen semanal</h1><p class="lead">{lead}</p>{updated_line}<h2>{e(title)}</h2>{render(snap)}'
                    + ('<section class="top10"><h2>🏆 Top 10 de descuentos en imagen</h2><p class="meta">Para guardar o compartir. Se renueva cada viernes.</p>'
                       '<p><a href="img/top10-semana.jpg" download><img src="img/top10-semana.jpg" alt="Top 10 de los mayores descuentos de la semana" width="540" height="675" loading="lazy"></a></p></section>'
                       if getattr(self, "top10_image", False) else '') + f'{poll_html}{archive_html}',
                    crumbs=[("resumen-semanal.html", "Resumen semanal")])
        for h in history:
            self.layout(weekly.page_name(h), f"Resumen semanal de ofertas gamer: {h['label']}",
                        f"Juegos gratis, mejores descuentos y estrenos de la semana del {h['label']}.",
                        f'<h1>Resumen del {e(h["label"])}</h1><p class="lead">Así estaban las ofertas ese día. Los precios ya pueden haber cambiado: '
                        f'mira las <a href="ofertas.html">ofertas de hoy</a>.</p>{render(h)}',
                        crumbs=[("resumen-semanal.html", "Resumen semanal"), (weekly.page_name(h), h["label"])])

    def item_list_ld(self, offers):
        return {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": o["title"], "url": o["officialUrl"]}
            for i, o in enumerate(offers[:30])]}

    # ---------- páginas ----------
    def build(self, offers, status, updated_dt, games=None):
        if self.out.exists():
            for child in self.out.iterdir():
                if child.name in ("CNAME",):
                    continue
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        self.out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ASSETS, self.out / "assets")
        self.now = updated_dt
        updated = co_time(updated_dt)
        live = [o for o in offers if o["status"] != "Vencido"]
        rates = sorted(o["copApproximation"] / o["currentPrice"] for o in live
                       if o.get("copApproximation") and o.get("currentPrice") and o["currency"] == "USD")
        self.rate = rates[len(rates) // 2] if rates else None
        self.assign_pages(live, games or [])
        self.store_counts = {st: sum(1 for o in live if o["storeId"] == st) for st in self.stores}
        self.ranks = {g["id"]: g.get("rank") or i + 1 for i, g in enumerate(games or [])}
        free = [o for o in live if o.get("currentPrice") == 0]
        deals = [o for o in live if o.get("currentPrice")]
        soon = sorted([o for o in live if o.get("expiresAt")], key=lambda o: o["expiresAt"])[:6]
        top = sorted(deals, key=lambda o: (-("CO" in (o.get("regions") or [])), -(o.get("metacritic") or 0) // 10,
                                           -(o.get("discountPercentage") or 0)))[:12]
        dotd = self.deal_of_day(live)
        notice = ('<p class="notice">Los precios y promociones pueden haber cambiado desde la última verificación. '
                  'Confirma siempre en la tienda antes de comprar. Los valores en pesos son aproximados.</p>')
        updated_line = f'<p class="meta">Actualizado el <time datetime="{updated_dt.strftime("%Y-%m-%dT%H:%M:%SZ")}">{updated}</time> · se revisa cada {self.cfg["intervalo_horas"]} horas</p>'

        guides_html = '<ul class="stores">' + "".join(
            f'<li><a href="{g["slug"]}.html"><strong>{e(g["title"])}</strong></a><p class="meta">{e(g["description"])}</p></li>'
            for g in GUIDES[:3]) + "</ul>"
        active_stores = [s for s in self.stores.values() if s["active"]]
        stores_html = '<ul class="stores">' + "".join(
            f'<li><strong>{e(s["name"])}</strong><p class="meta">{sum(1 for o in live if o["storeId"] == s["id"])} ofertas activas</p></li>'
            for s in active_stores) + "</ul>"
        faq_short = '<div class="faq">' + "".join(
            f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in FAQ[:3]) + \
            '</div><p><a href="preguntas-frecuentes.html">Ver todas las preguntas</a></p>'
        org = {"@context": "https://schema.org", "@type": "Organization", "name": self.cfg["nombre"],
               "url": self.base, "logo": self.base + "assets/icon-512.png",
               "sameAs": [u for u in [self.cfg.get("enlace_canal_telegram")] if u]}
        website = {"@context": "https://schema.org", "@type": "WebSite", "name": self.cfg["nombre"],
                   "url": self.base, "inLanguage": "es"}

        self.layout("index.html", "Ofertas Gamer CO: juegos gratis y ofertas de PC para Colombia",
                    "Juegos gratis y descuentos de videojuegos para PC en tiendas oficiales, con vigencia, precio original y equivalente aproximado en pesos colombianos. Actualizado cada 4 horas.",
                    f"""{self.tide_stage(free[:2] + top)}
<section class="hero compact home-bar" aria-labelledby="home-h">
<div class="hb-text"><h1 id="home-h">Juegos gratis y ofertas de PC, verificados para Colombia</h1>
<p class="lead">Hoy hay <strong>{len(free)} {"juego gratis" if len(free) == 1 else "juegos gratis"}</strong> y <strong>{len(deals)} ofertas</strong> de {sum(1 for n in self.store_counts.values() if n)} tiendas oficiales, con el precio en pesos y la hora en que terminan.</p>
{updated_line}</div>
{self.thermometer(live, free)}
{self.quick_search()}
</section>
{self.steam_strip(updated_dt)}
<section class="shelf shelf-free" aria-labelledby="free-h">
{self.sec_head("", 'Abordando: gratis esta semana', 'Te quedas con el juego para siempre si lo reclamas antes de que termine. <a href="juegos-gratis.html">Ver todos los gratis</a>', "ticket", "free-h")}
{self.saved_box()}
{self.offer_list(free[:8], with_filters=False, list_id="free-home", poster=True) if free else '<p class="notice">No hay juegos gratis activos en este momento. Te avisamos en Telegram cuando salga uno.</p>'}
</section>
{self.ad_slot("banner_after_hero")}
<section class="shelf shelf-top" aria-labelledby="top-h">
{self.sec_head("", 'Salidas: las mejores ofertas de hoy', f'Por descuento, crítica y disponibilidad en Colombia. <a href="ofertas.html">Ver las {len(live)} ofertas</a>', "depart", "top-h")}
{self.offer_list(top, with_filters=False, list_id="top-home", bento=True)}
<p class="shelf-more"><a class="btn btn-primary" href="ofertas.html">Buscar entre las {len(live)} ofertas {ICONS["arrow"]}</a></p>
</section>
<div class="duo">{self.dotd_block(dotd)}{self.soon_strip(live)}</div>
{self.halloween_box(games or [], live)}
<div class="duo duo-save">{self.savings_box(deals)}{self.duel_box(live)}</div>
{self.store_marquee()}
{self.curve_carousel(games or [], updated_dt)}
{self.today_releases(games or [], updated_dt)}
{self.trailers_box(games or [])}
<div class="duo duo-learn">{self.how_we_verify()}{self.tools_grid()}</div>
{self.journal()}
{self.cta_band(next((o for o in top if o.get("image")), None))}
<p class="meta small-notice">Los precios pueden cambiar en cualquier momento: confirma siempre en la tienda antes de comprar. Los valores en pesos son aproximados.</p>""", jsonld=[org, website, self.item_list_ld(live)])

        self.layout("juegos-gratis.html", "Juegos gratis para PC hoy",
                    "Juegos gratuitos para PC disponibles ahora en tiendas oficiales como Epic Games Store, con la fecha en que termina cada promoción.",
                    f"<h1>Juegos gratis para PC</h1><p class=\"lead\">Juegos que puedes reclamar gratis por tiempo limitado en tiendas oficiales.</p>{updated_line}{self.epic_countdown(free)}{self.saved_box()}{notice}{self.offer_list(free, poster=True)}{self.epic_next_block()}<p><a class=\"btn\" href=\"todos-los-juegos-gratis-de-epic.html\">Todos los juegos que ha regalado Epic</a> <a class=\"btn\" href=\"juegos-gratis-para-siempre.html\">Gratis para siempre (free to play)</a> <a class=\"btn btn-primary\" href=\"juegos-gratis-en-todas-las-tiendas.html\">Gratis en Steam, GOG, Amazon y más</a></p><p>¿Primera vez? Lee <a href=\"guia-juegos-gratis-temporales.html\">cómo funcionan los juegos gratuitos temporales</a>.</p>",
                    crumbs=[("juegos-gratis.html", "Juegos gratis")], jsonld=[self.item_list_ld(free)])

        self.layout("ofertas.html", "Ofertas y descuentos de videojuegos",
                    "Descuentos de juegos de PC en Steam, GOG, Humble Store, Green Man Gaming, Fanatical y Epic, con precio original, precio actual y porcentaje de descuento.",
                    self.mega(["OFERTAS", "DESCUENTOS", "MÍNIMOS", "PESOS"]) + f"<h1>Todas las ofertas</h1><p class=\"lead\">{len(free)} juegos gratis y {len(deals)} descuentos de {self.cfg['filtros_ofertas']['descuento_minimo']}% o más en tiendas oficiales. Busca, filtra y guarda tus favoritos.</p>{updated_line}{notice}{self.offer_list(free + deals)}{self.steam_sales(games or [], updated_dt, {o['title'].lower() for o in deals})}{self.ig_banner('rpg')}",
                    crumbs=[("ofertas.html", "Ofertas")], jsonld=[self.item_list_ld(free + deals)])
        self.layout("favoritos.html", "Mis favoritos",
                    "Las ofertas que guardaste con la estrella. Se guardan solo en este navegador.",
                    '<h1>Mis favoritos</h1><p class="lead">Las ofertas que guardaste con la estrella ★. Se guardan solo en este navegador, sin cuenta.</p>'
                    '<div id="fav-root" data-src="data/offers.json"><p class="notice">Activa JavaScript para ver tus favoritos.</p></div>'
                    '<p><a class="btn btn-primary" href="ofertas.html">Buscar más ofertas</a></p>',
                    crumbs=[("favoritos.html", "Mis favoritos")], noindex=True)

        rows = "".join(
            f"<tr><td>{e(s['name'])}</td><td>{', '.join(e(d) for d in s['domains'])}</td>"
            f"<td>{sum(1 for o in live if o['storeId'] == s['id'])}</td>"
            f"<td>{'Enlaces de afiliado activos' if s.get('approved') else 'Sin afiliación (enlace normal)'}</td></tr>"
            for s in active_stores)
        self.layout("tiendas.html", "Tiendas oficiales incluidas",
                    "Lista de tiendas oficiales de videojuegos que incluye Ofertas Gamer CO, sus dominios autorizados y su estado de afiliación.",
                    f"""<h1>Tiendas incluidas</h1><p class="lead">Solo publicamos ofertas de estas tiendas. Cada enlace se valida contra su dominio oficial antes de publicarse.</p>
<table><thead><tr><th scope="col">Tienda</th><th scope="col">Dominio autorizado</th><th scope="col">Ofertas activas</th><th scope="col">Afiliación</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Tiendas de claves</h2><p><a href="instant-gaming.html"><strong>Instant Gaming</strong></a>: vende claves para activar en Steam, consolas y más. No es tienda oficial; lo enlazamos para comparar precios. <strong>Enlace de afiliado activo.</strong></p>{self.ig_banner("rpg")}
<p>Mostrar una tienda no significa que tengamos una relación comercial con ella. Cuando exista, lo indicamos en esta tabla y en cada enlace.</p>
<p>¿Quieres proponer una tienda oficial? <a href="{REPO}/issues/new?template=proponer-tienda.yml" target="_blank" rel="noopener noreferrer">Envía una propuesta</a>.</p>""",
                    crumbs=[("tiendas.html", "Tiendas")])

        self.layout("guias.html", "Guías para comprar juegos de PC con seguridad",
                    "Guías originales en español sobre tiendas oficiales, claves regionales, juegos gratuitos, DRM y enlaces de afiliados.",
                    "<h1>Guías</h1><p class=\"lead\">Explicaciones cortas para comprar y reclamar juegos sin sorpresas.</p><ul class=\"stores\">" + "".join(
                        f'<li><a href="{g["slug"]}.html"><strong>{e(g["title"])}</strong></a><p class="meta">{e(g["description"])}</p></li>' for g in GUIDES) + "</ul>",
                    crumbs=[("guias.html", "Guías")])
        for g in GUIDES:
            art = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"], "description": g["description"],
                   "datePublished": g["date"], "dateModified": g["date"], "inLanguage": "es",
                   "author": {"@type": "Organization", "name": self.cfg["nombre"]},
                   "publisher": {"@type": "Organization", "name": self.cfg["nombre"]}, "mainEntityOfPage": self.base + g["slug"] + ".html"}
            self.layout(f"{g['slug']}.html", g["title"], g["description"],
                        f'<article class="prose"><h1>{e(g["title"])}</h1><p class="meta">Publicado el <time datetime="{g["date"]}">{g["date"]}</time></p>{g["body"]}{self.ad_slot("article_end")}</article><p><a href="guias.html">Ver todas las guías</a></p>',
                        crumbs=[("guias.html", "Guías"), (f"{g['slug']}.html", g["title"])], jsonld=[art], og_type="article")

        self.news_page(live, games or [], updated_dt, updated_line)
        terms = "".join(f'<div class="term"><dt id="{e(t.split()[0].lower())}">{e(t)}</dt><dd>{e(d)}</dd></div>' for t, d in GLOSSARY)
        self.layout("glosario.html", "Glosario gamer: DLC, DRM, AAA, early access y más",
                    "Qué significan las palabras que ves en las tiendas de juegos: DLC, DRM, AAA, free to play, early access, bundle y más.",
                    f'<h1>Glosario gamer</h1><p class="lead">Las palabras que ves en las tiendas, explicadas en una línea.</p><dl class="glossary">{terms}</dl>',
                    crumbs=[("glosario.html", "Glosario")],
                    jsonld=[{"@context": "https://schema.org", "@type": "DefinedTermSet", "name": "Glosario gamer",
                             "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t, "description": d} for t, d in GLOSSARY]}])
        self.stats_page(live, games or [], updated_line)
        self.layout("oferta-del-dia.html", "Oferta del día: el juego de PC que más vale la pena hoy",
                    "Cada día elegimos la oferta de PC que más vale la pena por descuento, nota de la crítica y precio en pesos.",
                    f'<h1>Oferta del día</h1><p class="lead">Cada mañana elegimos una sola oferta: la que más vale la pena según el descuento, '
                    f'la nota de la crítica y el precio en pesos. No es publicidad: nadie paga por salir aquí.</p>{updated_line}'
                    + (self.dotd_block(dotd, page=True) + self.score_block(dotd) if dotd else '<p class="notice">Hoy no hay una oferta destacada. Vuelve mañana.</p>')
                    + f'{notice}<p><a class="btn" href="ofertas.html">Ver todas las ofertas</a></p>',
                    crumbs=[("oferta-del-dia.html", "Oferta del día")],
                    og_image=self.base + "img/oferta-del-dia.jpg" if getattr(self, "dotd_image", False) else (dotd or {}).get("image"))

        self.release_extra_pages(games or [], updated_dt, updated_line)
        self.releases_page(games or [], updated_dt, updated_line)
        self.collection_pages(live, games or [], updated_dt, updated_line, notice)
        self.f2p_page(getattr(self, "f2p", []), updated_line)
        self.giveaways_page(getattr(self, "giveaways", []), updated_line)
        self.ig_page(live)
        self.epic_archive_page(updated_line)
        self.codes_pages(getattr(self, "codes", {}) or {}, updated_dt)
        self.alerts_page()
        self.weekly_pages(getattr(self, "weekly_history", []), live, games or [], updated_dt, updated_line)
        self.offer_pages(live, notice)
        self.game_pages(games or [], updated_dt)
        self.fun_pages(live, free, games or [], updated_dt, updated_line)
        self.static_pages(status, updated)
        self.feeds(live, updated_dt)
        self.sitemap(updated_dt)
        self.write("site.webmanifest", json.dumps({
            "name": self.cfg["nombre"], "short_name": "Ofertas Gamer", "lang": "es", "start_url": "./index.html",
            "display": "standalone", "background_color": "#080a12", "theme_color": "#080a12", "id": "./",
            "description": "Juegos gratis, ofertas de PC verificadas y calendario de lanzamientos para Colombia.",
            "icons": [{"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
            "shortcuts": [{"name": "Juegos gratis", "url": "./juegos-gratis.html"}, {"name": "Ofertas", "url": "./ofertas.html"},
                          {"name": "Lanzamientos", "url": "./lanzamientos.html"}]}, ensure_ascii=False, indent=1))
        # App instalable: el service worker guarda una copia para abrir la página sin internet.
        version = asset_version("styles.css") + asset_version("app.js")
        shell = ["./", "index.html", "sin-conexion.html", f"assets/styles.css?v={asset_version('styles.css')}",
                 f"assets/app.js?v={asset_version('app.js')}", "assets/icon-192.png", "assets/placeholder.svg"]
        self.write("sw.js", SW_TEMPLATE.replace("__VERSION__", version).replace("__SHELL__", json.dumps(shell)))
        self.write(".nojekyll", "")
        if self.cfg.get("indexnow_key"):  # IndexNow exige publicar la clave (no es secreta)
            self.write(f"{self.cfg['indexnow_key']}.txt", self.cfg["indexnow_key"])
        if self.cfg.get("verificacion_bing"):  # archivo de verificación de Bing (alternativa a la etiqueta meta)
            self.write("BingSiteAuth.xml", f'<?xml version="1.0"?>\n<users>\n\t<user>{e(self.cfg["verificacion_bing"])}</user>\n</users>\n')
        shutil.copy(ROOT / "config" / "_headers", self.out / "_headers")
        (self.out / "data").mkdir(exist_ok=True)
        public = [dict({k: o[k] for k in o if k != "telegramPublishedAt"}, page=self.detail.get(o["id"]),
                       action=self.action_label(o), saving=self.saving_text(o)) for o in live]
        self.write("data/offers.json", json.dumps({"updatedAt": updated_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                   "offers": public}, ensure_ascii=False, indent=1))
        self.write("data/juegos.json", json.dumps({"games": [
            {"id": g["id"], "title": g["title"], "page": self.detail.get(g["id"]), "image": g.get("image") or "",
             "when": date_label(g.get("date"), g.get("precision"))} for g in (games or []) if g["id"] in self.detail]},
            ensure_ascii=False, separators=(",", ":")))
        self.layout("buscar.html", "Buscar juegos, ofertas y lanzamientos", "Busca cualquier juego en las ofertas y en el calendario de lanzamientos.",
                    '<h1>Buscar</h1><div id="search-root" hidden><label class="sr-only" for="site-q">Nombre del juego</label>'
                    '<input class="big-search" id="site-q" type="search" placeholder="Escribe un juego: GTA, Zelda, Hollow Knight…" autocomplete="off" autofocus>'
                    '<div id="search-out" aria-live="polite"></div></div>'
                    '<noscript><p>El buscador necesita JavaScript. Mira <a href="ofertas.html">todas las ofertas</a> o el <a href="lanzamientos.html">calendario</a>.</p></noscript>',
                    crumbs=[("buscar.html", "Buscar")], noindex=True)
        self.layout("seguidos.html", "Mis juegos seguidos", "Los lanzamientos que sigues con la campana. Se guardan solo en este navegador.",
                    '<h1>Mis juegos seguidos</h1><p class="lead">Los lanzamientos que sigues con la campana. Se guardan solo en este navegador, sin cuenta. '
                    'Para recibir un aviso cuando salgan, usa las <a href="alertas.html">alertas de Telegram</a>.</p>'
                    '<div id="follow-root"><p class="notice">Activa JavaScript para ver tus juegos seguidos.</p></div>',
                    crumbs=[("seguidos.html", "Mis seguidos")], noindex=True)

    def static_pages(self, status, updated):
        tg = self.cfg.get("enlace_canal_telegram")
        tg_link = ext_link(tg, "canal de Telegram", cls="") if tg else "nuestro canal de Telegram"
        P = self.layout
        P("quienes-somos.html", "Quiénes somos", "Qué es Ofertas Gamer CO, a quién está dirigida y qué no hace.",
          f"""<div class="prose"><h1>Quiénes somos</h1>
<p>Ofertas Gamer CO es una plataforma independiente en español que reúne promociones verificadas, juegos gratuitos y descuentos de videojuegos para usuarios de Colombia y Latinoamérica. Nuestro objetivo es facilitar el descubrimiento de oportunidades disponibles en tiendas oficiales.</p>
<p>Mostramos la tienda, el precio, la vigencia y el enlace correspondiente cuando la información se encuentra disponible. Los precios, la disponibilidad y las condiciones pueden cambiar sin previo aviso.</p>
<h2>Lo que no hacemos</h2>
<ul><li>No vendemos los productos.</li><li>No procesamos pagos ni pedimos datos bancarios.</li><li>No controlamos las políticas de cada tienda: garantías, devoluciones y licencias dependen del vendedor.</li></ul>
<p>Lee <a href="como-verificamos.html">cómo verificamos las ofertas</a>.</p></div>""",
          crumbs=[("quienes-somos.html", "Quiénes somos")])

        P("como-verificamos.html", "Cómo verificamos las ofertas", "Metodología de Ofertas Gamer CO: fuentes, validaciones automáticas y cómo tratamos precios, fechas y enlaces.",
          f"""<div class="prose"><h1>Cómo verificamos</h1>
<p>Cada {self.cfg['intervalo_horas']} horas un proceso automático consulta las fuentes listadas en <a href="fuentes.html">Fuentes de información</a> y valida cada oferta antes de publicarla.</p>
<h2>Reglas que aplicamos</h2>
<ul>
<li>Solo tiendas de una lista autorizada y enlaces HTTPS de sus dominios oficiales.</li>
<li>Rechazamos registros sin título, tienda o enlace.</li>
<li>Conservamos el precio y la moneda originales de la tienda. El valor en pesos solo se muestra si obtuvimos una tasa de cambio confiable, y siempre como aproximado.</li>
<li>El porcentaje de descuento solo se calcula cuando tenemos el precio anterior y el actual.</li>
<li>Si la tienda no informa la fecha de fin, mostramos "fecha desconocida". Las ofertas vencidas se ocultan.</li>
<li>Evitamos duplicados: un mismo juego aparece una sola vez, con la mejor oferta.</li>
<li>Si una fuente falla temporalmente, mantenemos la última versión válida por un máximo de {self.cfg.get('horas_retener_oferta_sin_confirmar', 24)} horas en lugar de vaciar la página.</li>
</ul>
<h2>Limitaciones</h2>
<p>Algunas fuentes informan precios de referencia de la tienda en dólares de Estados Unidos. El precio para Colombia puede variar. Por eso indicamos la región cuando la conocemos.</p>
<h2 id="termometro">Termómetro de ofertas</h2>
<p>Es una nota de 0 a 10 que se calcula sola en cada revisión con tres datos reales: el descuento promedio de las 50 mejores ofertas (hasta 6 puntos), cuántas ofertas están en el precio más bajo que hemos visto (hasta 2 puntos, con 20 o más) y cuántos juegos gratis hay (hasta 2 puntos, con 5 o más). No es una predicción: solo dice qué tan bueno está el día comparado con lo normal.</p>
<p>¿Encontraste un error? <a href="contacto.html">Repórtalo</a>.</p></div>""",
          crumbs=[("como-verificamos.html", "Cómo verificamos")])

        issue = f"{REPO}/issues/new?template=reportar-oferta.yml"
        P("contacto.html", "Contacto y reportes", "Cómo reportar enlaces vencidos, precios incorrectos, ofertas agotadas o problemas de funcionamiento en Ofertas Gamer CO.",
          f"""<div class="prose"><h1>Contacto</h1>
<p>Usa estos canales para reportar:</p>
<ul><li>Enlaces vencidos</li><li>Precios incorrectos</li><li>Ofertas agotadas</li><li>Problemas de funcionamiento</li><li>Consultas generales</li></ul>
<h2>Canales</h2>
<ul><li>Telegram: {tg_link} (contacto público principal).</li>
<li>GitHub: <a href="{issue}" target="_blank" rel="noopener noreferrer">abrir un reporte de oferta</a> con un formulario prellenado. Necesitas una cuenta de GitHub y el reporte es público.</li></ul>
<p class="notice">No envíes contraseñas, datos bancarios, números de tarjeta ni documentos de identidad. Nunca te los pediremos.</p></div>""",
          crumbs=[("contacto.html", "Contacto")])

        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}
        P("preguntas-frecuentes.html", "Preguntas frecuentes", "Respuestas sobre cómo funciona Ofertas Gamer CO, los precios en pesos, los juegos gratis y los enlaces de afiliados.",
          '<h1>Preguntas frecuentes</h1><div class="faq">' + "".join(
              f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in FAQ) + "</div>",
          crumbs=[("preguntas-frecuentes.html", "Preguntas frecuentes")], jsonld=[faq_ld])

        P("privacidad.html", "Política de privacidad", "Qué datos trata Ofertas Gamer CO, qué servicios técnicos usa y cómo hacer consultas de privacidad.",
          f"""<div class="prose"><h1>Política de privacidad</h1><p class="meta">Última actualización: {LEGAL_UPDATED}</p>
<h2>Resumen</h2>
<ul><li>La página no requiere registro de usuario.</li>
<li>No pedimos contraseñas, datos bancarios, números de tarjeta, documentos de identidad ni información financiera.</li>
<li>No usamos herramientas de analítica, publicidad ni cookies de seguimiento.</li></ul>
<h2>Alertas por Telegram (opcional)</h2>
<p>Si creas una alerta en nuestro bot de Telegram, guardamos tu número de chat de Telegram (lo necesitamos para escribirte) y el texto de tus alertas. No guardamos tu nombre, usuario ni teléfono. Esos datos se guardan cifrados y solo los usa el bot. Puedes borrarlos cuando quieras escribiendo <code>/borrar todo</code> al bot. Los favoritos, los juegos que sigues y el tema se guardan solo en tu navegador.</p>
<h2>Servicios técnicos que usamos</h2>
<ul>
<li><strong>GitHub Pages</strong> aloja la página. Como cualquier servidor web, puede procesar datos técnicos como la dirección IP para entregar el sitio y protegerlo. <a href="https://docs.github.com/es/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener noreferrer">Declaración de privacidad de GitHub</a>.</li>
<li><strong>Imágenes de las tiendas</strong>: algunas imágenes de los juegos se cargan desde los servidores de cada tienda, que pueden registrar datos técnicos de la solicitud según sus propias políticas.</li>
<li><strong>Google Search Console</strong>: usamos una etiqueta de verificación para que Google indexe el sitio. No instala seguimiento en tu navegador.</li>
<li><strong>Telegram</strong>: si te unes a nuestro canal, aplica la <a href="https://telegram.org/privacy" target="_blank" rel="noopener noreferrer">política de privacidad de Telegram</a>.</li>
</ul>
<h2>Almacenamiento en tu navegador</h2>
<p>Si usas favoritos o cambias el tema, guardamos esa preferencia en el almacenamiento local de tu navegador. No sale de tu dispositivo y puedes borrarla desde la configuración del navegador. Ver <a href="cookies.html">Política de cookies</a>.</p>
<h2>Enlaces a terceros</h2>
<p>Los enlaces llevan a páginas de terceros con sus propias políticas de privacidad, que te recomendamos revisar.</p>
<h2>Cambios</h2>
<p>No instalaremos analítica, cookies, formularios, boletines, notificaciones ni publicidad sin actualizar antes esta política.</p>
<h2>Consultas</h2>
<p>Puedes enviar consultas de privacidad por nuestro {tg_link}.</p>
{LEGAL_REVIEW}</div>""", crumbs=[("privacidad.html", "Privacidad")])

        P("cookies.html", "Política de cookies", "Ofertas Gamer CO no usa cookies de seguimiento. Qué guardamos en tu navegador y cómo borrarlo.",
          f"""<div class="prose"><h1>Política de cookies</h1><p class="meta">Última actualización: {LEGAL_UPDATED}</p>
<p>Ofertas Gamer CO no instala cookies propias ni de terceros para analítica o publicidad.</p>
<p>Usamos el almacenamiento local del navegador solo para preferencias opcionales, como los favoritos (<code>ogc-favs</code>). No se envían a ningún servidor.</p>
<p>Las tiendas a las que enlazamos pueden usar sus propias cookies cuando visitas su sitio.</p>
<p>Si en el futuro activamos analítica o anuncios, actualizaremos esta política y pediremos tu consentimiento cuando la ley lo requiera.</p>
{LEGAL_REVIEW}</div>""", crumbs=[("cookies.html", "Cookies")])

        P("afiliados.html", "Aviso de afiliados", "Cómo funcionan los enlaces de afiliados en Ofertas Gamer CO y cómo se identifican.",
          f"""<div class="prose"><h1>Aviso de afiliados</h1><p class="meta">Última actualización: {LEGAL_UPDATED}</p>
<p>Algunos enlaces publicados en Ofertas Gamer CO pueden ser enlaces de afiliados. Si una persona realiza una compra mediante uno de esos enlaces, Ofertas Gamer CO puede recibir una comisión sin que el comprador pague un valor adicional.</p>
<p>La selección y presentación de las ofertas se mantiene independiente de esa posible comisión. Los precios, la disponibilidad, las condiciones y la duración de cada promoción son responsabilidad de la tienda correspondiente. Antes de comprar, comprueba la información directamente en el sitio oficial del vendedor.</p>
<h2>Cómo identificarlos</h2>
<p>Cada oferta con enlace de afiliado muestra la etiqueta <strong>Enlace de afiliado</strong>. Un enlace normal nunca se marca como afiliado. El estado de cada tienda aparece en <a href="tiendas.html">Tiendas</a>.</p>
{LEGAL_REVIEW}</div>""", crumbs=[("afiliados.html", "Aviso de afiliados")])

        P("publicidad.html", "Política de publicidad y patrocinios", "Cómo distingue Ofertas Gamer CO la publicidad, los patrocinios y los enlaces de afiliados.",
          f"""<div class="prose"><h1>Publicidad y patrocinios</h1><p class="meta">Última actualización: {LEGAL_UPDATED}</p>
<ul>
<li><strong>Publicidad</strong>: un espacio pagado por un anunciante o una red de anuncios. Se marca con la palabra "Publicidad".</li>
<li><strong>Patrocinio</strong>: una marca paga para destacar una oferta, un artículo o una publicación. Se marca como "Patrocinado" o "Enlace patrocinado", con fecha de inicio y de fin.</li>
<li><strong>Enlace de afiliado</strong>: un enlace normal con un identificador que puede generarnos una comisión. Se marca como "Enlace de afiliado".</li>
</ul>
<h2>Reglas</h2>
<ul>
<li>Una marca no puede comprar una opinión positiva ni cambiar los datos de una oferta.</li>
<li>Las ofertas patrocinadas se marcan claramente y no se mezclan sin aviso con las demás.</li>
<li>No aceptamos productos ilegales, engañosos o no relacionados con videojuegos.</li>
<li>No usamos ventanas emergentes invasivas ni anuncios que imiten botones de descarga.</li>
</ul>
<p>Hoy el sitio no muestra publicidad. ¿Te interesa anunciarte? Ve a <a href="anunciate.html">Anúnciate</a>.</p>
{LEGAL_REVIEW}</div>""", crumbs=[("publicidad.html", "Publicidad")])

        P("terminos.html", "Términos de uso", "Condiciones de uso de Ofertas Gamer CO: precios, responsabilidad de las tiendas y enlaces externos.",
          f"""<div class="prose"><h1>Términos de uso</h1><p class="meta">Última actualización: {LEGAL_UPDATED}</p>
<ul>
<li>Los precios y las promociones pueden cambiar en cualquier momento.</li>
<li>Debes verificar la información en la tienda antes de comprar.</li>
<li>Ofertas Gamer CO no vende productos ni procesa pagos.</li>
<li>Las garantías, devoluciones y licencias pertenecen al vendedor.</li>
<li>No garantizamos la disponibilidad permanente del sitio ni de las ofertas.</li>
<li>Los enlaces externos tienen sus propios términos y condiciones.</li>
</ul>
{LEGAL_REVIEW}</div>""", crumbs=[("terminos.html", "Términos")])

        P("anunciate.html", "Anúnciate en Ofertas Gamer CO", "Formatos de patrocinio disponibles en Ofertas Gamer CO y las reglas para anunciarse.",
          f"""<div class="prose"><h1>Anúnciate</h1>
<p>Ofertas Gamer CO es un sitio en español de juegos gratis y ofertas de PC para personas de Colombia y Latinoamérica que juegan en computador.</p>
<h2>Formatos previstos</h2>
<ul><li>Oferta destacada patrocinada</li><li>Banner semanal</li><li>Patrocinio de artículo</li><li>Publicación patrocinada en Telegram</li><li>Comparación patrocinada, claramente identificada</li></ul>
<h2>Condiciones básicas</h2>
<ul><li>Toda campaña tiene fecha de inicio, fecha de fin y etiqueta de patrocinio.</li>
<li>Solo productos y servicios legales relacionados con videojuegos.</li>
<li>No se compran opiniones positivas. Más detalles en la <a href="publicidad.html">política de publicidad</a>.</li></ul>
<p>Todavía no publicamos cifras de audiencia. Para conversar, escríbenos por nuestro {tg_link}.</p></div>""",
          crumbs=[("anunciate.html", "Anúnciate")])

        rows = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in status.items())
        P("estado.html", "Estado del sistema", "Estado de la última actualización automática de Ofertas Gamer CO y de cada fuente de datos.",
          f"""<h1>Estado del sistema</h1><p class="lead">Resultado de la última ejecución automática.</p>
<table><tbody><tr><td>Última actualización</td><td>{e(updated)}</td></tr>{rows}</tbody></table>
<p>Los registros completos están en <a href="{REPO}/actions" target="_blank" rel="noopener noreferrer">GitHub Actions</a>. Archivo de datos: <a href="data/offers.json">offers.json</a>.</p>""",
          crumbs=[("estado.html", "Estado del sistema")])

        P("fuentes.html", "Fuentes de información", "Fuentes de datos que usa Ofertas Gamer CO para encontrar juegos gratis, ofertas y tasas de cambio.",
          """<div class="prose"><h1>Fuentes de información</h1>
<ul>
<li><strong>Epic Games Store</strong>: listado público de juegos gratis, consultado para Colombia. Enlace a la ficha oficial del juego.</li>
<li><strong><a href="https://www.cheapshark.com" target="_blank" rel="noopener noreferrer">CheapShark</a></strong>: API pública de precios de tiendas de juegos de PC. La usamos para encontrar descuentos; el enlace lleva a la tienda oficial (ficha de Steam o búsqueda oficial de la tienda). Gracias a CheapShark por ofrecer estos datos.</li>
<li><strong><a href="https://www.wikidata.org/" target="_blank" rel="noopener noreferrer">Wikidata</a></strong>: la base de datos libre de Wikipedia. La usamos para los juegos grandes y de consola (PlayStation, Xbox y Switch) y sus fechas; los ordenamos por en cuántos idiomas de Wikipedia tienen artículo.</li>
<li><strong>Códigos de canje de HoYoverse</strong>: dos listas públicas y gratuitas de la comunidad, <a href="https://hoyo-codes.seria.moe" target="_blank" rel="noopener noreferrer">hoyo-codes</a> y <a href="https://api.ennead.cc" target="_blank" rel="noopener noreferrer">ennead</a>. Un código solo aparece como activo si ninguna de las dos lo da por vencido. El botón «Canjear» lleva a la página oficial de HoYoverse.</li>
<li><strong><a href="https://www.exchangerate-api.com" target="_blank" rel="noopener noreferrer">ExchangeRate-API</a></strong>: tasa de cambio del día para el valor aproximado en pesos.</li>
</ul>
<p>No copiamos textos protegidos de las tiendas. Las imágenes de los juegos son las promocionales que publican las propias tiendas o fuentes. Si eres titular de derechos y quieres que retiremos una imagen, escríbenos desde <a href="contacto.html">Contacto</a>.</p></div>""",
          crumbs=[("fuentes.html", "Fuentes de información")])

        P("404.html", "Página no encontrada", "La página que buscas no existe en Ofertas Gamer CO.",
          '<h1>Página no encontrada</h1><p>La dirección no existe o cambió.</p><p><a class="btn btn-primary" href="index.html">Ir al inicio</a></p>',
          noindex=True)
        P("sin-conexion.html", "Sin conexión", "No hay conexión a internet.",
          '<h1>Sin conexión</h1><p>No hay internet en este momento. Cuando vuelva la conexión, las ofertas se actualizan solas.</p>'
          '<p><a class="btn btn-primary" href="index.html">Reintentar</a></p>', noindex=True)

    def feeds(self, offers, updated_dt):
        latest = sorted(offers, key=lambda o: o.get("createdAt") or "", reverse=True)[:30]

        def summary(o):
            if o.get("currentPrice") == 0:
                return f"Gratis en {o['store']}."
            return f"{o.get('discountPercentage') or ''}% de descuento en {o['store']}: {money(o['currentPrice'], o['currency'])}."

        x = lambda s: html.escape(str(s), quote=True)
        items = "".join(
            f"<item><title>{x(o['title'])}</title><link>{x(o['destinationUrl'])}</link><guid isPermaLink=\"false\">{x(o['id'])}</guid>"
            f"<pubDate>{format_datetime(parse_iso(o['createdAt']) or updated_dt)}</pubDate><description>{x(summary(o))}</description></item>"
            for o in latest)
        self.write("rss.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>Ofertas Gamer CO</title>'
                              f"<link>{self.base}</link><description>Juegos gratis y ofertas de PC</description><language>es</language>"
                              f"<lastBuildDate>{format_datetime(updated_dt)}</lastBuildDate>{items}</channel></rss>\n")
        stamp = updated_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        entries = "".join(
            f"<entry><title>{x(o['title'])}</title><link href=\"{x(o['destinationUrl'])}\"/><id>urn:ogc:{x(o['id'])}</id>"
            f"<updated>{x(o.get('updatedAt') or stamp)}</updated><summary>{x(summary(o))}</summary></entry>" for o in latest)
        self.write("atom.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>Ofertas Gamer CO</title>'
                               f'<link href="{self.base}"/><link rel="self" href="{self.base}atom.xml"/><id>{self.base}</id>'
                               f"<updated>{stamp}</updated><author><name>Ofertas Gamer CO</name></author>{entries}</feed>\n")
        self.write("feed.json", json.dumps({
            "version": "https://jsonfeed.org/version/1.1", "title": "Ofertas Gamer CO", "home_page_url": self.base,
            "feed_url": self.base + "feed.json", "language": "es",
            "items": [{"id": o["id"], "url": o["destinationUrl"], "title": o["title"], "content_text": summary(o),
                       "date_published": o.get("createdAt"), "image": o.get("image") or None} for o in latest]},
            ensure_ascii=False, indent=1))

    def sitemap(self, updated_dt):
        day = updated_dt.strftime("%Y-%m-%d")
        # Índice con tres mapas: así Google encuentra antes los lanzamientos y las ofertas nuevas.
        groups = {"sitemap-ofertas.xml": [p for p in self.pages if p.startswith("oferta-")],
                  "sitemap-lanzamientos.xml": [p for p in self.pages if p.startswith("juego-")]}
        groups["sitemap-paginas.xml"] = [p for p in self.pages if not p.startswith(("oferta-", "juego-"))]
        for fname, pages in groups.items():
            urls = "".join(f"<url><loc>{self.base}{'' if p == 'index.html' else p}</loc><lastmod>{day}</lastmod></url>" for p in pages)
            self.write(fname, '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                              f"{urls}</urlset>\n")
        maps = "".join(f"<sitemap><loc>{self.base}{f}</loc><lastmod>{day}</lastmod></sitemap>" for f in groups)
        self.write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                  f"{maps}</sitemapindex>\n")
        self.write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {self.base}sitemap.xml\n")
