"""Busca juegos gratis y ofertas, los publica en Telegram y genera la página web.

Corre solo en GitHub Actions (ver .github/workflows/bot.yml). No necesita dependencias
fuera de la librería estándar de Python.
"""

import html
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
STATE_FILE = ROOT / "state.json"
CONFIG_FILE = ROOT / "config.json"
DOCS = ROOT / "docs"

STORES = {"1": "Steam", "3": "GreenManGaming", "7": "GOG", "11": "Humble Store", "25": "Epic Games"}
USER_AGENT = "ofertas-gamer-co/1.0"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def usd_to_cop():
    try:
        return float(get_json("https://open.er-api.com/v6/latest/USD")["rates"]["COP"])
    except Exception as exc:  # la tasa no es crítica: usamos una aproximada
        print(f"No se pudo leer la tasa de cambio ({exc}); uso 4000", file=sys.stderr)
        return 4000.0


def fmt_cop(usd, rate):
    return "$" + f"{round(usd * rate / 100) * 100:,.0f}".replace(",", ".") + " COP"


def epic_free_games():
    url = ("https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
           "?locale=es-ES&country=CO&allowCountries=CO")
    games = []
    for el in get_json(url)["data"]["Catalog"]["searchStore"]["elements"]:
        promos = (el.get("promotions") or {}).get("promotionalOffers") or []
        offers = [o for p in promos for o in p.get("promotionalOffers", [])]
        free_now = [o for o in offers if o["discountSetting"]["discountPercentage"] == 0]
        if not free_now or el["price"]["totalPrice"]["discountPrice"] != 0:
            continue
        slug = el.get("productSlug") or ""
        mappings = (el.get("catalogNs") or {}).get("mappings") or el.get("offerMappings") or []
        if mappings:
            slug = mappings[0].get("pageSlug") or slug
        image = next((i["url"] for i in el.get("keyImages", [])
                      if i["type"] in ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail")), "")
        games.append({
            "id": f"epic-{el['id']}-{free_now[0]['endDate'][:10]}",
            "kind": "gratis",
            "title": el["title"],
            "store": "Epic Games",
            "url": f"https://store.epicgames.com/es-ES/p/{slug.split('/')[0]}" if slug else "https://store.epicgames.com/es-ES/free-games",
            "image": image,
            "normal_usd": el["price"]["totalPrice"]["originalPrice"] / 100,
            "sale_usd": 0.0,
            "savings": 100,
            "ends": free_now[0]["endDate"],
        })
    return games


def cheapshark_deals(cfg):
    params = {
        "storeID": ",".join(STORES),
        "sortBy": "Deal Rating",
        "pageSize": 60,
        "upperPrice": cfg["precio_maximo_usd"],
        "metacritic": cfg["metacritic_minimo"],
        "onSale": 1,
    }
    deals = []
    for d in get_json("https://www.cheapshark.com/api/1.0/deals?" + urllib.parse.urlencode(params)):
        savings = float(d["savings"])
        if savings < cfg["descuento_minimo"]:
            continue
        deals.append({
            "id": f"cs-{d['gameID']}-{d['storeID']}-{d['salePrice']}",
            "kind": "gratis" if float(d["salePrice"]) == 0 else "oferta",
            "title": d["title"],
            "store": STORES.get(d["storeID"], "Tienda"),
            "url": affiliate_url(d, cfg),
            "image": d.get("thumb", ""),
            "normal_usd": float(d["normalPrice"]),
            "sale_usd": float(d["salePrice"]),
            "savings": round(savings),
            "metacritic": d.get("metacriticScore"),
            "ends": None,
        })
    return deals


def affiliate_url(deal, cfg):
    # Mientras no tengas tus propios enlaces de afiliado, enlazamos por CheapShark como piden sus términos.
    template = cfg.get("afiliados", {}).get(deal["storeID"])
    if template and deal.get("steamAppID"):
        return template.format(steamAppID=deal["steamAppID"], title=urllib.parse.quote(deal["title"]))
    return f"https://www.cheapshark.com/redirect?dealID={deal['dealID']}"


def caption(item, rate, cfg):
    title = html.escape(item["title"])
    if item["sale_usd"] == 0:
        head = f"🎁 <b>GRATIS</b> · {title}"
        price = f"Normalmente {fmt_cop(item['normal_usd'], rate)}" if item["normal_usd"] else ""
    else:
        head = f"🔥 <b>-{item['savings']}%</b> · {title}"
        price = (f"<b>{fmt_cop(item['sale_usd'], rate)}</b> (antes {fmt_cop(item['normal_usd'], rate)})"
                 f" · US${item['sale_usd']:.2f}")
    lines = [head, f"🛒 {item['store']}"]
    if price:
        lines.append(price)
    if item.get("metacritic") and item["metacritic"] != "0":
        lines.append(f"⭐ Metacritic {item['metacritic']}")
    if item.get("ends"):
        lines.append(f"⏰ Hasta el {item['ends'][:10]}")
    lines.append(f'👉 <a href="{html.escape(item["url"])}">Ver oferta</a>')
    if cfg.get("pie_de_mensaje"):
        lines.append(cfg["pie_de_mensaje"])
    return "\n".join(lines)


def send_telegram(item, rate, cfg):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    text = caption(item, rate, cfg)
    method, payload = ("sendPhoto", {"chat_id": chat, "photo": item["image"], "caption": text, "parse_mode": "HTML"}) \
        if item["image"] else ("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML"})
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}",
                                 data=urllib.parse.urlencode(payload).encode(), method="POST")
    try:
        urllib.request.urlopen(req, timeout=30).read()
        return True
    except Exception as exc:
        print(f"Telegram falló con '{item['title']}': {exc}", file=sys.stderr)
        return False


