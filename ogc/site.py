"""Genera el sitio estático (docs/), los feeds, el sitemap y el resumen de WhatsApp."""

import html
import json
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from .channels import cop_text, date_es, money, region_text, whatsapp_text
from .content import FAQ, GUIDES, LEGAL_REVIEW, LEGAL_UPDATED
from .model import parse_iso
from .releases import date_label, relative_label, MONTHS_ES

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
REPO = "https://github.com/mpereira17-uc/ofertas-gamer-co"
DISCLOSURE = ("Algunos enlaces publicados pueden ser enlaces de afiliados. Si realizas una compra mediante "
              "ellos podemos recibir una comisión sin costo adicional para ti.")

NAV = [
    ("Ofertas", [("index.html", "Inicio", "⌂"), ("juegos-gratis.html", "Juegos gratis", "🎁"),
                 ("ofertas.html", "Ofertas", "🔥"), ("noticias.html", "Novedades", "📰")]),
    ("Lanzamientos", [("lanzamientos.html", "Calendario", "📅"), ("lanzamientos.html#proximos", "Próximos", "⏳"),
                      ("lanzamientos.html#recientes", "Recientes", "🆕"), ("lanzamientos.html#por-confirmar", "Por confirmar", "❔")]),
    ("Ayuda", [("guias.html", "Guías", "📘"), ("preguntas-frecuentes.html", "Preguntas", "💬"),
               ("como-verificamos.html", "Cómo verificamos", "✔")]),
]
FOOTER = [
    ("como-verificamos.html", "Cómo verificamos"), ("quienes-somos.html", "Quiénes somos"),
    ("contacto.html", "Contacto"), ("privacidad.html", "Privacidad"), ("cookies.html", "Cookies"),
    ("afiliados.html", "Aviso de afiliados"), ("publicidad.html", "Publicidad y patrocinios"),
    ("terminos.html", "Términos de uso"), ("anunciate.html", "Anúnciate"), ("estado.html", "Estado del sistema"),
    ("fuentes.html", "Fuentes de información"), ("whatsapp.html", "Resumen para WhatsApp"),
]
CSP = ("default-src 'self'; img-src 'self' https: data:; script-src 'self'; style-src 'self'; "
       "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
       "upgrade-insecure-requests")

e = html.escape


