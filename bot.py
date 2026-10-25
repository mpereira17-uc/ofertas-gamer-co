"""Actualiza las ofertas, publica las nuevas en Telegram y genera el sitio en docs/.

Uso:
  python bot.py                    # ejecución normal (la usa GitHub Actions)
  python bot.py --no-send          # no publica en Telegram ni Discord
  python bot.py --fixtures tests/fixtures --no-send   # sin internet, con datos de prueba

Solo usa la librería estándar de Python.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from ogc import channels, promote, releases, sources
from ogc.model import compute_status, dedupe, iso, merge, now_utc, parse_iso, validate
from ogc.site import Site

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OFFERS_FILE = DATA / "offers.json"
PUBLISHED_FILE = DATA / "telegram_publicados.json"
SOCIAL_FILE = DATA / "redes_publicados.json"
RELEASES_FILE = DATA / "lanzamientos.json"
DOCS = ROOT / "docs"


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def fixture_fetch(folder):
    def fetch(url):
        if "featuredcategories" in url:
            name = "steam_featured.json"
        elif "appdetails" in url:
            name = "steam_appdetails.json"
        else:
            name = "epic.json" if "epicgames" in url else "cheapshark.json" if "cheapshark" in url else "rate.json"
        return json.loads((Path(folder) / name).read_text(encoding="utf-8"))
    return fetch


def run(args):
    cfg = load_json(ROOT / "config" / "site.json", {})
    stores = {s["id"]: s for s in load_json(ROOT / "config" / "stores.json", {})["stores"]}
    ads = load_json(ROOT / "config" / "ads.json", {"ads_enabled": False, "slots": []})
    previous = load_json(OFFERS_FILE, {}).get("offers", [])
    published_list = list(load_json(PUBLISHED_FILE, {"enviados": []})["enviados"])
    published = set(published_list)
    now = now_utc()
    if args.fixtures:
        sources.get_json = fixture_fetch(args.fixtures)

    rate, rate_date = sources.usd_to_cop()
    status = {"Tasa de cambio USD a COP": f"{rate:,.0f} ({rate_date})".replace(",", ".") if rate else "No disponible: no se muestran pesos"}
    fresh, failed = {}, set()
    for name, func in (("epic", sources.epic_free_games), ("cheapshark", sources.cheapshark_deals)):
        try:
            fresh[name] = func(stores, rate, now, cfg, fetch=sources.get_json)
            status[f"Fuente {name}"] = f"OK, {len(fresh[name])} registros"
        except Exception as exc:
            failed.add(name)
            status[f"Fuente {name}"] = f"Falló ({type(exc).__name__}); se conserva la última versión válida"
            print(f"La fuente {name} falló: {exc}", file=sys.stderr)

    # Validación: lo que no pasa no se publica.
    rejected = 0
    for name in fresh:
        valid = []
        for offer in fresh[name]:
            errors = validate(offer, stores)
            if errors:
                rejected += 1
                print(f"Rechazada '{offer.get('title')}': {', '.join(errors)}", file=sys.stderr)
            else:
                valid.append(offer)
        fresh[name] = valid
    status["Ofertas rechazadas por validación"] = str(rejected)

    offers = merge(previous, fresh, failed, now, cfg)
    for offer in offers:
        offer["status"] = compute_status(offer, now, cfg.get("dias_proximo_a_vencer", 2))
    offers = dedupe([o for o in offers if o["status"] != "Vencido"])
    if not offers and previous and failed:
        print("Todas las fuentes fallaron: se conserva la versión anterior sin cambios", file=sys.stderr)
        offers = [o for o in previous if o.get("status") != "Vencido"]
    status["Ofertas publicadas"] = str(len(offers))

    budget = cfg.get("maximo_mensajes_telegram_por_ejecucion", 6)
    sent_now = 0
    tg = cfg.get("filtros_telegram", {})

    def worth_sending(o):  # a Telegram solo van las mejores, para no llenar el canal
        return o.get("currentPrice") == 0 or (
            (o.get("discountPercentage") or 0) >= tg.get("descuento_minimo", 0) and
            (o.get("metacritic") or 0) >= tg.get("metacritic_minimo", 0))

    candidates = sorted(offers, key=lambda o: (o.get("currentPrice") != 0, -(o.get("metacritic") or 0),
                                               -(o.get("discountPercentage") or 0)))
    for offer in candidates:
        if offer["id"] in published or not worth_sending(offer):
            continue
        if args.no_send or budget <= 0:
            continue
        if channels.send_telegram(offer):
            published.add(offer["id"])
            published_list.append(offer["id"])
            offer["telegramPublishedAt"] = iso(now)
            budget -= 1
            sent_now += 1
    status["Publicadas en Telegram en esta ejecución"] = str(sent_now)

    offers.sort(key=lambda o: (o.get("currentPrice") != 0, -(o.get("discountPercentage") or 0)))
    DATA.mkdir(exist_ok=True)
    save_json(OFFERS_FILE, {"updatedAt": iso(now), "offers": offers})
    save_json(PUBLISHED_FILE, {"enviados": published_list[-3000:]})  # en orden de envío: se olvidan los más viejos
    previous_releases = load_json(RELEASES_FILE, {}).get("games", [])
    games, status["Fuente lanzamientos (Steam)"] = releases.update(previous_releases, now, sources.get_json)
    save_json(RELEASES_FILE, {"updatedAt": iso(now), "games": games})

    site = Site(cfg, stores, ads, DOCS)
    site.assign_pages(offers, games)
    base = cfg["url_web"].rstrip("/") + "/"
    social = load_json(SOCIAL_FILE, {"bluesky": [], "mastodon": [], "discord": []})
    posted = {"bluesky": 0, "mastodon": 0, "discord": 0}
    if not args.no_send:
        for offer in candidates:
            if not worth_sending(offer) or offer["id"] not in site.detail:
                continue
            link = base + site.detail[offer["id"]]
            for net, send in (("bluesky", promote.send_bluesky), ("mastodon", promote.send_mastodon),
                              ("discord", promote.send_discord)):
                if offer["id"] in social.setdefault(net, []) or posted[net] >= cfg.get("maximo_posts_redes_por_ejecucion", 3):
                    continue
                if send(offer, link):
                    social[net].append(offer["id"])
                    posted[net] += 1
        social = {k: v[-3000:] for k, v in social.items()}
        save_json(SOCIAL_FILE, social)
    ready = {"bluesky": bool(os.environ.get("BLUESKY_HANDLE", "").strip() and os.environ.get("BLUESKY_APP_PASSWORD", "").strip()),
             "mastodon": bool(os.environ.get("MASTODON_URL") and os.environ.get("MASTODON_TOKEN")),
             "discord": (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip().startswith(promote.DISCORD_PREFIXES)}
    for net, label in (("bluesky", "Bluesky"), ("mastodon", "Mastodon"), ("discord", "Discord")):
        status[f"{label} en esta ejecución"] = f"{posted[net]} publicadas" if ready[net] else "no configurado"
        print(f"{label}: {status[f'{label} en esta ejecución']}")

    site.build(offers, status, now, games)

    if not args.no_send and not args.fixtures and cfg.get("indexnow_key"):
        new_ids = {o["id"] for o in offers if (o.get("createdAt") or "") >= iso(now)[:13]} | \
            {g["id"] for g in games if g["id"] not in {p.get("id") for p in previous_releases}}
        urls = [base, base + "ofertas.html", base + "juegos-gratis.html", base + "lanzamientos.html"] + \
            [base + site.detail[i] for i in sorted(new_ids) if i in site.detail]
        ok = promote.indexnow(base, cfg["indexnow_key"], urls)
        print(f"IndexNow: {len(urls)} URL {'aceptadas' if ok else 'no enviadas'}")
    print(f"{len(offers)} ofertas; {rejected} rechazadas; {sent_now} enviadas a Telegram; fuentes con error: {sorted(failed) or 'ninguna'}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-send", action="store_true", help="no publicar en Telegram ni Discord")
    parser.add_argument("--fixtures", help="carpeta con epic.json, cheapshark.json y rate.json")
    sys.exit(run(parser.parse_args()))
