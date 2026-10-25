"""Genera el sitio estático (docs/), los feeds, el sitemap y el resumen de WhatsApp."""

import hashlib
import html
import json
import shutil
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

from .channels import CO_TZ, co_time, cop_text, date_es, money, time_left, whatsapp_text
from .content import FAQ, GUIDES, LEGAL_REVIEW, LEGAL_UPDATED
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
}.items()}

NAV = [
    ("Ofertas", [("index.html", "Inicio", "home"), ("juegos-gratis.html", "Juegos gratis", "gift"),
                 ("ofertas.html", "Todas las ofertas", "flame"), ("favoritos.html", "Mis favoritos", "star"),
                 ("noticias.html", "Novedades", "news"), ("resumen-semanal.html", "Resumen semanal", "calendar"),
                 ("juegos-baratos.html", "Baratos en pesos", "sparkle"), ("juegos-gratis-para-siempre.html", "Gratis para siempre", "gift")]),
    ("Lanzamientos", [("lanzamientos.html", "Calendario", "calendar"), ("lanzamientos.html#proximos", "Próximos", "clock"),
                      ("lanzamientos.html#recientes", "Recientes", "sparkle"), ("lanzamientos.html#por-confirmar", "Por confirmar", "question"),
                      ("lanzamientos-playstation.html", "PlayStation", "store"), ("lanzamientos-xbox.html", "Xbox", "store"),
                      ("lanzamientos-switch.html", "Nintendo Switch", "store")]),
    ("Ayuda", [("guias.html", "Guías", "book"), ("preguntas-frecuentes.html", "Preguntas", "chat"),
               ("como-verificamos.html", "Cómo verificamos", "check")]),
]
FOOTER = [
    ("como-verificamos.html", "Cómo verificamos"), ("quienes-somos.html", "Quiénes somos"),
    ("contacto.html", "Contacto"), ("privacidad.html", "Privacidad"), ("cookies.html", "Cookies"),
    ("afiliados.html", "Aviso de afiliados"), ("publicidad.html", "Publicidad y patrocinios"),
    ("terminos.html", "Términos de uso"), ("anunciate.html", "Anúnciate"), ("estado.html", "Estado del sistema"),
    ("fuentes.html", "Fuentes de información"), ("whatsapp.html", "Resumen para WhatsApp"),
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



def no_cover(g, cls="no-cover"):
    """Tarjeta con el nombre del juego cuando no hay ninguna imagen libre (mejor que un gris vacío)."""
    plats = " · ".join(g.get("platforms", [])[:3])
    return (f'<div class="{cls}" role="img" aria-label="{e(g["title"])}"><strong>{e(g["title"])}</strong>'
            f'{f"<span>{e(plats)}</span>" if plats else ""}</div>')


def fallback(o):
    """Miniatura de respaldo por si la portada grande no existe (app.js la cambia al fallar)."""
    small = o.get("imageSmall") or ""
    return f' data-fallback="{e(small)}"' if small.startswith("https://") else ""


class Site:
    def __init__(self, cfg, stores, ads, out):
        self.cfg, self.stores, self.ads, self.out = cfg, stores, ads, Path(out)
        self.base = cfg["url_web"].rstrip("/") + "/"
        self.pages = []
        self.detail = {}  # id de oferta o juego -> nombre de su página propia
        self.now = datetime.now(timezone.utc)
        self.rate = None  # pesos por dólar, deducido de las ofertas

    # ---------- plantilla común ----------
    def layout(self, name, title, description, body, crumbs=None, jsonld=None, noindex=False, og_type="website", og_image=None):
        canonical = self.base + ("" if name == "index.html" else name)
        full_title = title if name == "index.html" else f"{title} | {self.cfg['nombre']}"
        stores_nav = [(f"ofertas.html?tienda={st['id']}", st["name"], "store-" + st["id"]) for st in self.stores.values() if st["active"]]
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
<body>
<div class="bg-decor" aria-hidden="true"></div>
<a class="skip" href="#contenido">Saltar al contenido</a>
<header class="site"><div class="wrap">
<div class="bar"><a class="brand" href="index.html"><img src="assets/logo-72.png" alt="" width="36" height="36">Ofertas Gamer CO</a>
<div class="bar-actions"><button class="btn" id="theme-toggle" type="button" aria-label="Cambiar entre modo claro y oscuro">Tema</button>
<button class="btn menu-toggle" id="menu-toggle" type="button" aria-expanded="false" aria-controls="main-nav">Menú</button></div></div>
</div></header>
<div class="shell">
<nav class="side" id="main-nav" aria-label="Principal">{nav}{self.side_channels()}</nav>
<main id="contenido"><div class="wrap">
{crumb_html}
{body}
</div></main>
</div>
<footer class="site"><div class="wrap">
<p class="foot-brand"><img src="assets/logo-72.png" alt="" width="32" height="32"> Ofertas Gamer CO</p>
<p class="install" id="install-box" hidden><button class="btn btn-primary" type="button" id="install-app">Instalar la app en tu celular</button></p>
<p>{e(DISCLOSURE)}</p>
<nav aria-label="Pie de página"><ul>{foot}</ul></nav>
<p>Ofertas Gamer CO no vende productos ni procesa pagos. Los precios y la disponibilidad pueden cambiar sin previo aviso.</p>
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

    def trust_chips(self, o, full=False):
        chips = []
        if "CO" in (o.get("regions") or []):
            chips.append('<span class="st ok">Precio para Colombia</span>')
        elif o["currency"] == "USD":
            chips.append('<span class="st ref">Precio de referencia en USD</span>')
        else:
            chips.append('<span class="st warn">Región por confirmar</span>')
        if not o.get("expiresAt"):
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
        return f"""<li class="card{' is-free' if free else ''}" data-id="{e(o['id'])}" data-title="{e(o['title'].lower())}" data-store="{e(o['storeId'])}" data-type="{'gratis' if free else 'descuento'}" data-discount="{100 if free else (o.get('discountPercentage') or 0)}" data-expires="{e(o.get('expiresAt') or '')}" data-price="{o.get('currentPrice') or 0}" data-cop="{round(cop_now)}">
<div class="thumb"><img src="{e(img)}"{fallback(o)} alt="{e(alt)}" width="460" height="215" loading="lazy" decoding="async">{self.badge(o)}{self.store_chip(o)}</div>
<div class="body"><h3 class="clamp2">{self.title_link(o)}</h3>
{self.price_html(o)}
{self.countdown(o)}
{self.trust_chips(o)}
<div class="actions">{self.offer_button(o)}<button class="btn icon-btn" type="button" data-fav="{e(o['id'])}" aria-pressed="false" aria-label="Guardar {e(o['title'])} en favoritos" hidden>{ICONS['star']}</button><button class="btn icon-btn" type="button" data-share="{e(self.base + self.detail[o['id']] if o['id'] in self.detail else o['destinationUrl'])}" data-title="{e(o['title'])}" aria-label="Compartir {e(o['title'])}" hidden>↗</button></div>
</div></li>"""

    def offer_list(self, offers, with_filters=True, list_id="offers"):
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
<label>Ordenar por<select name="sort"><option value="discount">Mayor descuento</option><option value="expires">Vence primero</option><option value="price">Menor precio</option><option value="title">Nombre</option></select></label>
<label><span>Favoritos</span><span><input type="checkbox" name="favs"> Solo mis favoritos</span></label>
</form>
<p class="count" id="count" aria-live="polite">{len(offers)} ofertas</p>"""
        return filters + f'<ul class="grid" id="{list_id}">' + "".join(cards) + "</ul>"

    def side_channels(self):
        links = [ext_link(self.cfg[k], label, cls=f"btn {cls}") for k, label, cls in
                 (("enlace_canal_telegram", "Canal de Telegram", "btn-tg"), ("enlace_canal_whatsapp", "Canal de WhatsApp", "btn-wa"),
                  ("enlace_discord", "Servidor de Discord", "btn-dc"))
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
        parts.append('<a class="btn" href="whatsapp.html">Resumen para WhatsApp</a>')
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
<div class="f-info"><div class="f-top">{self.store_chip(m)}{self.badge(m)}</div>
<h2 class="f-title">{self.title_link(m)}</h2>
{self.price_html(m, big=True)}
{self.countdown(m, "left f-left")}
<div class="cta">{self.offer_button(m)}<button class="btn icon-btn" type="button" data-fav="{e(m['id'])}" aria-pressed="false" aria-label="Guardar {e(m['title'])} en favoritos" hidden>{ICONS['star']}</button></div></div></article>"""
        side = "".join(f"""<li class="f-item"><img src="{e(o['image'])}"{fallback(o)} alt="" width="460" height="215" loading="lazy" decoding="async">
<div class="f-item-info">{self.badge(o)}<h3 class="clamp2">{self.title_link(o)}</h3><p class="f-price{' free' if o.get('currentPrice') == 0 else ''}">{'Gratis' if o.get('currentPrice') == 0 else e(money(o['currentPrice'], o['currency']))}</p>{self.countdown(o)}</div></li>"""
                       for o in picks[1:])
        return f'<section class="feature" aria-label="Ofertas destacadas">{main}<ul class="f-side">{side}</ul></section>'

    def soon_strip(self, offers):
        """Franja horizontal con lo que termina en las próximas 72 horas."""
        soon = sorted((o for o in offers if o.get("expiresAt") and
                       0 < (parse_iso(o["expiresAt"]) - self.now).total_seconds() < 72 * 3600),
                      key=lambda o: o["expiresAt"])[:12]
        if not soon:
            return ""
        items = "".join(f"""<li class="soon-item"><img src="{e(o.get('image') or 'assets/placeholder.svg')}"{fallback(o)} alt="" width="460" height="215" loading="lazy" decoding="async">
<div>{self.badge(o)}<p class="soon-title clamp2">{self.title_link(o)}</p>{self.countdown(o)}</div></li>""" for o in soon)
        return (f'<section class="soon" aria-labelledby="soon-h"><h2 id="soon-h">{ICONS["clock"]} Terminan pronto</h2>'
                f'<ul class="soon-strip">{items}</ul></section>')

    def quick_search(self):
        stores = "".join(f'<a class="chip" href="ofertas.html?tienda={e(st["id"])}"><span class="store-dot store-{e(st["id"])}" aria-hidden="true"></span>{e(st["name"])}</a>'
                         for st in self.stores.values() if st["active"])
        return f"""<section class="quick" aria-label="Buscar ofertas">
<form class="quick-form" action="ofertas.html" method="get" role="search"><label class="sr-only" for="qs">Buscar un juego</label>
<input id="qs" name="q" type="search" placeholder="Busca un juego…" autocomplete="off"><button class="btn btn-primary" type="submit">{ICONS['search']} Buscar</button></form>
<nav class="chips quick-chips" aria-label="Filtros rápidos"><a class="chip hot" href="juegos-gratis.html">Gratis</a><a class="chip" href="ofertas.html?orden=vence">Terminan pronto</a><a class="chip" href="ofertas.html?max=20000">Menos de $20.000</a><a class="chip" href="ofertas.html?min=75">-75% o más</a>{stores}</nav>
</section>"""

    def how_we_verify(self):
        return """<section class="how" aria-labelledby="how-h"><h2 id="how-h">Cómo verificamos los precios</h2><ol class="how-steps">
<li><strong>Tiendas oficiales</strong><span>Solo Steam, Epic, GOG, Humble, Green Man Gaming y Fanatical. Nada de claves de reventa.</span></li>
<li><strong>Revisión cada 4 horas</strong><span>Un sistema automático consulta los precios y retira las ofertas que ya terminaron.</span></li>
<li><strong>Estados claros</strong><span><span class="st ok">Precio para Colombia</span> <span class="st ref">Referencia en USD</span> <span class="st muted">Vigencia por confirmar</span></span></li>
</ol><p><a href="como-verificamos.html">Leer el método completo</a></p></section>"""

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
<div class="detail-media">{img}{self.badge(o)}</div>
<div class="detail-info">{self.store_chip(o)}
<h1>{e(o['title'])}</h1>
{self.price_html(o, big=True)}
{self.countdown(o)}{f'<p class="meta">{e(until)}</p>' if until else ''}
{self.trust_chips(o, full=True)}
<div class="cta">{btn}<button class="btn icon-btn" type="button" data-fav="{e(o['id'])}" aria-pressed="false" aria-label="Guardar {e(o['title'])} en favoritos" hidden>{ICONS['star']}</button><a class="btn" href="ofertas.html">Ver más ofertas</a>{self.alert_button(o, "offer")}</div>
{search_note}<p class="meta">Verificado el {e(date_es(o['verifiedAt']))}.</p>
{notice}</div></article>{self.compare_block(o)}""",
                        crumbs=[("ofertas.html", "Ofertas"), (name, o["title"])], jsonld=[ld], og_image=o.get("image"))

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
            img = f'<img src="{e(g["image"])}"{fallback(g)} alt="Imagen de {e(g["title"])}" width="920" height="430" decoding="async">' if g.get("image") else no_cover(g, "no-cover big")
            tags = "".join(f'<span class="tag">{e(x)}</span>' for x in g.get("platforms", [])) + \
                "".join(f'<span class="tag genre">{e(x)}</span>' for x in g.get("genres", []))
            ld = {"@context": "https://schema.org", "@type": "VideoGame", "name": g["title"], "url": g["url"],
                  "gamePlatform": g.get("platforms"), "genre": g.get("genres")}
            if g.get("image"):
                ld["image"] = g["image"]
            if g.get("precision") == "day":
                ld["datePublished"] = g["date"]
            self.layout(name, f"{g['title']}: fecha de lanzamiento" + ("" if consoles else " en PC"),
                        f"Fecha de lanzamiento de {g['title']} ({', '.join(g.get('platforms', []))}): {when}. Plataformas, géneros y enlace.",
                        f"""<article class="detail">
<div class="detail-media" id="trailer">{img}{f'<span class="badge rel">{e(rel)}</span>' if rel else ''}{self.trailer_link(g)}</div>
<div class="detail-info"><p class="eyebrow">Lanzamiento{" en Steam" if src == "Steam" else ""}</p>
<h1>{e(g['title'])}</h1>
<p class="detail-date">📅 {e(when)}</p>
<div class="tags">{tags}</div>
{f'<p class="lead">{e(g["description"])}</p>' if g.get("description") else ''}
<div class="cta">{self.game_link(g, cls="btn btn-primary")}<a class="btn" href="lanzamientos.html">Ver calendario</a>{self.alert_button(g, "game") if g.get("comingSoon") else ""}
<button class="btn icon-btn" type="button" data-follow="{e(g['id'])}" aria-pressed="false" aria-label="Seguir {e(g['title'])}" hidden>🔔 Seguir</button></div>
<p class="meta">La fecha es la que publica {src} y puede cambiar.{' Resumen e imagen: Wikipedia en español (CC BY-SA 4.0).' if src == "Wikidata" and g.get("description") else ''} Verificado: {e(date_es(g.get('verifiedAt')))}.</p></div></article>""",
                        crumbs=[("lanzamientos.html", "Lanzamientos"), (name, g["title"])], jsonld=[ld], og_image=g.get("image"))

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

    def trailer_chip(self, g):
        page = self.detail.get(g["id"])
        if not page or not ((g.get("trailer") or {}).get("video") or (g.get("trailer") or {}).get("hls") or g.get("youtube")):
            return ""
        return f'<a class="trailer-chip" href="{page}#trailer" aria-label="Tráiler de {e(g["title"])}">{ICONS["play"]}</a>'

    def rank(self, g):
        return getattr(self, "ranks", {}).get(g["id"], 9999)

    def release_card(self, g, now, compact=True):
        hot = self.rank(g) <= 25
        img = g.get("image") or "assets/placeholder.svg"
        alt = f"Imagen de {g['title']}" if g.get("image") else ""
        plats = "".join(f'<span class="ver">{e(p)}</span>' for p in g.get("platforms", []))
        genres = "".join(f'<span class="tag genre">{e(x)}</span>' for x in g.get("genres", [])[:2])
        rel = relative_label(g.get("date"), g.get("precision"), now)
        when = date_label(g.get("date"), g.get("precision"))
        link = self.game_link(g, g.get("store") or "Steam")
        return f"""<li class="rel-card{' is-hot' if hot else ''}" data-id="{e(g['id'])}" data-title="{e(g['title'].lower())}" data-date="{e(g.get('date') or '')}" data-precision="{e(g.get('precision') or '')}" data-platforms="{e('|'.join(g.get('platforms', [])))}" data-genres="{e('|'.join(g.get('genres', [])))}">
<div class="rel-img">{f'<img src="{e(img)}"{fallback(g)} alt="{e(alt)}" width="460" height="215" loading="lazy" decoding="async">' if g.get("image") else no_cover(g)}{f'<span class="badge rel">{e(rel)}</span>' if rel and not compact else ''}{f'<span class="hot-tag">{ICONS["flame"]} Muy esperado</span>' if hot else ''}{self.trailer_chip(g)}</div>
<p class="rel-name">{self.title_link(g)}</p>
<p class="rel-vers"><span class="rel-type" aria-hidden="true">🎮</span>{plats}</p>
{'' if compact else f'<p class="meta">{e(when)}</p>'}
<div class="tags">{genres}</div>
<div class="rel-actions">{link}<button class="btn btn-sm icon-btn" type="button" data-follow="{e(g['id'])}" aria-pressed="false" aria-label="Seguir {e(g['title'])}" hidden>🔔</button></div></li>"""

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
            out.append(f'<section class="rel-day {kind}" aria-label="{e(label)}"><h3 class="rel-head">'
                       f'<span class="rel-dot" aria-hidden="true"></span><span class="rel-big">{e(big)}</span>'
                       f'<span class="rel-sub">{e(rel)}</span><span class="rel-line" aria-hidden="true"></span>'
                       f'<span class="rel-crumb">Juegos · {len(items)}</span></h3>'
                       f'<ul class="rel-grid">{"".join(self.release_card(g, now, compact) for g in items)}</ul></section>')
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
        bg = f'<img class="spot-bg" src="{e(img)}"{fallback(g)} alt="" width="460" height="215" loading="lazy" decoding="async">' if main and g.get("image") else ""
        fg = (f'<img class="spot-fg" src="{e(img)}"{fallback(g)} alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async">'
              if g.get("image") else no_cover(g, "no-cover spot-fg"))
        return f"""<li class="spot-card{' spot-main' if main else ''}"><div class="spot-img">{bg}{fg}<span class="spot-rank">#{self.rank(g)}</span>{self.trailer_chip(g)}{f'<span class="badge rel">{e(rel)}</span>' if rel else ''}</div>
<div class="spot-body"><p class="spot-date">{ICONS['calendar']}{e(when)}</p><h3 class="clamp2">{self.title_link(g)}</h3>{f'<p class="spot-desc">{e(desc)}</p>' if desc else ''}<div class="tags">{genres}</div>
<div class="rel-actions">{link}<button class="btn btn-sm icon-btn" type="button" data-follow="{e(g['id'])}" aria-pressed="false" aria-label="Seguir {e(g['title'])}" hidden>{ICONS['bell']}</button></div></div></li>"""

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
<button type="button" class="tab" data-view="hot" aria-pressed="true">🔥 Destacados</button>
<button type="button" class="tab" data-view="week" aria-pressed="false">Esta semana</button>
<button type="button" class="tab" data-view="month" aria-pressed="false">Este mes</button>
<button type="button" class="tab" data-view="all" aria-pressed="false">Todo</button>
<button type="button" class="tab" data-view="follow" aria-pressed="false">🔔 Siguiendo</button>
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
                    f"""<div class="rel-top"><div><h1>Calendario de <span class="grad">lanzamientos</span></h1>
<p class="lead">Los próximos juegos de PC y consolas y los estrenos recientes, día por día. Las fechas son las que publica cada tienda y pueden cambiar.</p>
{updated_line}</div></div>
{self.spotlight(games, now)}
{self.anticipated(games, now)}
<h2 class="all-rel">Calendario completo</h2>
{toolbar}
<p class="count" id="rel-count" aria-live="polite">{len(games)} juegos</p>
<div id="rel-list">{body or '<p class="notice">Todavía no hay lanzamientos cargados. Vuelve en unas horas.</p>'}</div>
<p class="notice" id="rel-empty" hidden>No hay juegos con estos filtros. Prueba con «Todo» o quita algún filtro.</p>{credit}""",
                    crumbs=[("lanzamientos.html", "Lanzamientos")], jsonld=[ld])

    def upcoming_home(self, games, now):
        limit = (now + timedelta(days=30)).strftime("%Y-%m-%d")
        upcoming = sorted([g for g in self.split_releases(games, now)[0] if g.get("precision") == "day" and g["date"] <= limit],
                          key=self.rank)[:6]
        upcoming.sort(key=lambda g: g["date"])
        if not upcoming:
            return ""
        return ('<h2>Próximos lanzamientos más esperados</h2><ul class="rel-grid">' +
                "".join(self.release_card(g, now, compact=False) for g in upcoming) +
                '</ul><p><a class="btn" href="lanzamientos.html">Ver el calendario completo</a></p>')

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
        notes = []
        for key in sorted((k for k in days if k), reverse=True)[:10]:
            d = days[key]
            deals = sorted(d["deals"], key=lambda o: -(o.get("discountPercentage") or 0))
            rel = sorted(d["games"], key=self.rank)
            parts = []
            if d["free"]:
                parts.append(f'<section class="n-sec"><h3>{ICONS["gift"]} Juegos gratis nuevos</h3><ul>' +
                             "".join(self.note_row(o, "offer", now) for o in d["free"]) + "</ul></section>")
            if rel:
                parts.append(f'<section class="n-sec"><h3>{ICONS["sparkle"]} Estrenos</h3><ul>' +
                             "".join(self.note_row(g, "game", now) for g in rel[:8]) + "</ul></section>")
            if deals:
                more = f'<p class="n-more"><a href="ofertas.html">Y {len(deals) - 10} ofertas más</a></p>' if len(deals) > 10 else ""
                parts.append(f'<section class="n-sec"><h3>{ICONS["flame"]} Nuevas ofertas</h3><ul>' +
                             "".join(self.note_row(o, "offer", now) for o in deals[:10]) + f"</ul>{more}</section>")
            counts = " · ".join(x for x in (
                f"{len(d['free'])} gratis" if d["free"] else "", f"{len(rel)} estrenos" if rel else "",
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
        pages = [
            ("juegos-baratos.html", "Juegos de PC baratos en pesos colombianos", "Juegos de PC por menos de $20.000 COP",
             "Juegos de PC en oferta que cuestan menos de $20.000 pesos colombianos (valor aproximado), en tiendas oficiales.", cheap),
            ("ofertas-90-por-ciento.html", "Juegos con 90% de descuento o más", "Juegos con 90% de descuento o más",
             "Los descuentos más grandes del día en tiendas oficiales de PC: 90% o más.", huge),
            ("ofertas-terminan-pronto.html", "Ofertas de juegos que terminan pronto", "Ofertas que terminan esta semana",
             "Juegos gratis y descuentos con fecha de fin en los próximos 7 días. Aprovecha antes de que terminen.", ending),
        ]
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

    def f2p_page(self, f2p, updated_line):
        if f2p:
            cards = "".join(
                f'<li class="spot-card"><div class="spot-img"><img class="spot-fg" src="{e(g["image"])}" alt="Imagen de {e(g["title"])}" width="460" height="215" loading="lazy" decoding="async"></div>'
                f'<div class="spot-body"><h3 class="clamp2">{e(g["title"])}</h3><div class="rel-actions">'
                f'{ext_link(g["url"], "Jugar gratis en Steam", cls="btn btn-primary btn-sm btn-free", label=f"Jugar {g["title"]} gratis en Steam (abre en otra pestaña)")}</div></div></li>'
                for g in f2p)
            listing = f'<ul class="spot-grid small">{cards}</ul>'
        else:
            listing = '<p class="notice">Todavía no se cargó la lista. Vuelve en unas horas.</p>'
        self.layout("juegos-gratis-para-siempre.html", "Juegos gratis para siempre en PC (free to play)",
                    "Los juegos gratis para siempre más jugados en Steam ahora mismo: free to play que puedes descargar sin pagar.",
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

        archive = "".join(f'<li><a href="{weekly.page_name(h)}">Resumen del {e(h["label"])}</a></li>' for h in history)
        archive_html = f'<h2>Resúmenes anteriores</h2><ul class="archive">{archive}</ul>' if archive else ""
        lead = ("Lo mejor de la semana: juegos gratis, los descuentos más grandes y los estrenos. Sale solo cada viernes en "
                '<a href="' + e(self.cfg.get("enlace_canal_telegram", "")) + '" target="_blank" rel="noopener noreferrer">Telegram</a>, Discord y Bluesky.')
        title = f"Resumen semanal del {snap['label']}" if current else "Lo mejor de esta semana (hasta ahora)"
        self.layout("resumen-semanal.html", "Resumen semanal de ofertas gamer para Colombia",
                    "Cada viernes: juegos gratis, los mejores descuentos de PC y los estrenos de la semana, en un solo lugar.",
                    f'<h1>Resumen semanal</h1><p class="lead">{lead}</p>{updated_line}<h2>{e(title)}</h2>{render(snap)}{archive_html}',
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
        self.ranks = {g["id"]: g.get("rank") or i + 1 for i, g in enumerate(games or [])}
        free = [o for o in live if o.get("currentPrice") == 0]
        deals = [o for o in live if o.get("currentPrice")]
        soon = sorted([o for o in live if o.get("expiresAt")], key=lambda o: o["expiresAt"])[:6]
        top = sorted(deals, key=lambda o: (-("CO" in (o.get("regions") or [])), -(o.get("metacritic") or 0) // 10,
                                           -(o.get("discountPercentage") or 0)))[:12]
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
                    f"""<section class="hero compact">
<p class="eyebrow">Radar de ofertas gamer · Colombia</p>
<h1>Juegos <span class="grad">gratis</span> y ofertas de PC, verificados</h1>
<ul class="stats mini">
<li><strong data-count="{len(free)}">{len(free)}</strong><span>gratis ahora</span></li>
<li><strong data-count="{len(deals)}">{len(deals)}</strong><span>ofertas activas</span></li>
<li><strong data-count="{max((o.get('discountPercentage') or 0) for o in deals) if deals else 0}" data-suffix="%">{max((o.get('discountPercentage') or 0) for o in deals) if deals else 0}%</strong><span>mayor descuento</span></li>
</ul>
{updated_line}
</section>
{self.feature(free + top)}
{self.soon_strip(live)}
{self.quick_search()}
{self.ad_slot("banner_after_hero")}
<h2>{ICONS['gift']} Gratis esta semana</h2>
{self.offer_list(free[:8], with_filters=False, list_id="free-home") if free else '<p>No hay juegos gratis activos en este momento. Te avisamos en Telegram cuando salga uno.</p>'}
{f'<p><a class="btn" href="juegos-gratis.html">Ver los {len(free)} juegos gratis</a></p>' if len(free) > 8 else ''}
<h2>{ICONS['flame']} Mejores ofertas verificadas</h2>
{self.offer_list(top, with_filters=False, list_id="top-home")}
<p><a class="btn btn-primary" href="ofertas.html">Ver las {len(live)} ofertas con buscador y filtros</a></p>
{self.upcoming_home(games or [], updated_dt)}
{self.how_we_verify()}
<section class="channels"><h2>{ICONS['bell']} Recibe las ofertas al instante</h2><p class="lead">Las mejores ofertas llegan solas a Telegram, Discord y Bluesky cada 4 horas.</p>{self.channels_cta()}</section>
<p class="meta small-notice">Los precios pueden cambiar en cualquier momento: confirma siempre en la tienda antes de comprar. Los valores en pesos son aproximados.</p>""", jsonld=[org, website, self.item_list_ld(live)])

        self.layout("juegos-gratis.html", "Juegos gratis para PC hoy",
                    "Juegos gratuitos para PC disponibles ahora en tiendas oficiales como Epic Games Store, con la fecha en que termina cada promoción.",
                    f"<h1>Juegos gratis para PC</h1><p class=\"lead\">Juegos que puedes reclamar gratis por tiempo limitado en tiendas oficiales.</p>{updated_line}{notice}{self.offer_list(free)}<p>¿Primera vez? Lee <a href=\"guia-juegos-gratis-temporales.html\">cómo funcionan los juegos gratuitos temporales</a>.</p>",
                    crumbs=[("juegos-gratis.html", "Juegos gratis")], jsonld=[self.item_list_ld(free)])

        self.layout("ofertas.html", "Ofertas y descuentos de videojuegos",
                    "Descuentos de juegos de PC en Steam, GOG, Humble Store, Green Man Gaming, Fanatical y Epic, con precio original, precio actual y porcentaje de descuento.",
                    f"<h1>Todas las ofertas</h1><p class=\"lead\">{len(free)} juegos gratis y {len(deals)} descuentos de {self.cfg['filtros_ofertas']['descuento_minimo']}% o más en tiendas oficiales. Busca, filtra y guarda tus favoritos.</p>{updated_line}{notice}{self.offer_list(free + deals)}",
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

        self.releases_page(games or [], updated_dt, updated_line)
        self.collection_pages(live, games or [], updated_dt, updated_line, notice)
        self.f2p_page(getattr(self, "f2p", []), updated_line)
        self.alerts_page()
        self.weekly_pages(getattr(self, "weekly_history", []), live, games or [], updated_dt, updated_line)
        self.offer_pages(live, notice)
        self.game_pages(games or [], updated_dt)
        self.static_pages(status, updated)
        self.whatsapp_page(live, updated)
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
<p>Usamos el almacenamiento local del navegador solo para dos preferencias opcionales: los favoritos (<code>ogc-favs</code>) y el tema claro u oscuro (<code>ogc-theme</code>). No se envían a ningún servidor.</p>
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

    def whatsapp_page(self, offers, updated):
        text = whatsapp_text(offers, self.cfg, updated)
        self.layout("whatsapp.html", "Resumen para WhatsApp", "Resumen de ofertas listo para copiar y pegar en un canal de WhatsApp.",
                    f"""<h1>Resumen para WhatsApp</h1>
<p class="lead">Toca "Copiar texto", abre tu canal de WhatsApp y pega. Actualizado: {e(updated)}.</p>
<p><button class="btn btn-wa" id="copy-wa" type="button">Copiar texto</button></p>
<label for="wa-text" class="meta">Texto del resumen</label>
<textarea class="wa" id="wa-text" readonly>{e(text)}</textarea>""", noindex=True)
        self.write("whatsapp.txt", text)

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
        urls = "".join(f"<url><loc>{self.base}{'' if p == 'index.html' else p}</loc><lastmod>{day}</lastmod></url>" for p in self.pages)
        self.write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                  f"{urls}</urlset>\n")
        self.write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {self.base}sitemap.xml\n")