def ext_link(url, text, affiliate=False, cls="btn btn-primary", label=None):
    rel = "sponsored nofollow noopener noreferrer" if affiliate else "noopener noreferrer"
    aria = f' aria-label="{e(label)}"' if label else ""
    return f'<a class="{cls}" href="{e(url)}" target="_blank" rel="{rel}"{aria}>{text}</a>'



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

    # ---------- plantilla común ----------
    def layout(self, name, title, description, body, crumbs=None, jsonld=None, noindex=False, og_type="website", og_image=None):
        canonical = self.base + ("" if name == "index.html" else name)
        full_title = title if name == "index.html" else f"{title} | {self.cfg['nombre']}"
        stores_nav = [(f"ofertas.html?tienda={st['id']}", st["name"], "🏬") for st in self.stores.values() if st["active"]]
        groups = NAV[:1] + [("Tiendas", stores_nav)] + NAV[1:]
        nav = "".join(
            f'<div class="side-group"><p class="side-title">{e(title)}</p><ul>' + "".join(
                f'<li><a href="{href}"{" aria-current=\"page\"" if href == name else ""}>'
                f'<span class="side-ico" aria-hidden="true">{ico}</span>{e(label)}</a></li>' for href, label, ico in links) + "</ul></div>"
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
            if self.cfg.get("verificacion_google"):
                verif += f'<meta name="google-site-verification" content="{e(self.cfg["verificacion_google"])}">\n'
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
<meta name="theme-color" content="#07070d">
<link rel="icon" href="assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="Ofertas Gamer CO (RSS)" href="rss.xml">
<link rel="alternate" type="application/atom+xml" title="Ofertas Gamer CO (Atom)" href="atom.xml">
<link rel="alternate" type="application/feed+json" title="Ofertas Gamer CO (JSON)" href="feed.json">
<link rel="stylesheet" href="assets/styles.css">
<script src="assets/app.js" defer></script>
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
<p>{e(DISCLOSURE)}</p>
<nav aria-label="Pie de página"><ul>{foot}</ul></nav>
<p>Ofertas Gamer CO no vende productos ni procesa pagos. Los precios y la disponibilidad pueden cambiar sin previo aviso.</p>
</div></footer>
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

    def card(self, o):
        free = o.get("currentPrice") == 0
        badge = '<span class="badge free">GRATIS</span>' if free else \
            (f'<span class="badge">-{o["discountPercentage"]}%</span>' if o.get("discountPercentage") else "")
        img = o.get("image") or "assets/placeholder.svg"
        alt = f"Imagen de {o['title']}" if o.get("image") else ""
        if free:
            price = '<p class="price">Gratis' + (f' <s>{e(money(o.get("originalPrice"), o["currency"]))}</s>' if o.get("originalPrice") else "") + "</p>"
        else:
            price = f'<p class="price">{e(money(o["currentPrice"], o["currency"]))}' + \
                    (f' <s>{e(money(o["originalPrice"], o["currency"]))}</s>' if o.get("originalPrice") else "") + "</p>"
            if cop_text(o):
                price += f'<p class="meta">{e(cop_text(o))}</p>'
        tags = [f'<span class="tag">{e(o.get("platform") or "PC")}</span>']
        if o.get("drm"):
            tags.append(f'<span class="tag">Activación: {e(o["drm"])}</span>')
        if o.get("affiliate"):
            tags.append('<span class="tag aff">Enlace de afiliado</span>')
        if o.get("sponsored"):
            tags.append('<span class="tag aff">Patrocinado</span>')
        expires = f"Hasta el {date_es(o['expiresAt'])}" if o.get("expiresAt") else "Vigencia: fecha desconocida"
        btn = ext_link(o["destinationUrl"], "Ver oferta", o.get("affiliate"),
                       label=f"Ver oferta de {o['title']} en {o['store']} (abre en otra pestaña)")
        return f"""<li class="card" data-id="{e(o['id'])}" data-title="{e(o['title'].lower())}" data-store="{e(o['storeId'])}" data-type="{'gratis' if free else 'descuento'}" data-discount="{100 if free else (o.get('discountPercentage') or 0)}" data-expires="{e(o.get('expiresAt') or '')}" data-price="{o.get('currentPrice') or 0}">
<div class="thumb"><img src="{e(img)}"{fallback(o)} alt="{e(alt)}" width="460" height="215" loading="lazy" decoding="async">{badge}</div>
<div class="body"><h3>{self.title_link(o)}</h3>
<p class="meta">Tienda: {e(o['store'])}</p>
{price}
<div class="tags">{''.join(tags)}</div>
<p class="meta"><span class="status">{e(o['status'])}</span> · {e(expires)}</p>
<p class="meta">Región: {e(region_text(o))}</p>
<p class="meta">Verificado: {e(date_es(o['verifiedAt']))}</p>
<div class="actions">{btn}<button class="btn icon-btn" type="button" data-fav="{e(o['id'])}" aria-pressed="false" aria-label="Guardar {e(o['title'])} en favoritos" hidden>★</button><button class="btn icon-btn" type="button" data-share="{e(o['destinationUrl'])}" data-title="{e(o['title'])}" aria-label="Compartir {e(o['title'])}" hidden>↗</button></div>
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
<label>Ordenar por<select name="sort"><option value="discount">Mayor descuento</option><option value="expires">Vence primero</option><option value="price">Menor precio</option><option value="title">Nombre</option></select></label>
<label><span>Favoritos</span><span><input type="checkbox" name="favs"> Solo mis favoritos</span></label>
</form>
<p class="count" id="count" aria-live="polite">{len(offers)} ofertas</p>"""
        return filters + f'<ul class="grid" id="{list_id}">' + "".join(cards) + "</ul>"

    def side_channels(self):
        tg = self.cfg.get("enlace_canal_telegram")
        if not tg:
            return ""
        return '<div class="side-group side-cta">' + ext_link(tg, "Canal de Telegram", cls="btn btn-tg") + "</div>"

    def channels_cta(self):
        parts = []
        if self.cfg.get("enlace_canal_telegram"):
            parts.append(ext_link(self.cfg["enlace_canal_telegram"], "Recibe las ofertas en Telegram", cls="btn btn-tg"))
        if self.cfg.get("enlace_canal_whatsapp"):
            parts.append(ext_link(self.cfg["enlace_canal_whatsapp"], "Canal de WhatsApp", cls="btn btn-wa"))
        parts.append('<a class="btn" href="whatsapp.html">Resumen para WhatsApp</a>')
        return '<div class="cta">' + "".join(parts) + "</div>"

    def slider(self, offers):
        seen, picks = set(), []
        for o in offers:
            if o["id"] not in seen and o.get("image"):
                seen.add(o["id"])
                picks.append(o)
        picks = picks[:8]
        if not picks:
            return ""
        slides = []
        for i, o in enumerate(picks):
            free = o.get("currentPrice") == 0
            badge = "GRATIS" if free else f"-{o.get('discountPercentage') or 0}%"
            if free:
                price = "Gratis"
            else:
                price = e(money(o["currentPrice"], o["currency"]))
            old = f' <s>{e(money(o["originalPrice"], o["currency"]))}</s>' if o.get("originalPrice") else ""
            cop = f'<span class="s-cop">{e(cop_text(o))}</span>' if not free and cop_text(o) else ""
            until = f'<span class="s-until">Hasta el {e(date_es(o["expiresAt"]))}</span>' if o.get("expiresAt") else ""
            btn = ext_link(o["destinationUrl"], "Ver oferta", o.get("affiliate"),
                           label=f"Ver oferta de {o['title']} en {o['store']} (abre en otra pestaña)")
            slides.append(f"""<li class="slide{' free' if free else ''}" id="slide-{i + 1}" aria-roledescription="diapositiva" aria-label="{i + 1} de {len(picks)}">
<img src="{e(o['image'])}"{fallback(o)} alt="" width="1280" height="600"{' fetchpriority="high"' if i == 0 else ' loading="lazy"'} decoding="async">
<div class="slide-info"><span class="s-badge">{badge}</span><p class="s-store">{e(o['store'])}</p>
<h2 class="s-title">{e(o['title'])}</h2>
<p class="s-price">{price}{old}</p><p class="s-meta">{cop}{until}</p>
<div class="s-cta">{btn}</div></div></li>""")
        dots = "".join(f'<a href="#slide-{i + 1}" aria-label="Ir a la oferta {i + 1}"></a>' for i in range(len(picks)))
        return (f'<section class="slider" aria-roledescription="carrusel" aria-label="Ofertas destacadas">'
                f'<ul class="slides" id="slides" tabindex="0">{"".join(slides)}</ul>'
                f'<button class="s-nav prev" type="button" aria-label="Oferta anterior" hidden>‹</button>'
                f'<button class="s-nav next" type="button" aria-label="Oferta siguiente" hidden>›</button>'
                f'<nav class="s-dots" aria-label="Elegir oferta">{dots}</nav>'
                f'<div class="s-bar" aria-hidden="true"><span></span></div></section>')

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

    def offer_pages(self, offers, notice):
        for o in offers:
            name = self.detail.get(o["id"])
            if not name:
                continue
            free = o.get("currentPrice") == 0
            what = "gratis" if free else f"con {o.get('discountPercentage') or 0}% de descuento"
            price = "Gratis" if free else e(money(o["currentPrice"], o["currency"]))
            old = f' <s>{e(money(o["originalPrice"], o["currency"]))}</s>' if o.get("originalPrice") else ""
            cop = f'<p class="meta">{e(cop_text(o))}</p>' if not free and cop_text(o) else ""
            until = f"Hasta el {date_es(o['expiresAt'])}" if o.get("expiresAt") else "Vigencia: fecha desconocida"
            img = f'<img src="{e(o["image"])}"{fallback(o)} alt="Imagen de {e(o["title"])}" width="920" height="430" decoding="async">' if o.get("image") else ""
            btn = ext_link(o["destinationUrl"], f"Ver oferta en {e(o['store'])}", o.get("affiliate"),
                           label=f"Ver oferta de {o['title']} en {o['store']} (abre en otra pestaña)")
            ld = {"@context": "https://schema.org", "@type": "Product", "name": o["title"], "image": o.get("image") or None,
                  "offers": {"@type": "Offer", "price": o.get("currentPrice"), "priceCurrency": o["currency"],
                             "url": o["officialUrl"], "availability": "https://schema.org/InStock",
                             "seller": {"@type": "Organization", "name": o["store"]},
                             **({"priceValidUntil": o["expiresAt"][:10]} if o.get("expiresAt") else {})}}
            ld = {k: v for k, v in ld.items() if v is not None}
            self.layout(name, f"{o['title']} {what} en {o['store']}",
                        f"{o['title']} está {what} en {o['store']}. Precio, vigencia y enlace oficial verificados por Ofertas Gamer CO.",
                        f"""<article class="detail">
<div class="detail-media">{img}<span class="badge{' free' if free else ''}">{'GRATIS' if free else '-' + str(o.get('discountPercentage') or 0) + '%'}</span></div>
<div class="detail-info"><p class="eyebrow">{e(o['store'])}</p>
<h1>{e(o['title'])}</h1>
<p class="s-price detail-price">{price}{old}</p>{cop}
<p class="meta"><span class="status">{e(o['status'])}</span> · {e(until)}</p>
<p class="meta">Región: {e(region_text(o))} · Verificado: {e(date_es(o['verifiedAt']))}</p>
<div class="cta">{btn}<a class="btn" href="ofertas.html">Ver más ofertas</a></div>
{notice}</div></article>""",
                        crumbs=[("ofertas.html", "Ofertas"), (name, o["title"])], jsonld=[ld], og_image=o.get("image"))

    def game_pages(self, games, now):
        for g in games:
            name = self.detail.get(g["id"])
            if not name:
                continue
            when = date_label(g.get("date"), g.get("precision"))
            rel = relative_label(g.get("date"), g.get("precision"), now)
            img = f'<img src="{e(g["image"])}" alt="Imagen de {e(g["title"])}" width="920" height="430" decoding="async">' if g.get("image") else ""
            tags = "".join(f'<span class="tag">{e(x)}</span>' for x in g.get("platforms", [])) + \
                "".join(f'<span class="tag genre">{e(x)}</span>' for x in g.get("genres", []))
            ld = {"@context": "https://schema.org", "@type": "VideoGame", "name": g["title"], "url": g["url"],
                  "gamePlatform": g.get("platforms"), "genre": g.get("genres")}
            if g.get("image"):
                ld["image"] = g["image"]
            if g.get("precision") == "day":
                ld["datePublished"] = g["date"]
            self.layout(name, f"{g['title']}: fecha de lanzamiento en PC",
                        f"Fecha de lanzamiento de {g['title']} en Steam: {when}. Sistemas, géneros y enlace oficial.",
                        f"""<article class="detail">
<div class="detail-media">{img}{f'<span class="badge rel">{e(rel)}</span>' if rel else ''}</div>
<div class="detail-info"><p class="eyebrow">Lanzamiento en Steam</p>
<h1>{e(g['title'])}</h1>
<p class="detail-date">📅 {e(when)}</p>
<div class="tags">{tags}</div>
{f'<p class="lead">{e(g["description"])}</p>' if g.get("description") else ''}
<div class="cta">{ext_link(g["url"], "Ver en Steam", cls="btn btn-primary", label=f"Ver {g['title']} en Steam (abre en otra pestaña)")}<a class="btn" href="lanzamientos.html">Ver calendario</a>
<button class="btn icon-btn" type="button" data-follow="{e(g['id'])}" aria-pressed="false" aria-label="Seguir {e(g['title'])}" hidden>🔔 Seguir</button></div>
<p class="meta">La fecha es la que publica Steam y puede cambiar. Verificado: {e(date_es(g.get('verifiedAt')))}.</p></div></article>""",
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

    def release_card(self, g, now, compact=True):
        img = g.get("image") or "assets/placeholder.svg"
        alt = f"Imagen de {g['title']}" if g.get("image") else ""
        plats = "".join(f'<span class="ver">{e(p)}</span>' for p in g.get("platforms", []))
        genres = "".join(f'<span class="tag genre">{e(x)}</span>' for x in g.get("genres", [])[:2])
        rel = relative_label(g.get("date"), g.get("precision"), now)
        when = date_label(g.get("date"), g.get("precision"))
        link = ext_link(g["url"], "Steam", cls="btn btn-primary btn-sm", label=f"Ver {g['title']} en Steam (abre en otra pestaña)")
        return f"""<li class="rel-card" data-id="{e(g['id'])}" data-title="{e(g['title'].lower())}" data-date="{e(g.get('date') or '')}" data-precision="{e(g.get('precision') or '')}" data-platforms="{e('|'.join(g.get('platforms', [])))}" data-genres="{e('|'.join(g.get('genres', [])))}">
<div class="rel-img"><img src="{e(img)}" alt="{e(alt)}" width="460" height="215" loading="lazy" decoding="async">{f'<span class="badge rel">{e(rel)}</span>' if rel and not compact else ''}</div>
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
            items = groups[key]
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

    def releases_page(self, games, now, updated_line):
        upcoming, recent, tba = self.split_releases(games, now)
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
<div class="chips" role="group" aria-label="Sistema">{''.join(chip('platform', x) for x in ('Windows', 'Mac', 'Linux'))}</div>
<div class="chips" role="group" aria-label="Género">{''.join(chip('genre', x) for x in genres)}</div>
</div>"""
        body = (self.release_groups(upcoming, now, "Próximos lanzamientos", "proximos") +
                self.release_groups(recent, now, "Lanzados recientemente", "recientes") +
                self.release_groups(tba, now, "Fecha por confirmar", "por-confirmar"))
        ld = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": g["title"], "url": g["url"]} for i, g in enumerate(upcoming[:30])]}
        self.layout("lanzamientos.html", "Calendario de lanzamientos de juegos de PC",
                    "Próximos lanzamientos y estrenos recientes de juegos de PC en Steam, con la fecha que publica la tienda, sistemas y géneros.",
                    f"""<div class="rel-top"><div><h1>Calendario de <span class="grad">lanzamientos</span></h1>
<p class="lead">Los próximos juegos de PC y los estrenos recientes en Steam, día por día. Las fechas son las que publica cada tienda y pueden cambiar.</p>
{updated_line}</div></div>
{toolbar}
<p class="count" id="rel-count" aria-live="polite">{len(games)} juegos</p>
<div id="rel-list">{body or '<p class="notice">Todavía no hay lanzamientos cargados. Vuelve en unas horas.</p>'}</div>
<p class="notice" id="rel-empty" hidden>No hay juegos con estos filtros. Prueba con «Todo» o quita algún filtro.</p>""",
                    crumbs=[("lanzamientos.html", "Lanzamientos")], jsonld=[ld])

    def upcoming_home(self, games, now):
        upcoming = self.split_releases(games, now)[0][:6]
        if not upcoming:
            return ""
        return ('<h2>Próximos lanzamientos</h2><ul class="rel-grid">' +
                "".join(self.release_card(g, now, compact=False) for g in upcoming) +
                '</ul><p><a class="btn" href="lanzamientos.html">Ver el calendario completo</a></p>')

    def ticker(self, offers):
        if not offers:
            return ""
        items = "".join(
            f'<li><span class="t-badge">{"GRATIS" if o.get("currentPrice") == 0 else "-" + str(o.get("discountPercentage") or 0) + "%"}</span>{e(o["title"])}</li>'
            for o in offers[:12])
        return (f'<div class="ticker" aria-label="Destacados de hoy"><ul class="ticker-track">{items}</ul>'
                f'<ul class="ticker-track" aria-hidden="true">{items}</ul></div>')

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
        updated = updated_dt.strftime("%d/%m/%Y %H:%M UTC")
        live = [o for o in offers if o["status"] != "Vencido"]
        self.assign_pages(live, games or [])
        free = [o for o in live if o.get("currentPrice") == 0]
        deals = [o for o in live if o.get("currentPrice")]
        soon = sorted([o for o in live if o.get("expiresAt")], key=lambda o: o["expiresAt"])[:6]
        top = sorted(deals, key=lambda o: -(o.get("discountPercentage") or 0))[:6]
        notice = ('<p class="notice">Los precios y promociones pueden haber cambiado desde la última verificación. '
                  'Confirma siempre en la tienda antes de comprar. Los valores en pesos son aproximados.</p>')
        updated_line = f'<p class="meta">Última actualización: <time datetime="{updated_dt.strftime("%Y-%m-%dT%H:%M:%SZ")}">{updated}</time> · se actualiza cada {self.cfg["intervalo_horas"]} horas</p>'

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
                    f"""{self.slider(free + top)}
<section class="hero">
<p class="eyebrow">Juegos de PC · Colombia y Latinoamérica</p>
<h1>Juegos <span class="grad">gratis</span> y ofertas de PC en tiendas oficiales</h1>
<p class="lead">Ofertas Gamer CO reúne juegos gratuitos y descuentos verificados de tiendas oficiales para Colombia y Latinoamérica. Te mostramos la tienda, el precio, la vigencia y el enlace, y tú compras directamente en la tienda.</p>
{self.channels_cta()}
<ul class="stats">
<li><strong data-count="{len(free)}">{len(free)}</strong><span>juegos gratis ahora</span></li>
<li><strong data-count="{len(deals)}">{len(deals)}</strong><span>ofertas activas</span></li>
<li><strong data-count="{len({o['storeId'] for o in live})}">{len({o['storeId'] for o in live})}</strong><span>tiendas oficiales</span></li>
<li><strong data-count="{max((o.get('discountPercentage') or 0) for o in deals) if deals else 0}" data-suffix="%">{max((o.get('discountPercentage') or 0) for o in deals) if deals else 0}%</strong><span>mayor descuento</span></li>
</ul>
{updated_line}
</section>
{self.ticker(free + top)}
{self.ad_slot("banner_after_hero")}
{notice}
<h2>Juegos gratis disponibles</h2>
{self.offer_list(free, with_filters=False, list_id="free-home") if free else '<p>No hay juegos gratis activos en este momento.</p>'}
<h2>Mejores descuentos</h2>
{self.offer_list(top, with_filters=False, list_id="top-home")}
{'<h2>Próximas a vencer</h2>' + self.offer_list(soon, with_filters=False, list_id="soon-home") if soon else ''}
{self.upcoming_home(games or [], updated_dt)}
<h2>Buscar entre las mejores ofertas</h2>
{self.offer_list(live[:60])}
{f'<p><a class="btn btn-primary" href="ofertas.html">Ver las {len(deals)} ofertas</a></p>' if len(live) > 60 else ''}
<h2>Tiendas</h2>
{stores_html}
<p><a href="tiendas.html">Ver detalles de las tiendas</a></p>
<h2>Guías recientes</h2>
{guides_html}
<h2>Preguntas frecuentes</h2>
{faq_short}""", jsonld=[org, website, self.item_list_ld(live)])

        self.layout("juegos-gratis.html", "Juegos gratis para PC hoy",
                    "Juegos gratuitos para PC disponibles ahora en tiendas oficiales como Epic Games Store, con la fecha en que termina cada promoción.",
                    f"<h1>Juegos gratis para PC</h1><p class=\"lead\">Juegos que puedes reclamar gratis por tiempo limitado en tiendas oficiales.</p>{updated_line}{notice}{self.offer_list(free)}<p>¿Primera vez? Lee <a href=\"guia-juegos-gratis-temporales.html\">cómo funcionan los juegos gratuitos temporales</a>.</p>",
                    crumbs=[("juegos-gratis.html", "Juegos gratis")], jsonld=[self.item_list_ld(free)])

        self.layout("ofertas.html", "Ofertas y descuentos de videojuegos",
                    "Descuentos de juegos de PC en Steam, GOG, Humble Store, Green Man Gaming, Fanatical y Epic, con precio original, precio actual y porcentaje de descuento.",
                    f"<h1>Ofertas y descuentos</h1><p class=\"lead\">Descuentos de {self.cfg['filtros_ofertas']['descuento_minimo']}% o más en juegos con buena crítica, en tiendas oficiales.</p>{updated_line}{notice}{self.offer_list(deals)}",
                    crumbs=[("ofertas.html", "Ofertas")], jsonld=[self.item_list_ld(deals)])

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

        by_day = {}
        for o in sorted(live, key=lambda o: o.get("createdAt") or "", reverse=True)[:40]:
            by_day.setdefault((o.get("createdAt") or "")[:10], []).append(o)
        news = "".join(f"<h2>{e(day)}</h2><ul>" + "".join(
            f"<li>{e(o['title'])} en {e(o['store'])}: {'gratis' if o.get('currentPrice') == 0 else str(o.get('discountPercentage') or '') + '% de descuento'}"
            f" · {ext_link(o['destinationUrl'], 'ver', o.get('affiliate'), cls='')}</li>" for o in items) + "</ul>"
            for day, items in by_day.items())
        self.layout("noticias.html", "Noticias de ofertas: lo nuevo detectado",
                    "Registro de las ofertas y juegos gratis nuevos que detectó Ofertas Gamer CO, ordenados por fecha de detección.",
                    f"<h1>Noticias de ofertas</h1><p class=\"lead\">Ofertas nuevas detectadas por nuestro sistema, de la más reciente a la más antigua.</p>{news or '<p>Todavía no hay novedades registradas.</p>'}",
                    crumbs=[("noticias.html", "Noticias de ofertas")])

        self.releases_page(games or [], updated_dt, updated_line)
        self.offer_pages(live, notice)
        self.game_pages(games or [], updated_dt)
        self.static_pages(status, updated)
        self.whatsapp_page(live, updated)
        self.feeds(live, updated_dt)
        self.sitemap(updated_dt)
        self.write("site.webmanifest", json.dumps({
            "name": self.cfg["nombre"], "short_name": "Ofertas Gamer", "lang": "es", "start_url": "./index.html",
            "display": "standalone", "background_color": "#0f1115", "theme_color": "#0f1115",
            "icons": [{"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, ensure_ascii=False, indent=1))
        self.write(".nojekyll", "")
        if self.cfg.get("indexnow_key"):  # IndexNow exige publicar la clave (no es secreta)
            self.write(f"{self.cfg['indexnow_key']}.txt", self.cfg["indexnow_key"])
        shutil.copy(ROOT / "config" / "_headers", self.out / "_headers")
        (self.out / "data").mkdir(exist_ok=True)
        public = [{k: o[k] for k in o if k != "telegramPublishedAt"} for o in live]
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
<li><strong><a href="https://www.exchangerate-api.com" target="_blank" rel="noopener noreferrer">ExchangeRate-API</a></strong>: tasa de cambio del día para el valor aproximado en pesos.</li>
</ul>
<p>No copiamos textos protegidos de las tiendas. Las imágenes de los juegos son las promocionales que publican las propias tiendas o fuentes. Si eres titular de derechos y quieres que retiremos una imagen, escríbenos desde <a href="contacto.html">Contacto</a>.</p></div>""",
          crumbs=[("fuentes.html", "Fuentes de información")])

        P("404.html", "Página no encontrada", "La página que buscas no existe en Ofertas Gamer CO.",
          '<h1>Página no encontrada</h1><p>La dirección no existe o cambió.</p><p><a class="btn btn-primary" href="index.html">Ir al inicio</a></p>',
          noindex=True)

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