def build_site(items, rate, cfg):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cards = []
    for it in items:
        if it["sale_usd"] == 0:
            badge, price = "GRATIS", (f"<s>{fmt_cop(it['normal_usd'], rate)}</s>" if it["normal_usd"] else "")
        else:
            badge = f"-{it['savings']}%"
            price = f"<b>{fmt_cop(it['sale_usd'], rate)}</b> <s>{fmt_cop(it['normal_usd'], rate)}</s>"
        ends = f"<small>Hasta el {it['ends'][:10]}</small>" if it.get("ends") else ""
        img = f'<img src="{html.escape(it["image"])}" alt="" loading="lazy">' if it["image"] else ""
        cards.append(f"""<a class="card" href="{html.escape(it['url'])}" rel="nofollow sponsored noopener" target="_blank">
{img}<span class="badge">{badge}</span><h2>{html.escape(it['title'])}</h2>
<p>{html.escape(it['store'])}</p><p>{price}</p>{ends}</a>""")
    telegram = cfg.get("enlace_canal_telegram")
    join = f'<a class="join" href="{html.escape(telegram)}">📲 Recibe las ofertas en Telegram</a>' if telegram else ""
    page = (ROOT / "plantilla.html").read_text(encoding="utf-8")
    page = (page.replace("{{CARDS}}", "\n".join(cards) or "<p>No hay ofertas ahora mismo. Vuelve pronto.</p>")
                .replace("{{UPDATED}}", now)
                .replace("{{RATE}}", f"{rate:,.0f}".replace(",", "."))
                .replace("{{JOIN}}", join))
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(page, encoding="utf-8")


def main():
    cfg = load_json(CONFIG_FILE, {})
    state = load_json(STATE_FILE, {"enviados": []})
    rate = usd_to_cop()

    items = []
    for source in (epic_free_games, lambda: cheapshark_deals(cfg)):
        try:
            items += source()
        except Exception as exc:
            print(f"Una fuente falló: {exc}", file=sys.stderr)
    # Los gratis primero, luego los mayores descuentos; sin repetir el mismo juego.
    items.sort(key=lambda i: (i["sale_usd"] != 0, -i["savings"]))
    seen_titles, unique = set(), []
    for it in items:
        if it["title"].lower() not in seen_titles:
            seen_titles.add(it["title"].lower())
            unique.append(it)

    sent = set(state["enviados"])
    budget = cfg.get("maximo_mensajes_por_ejecucion", 6)
    for it in unique:
        if budget <= 0:
            break
        if it["id"] not in sent and send_telegram(it, rate, cfg):
            sent.add(it["id"])
            budget -= 1

    build_site(unique[: cfg.get("ofertas_en_la_web", 48)], rate, cfg)
    STATE_FILE.write_text(json.dumps({"enviados": sorted(sent)[-2000:]}, indent=1), encoding="utf-8")
    print(f"{len(unique)} ofertas, tasa {rate:.0f} COP/USD")


if __name__ == "__main__":
    main()
