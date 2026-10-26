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
import shutil
import sys
from datetime import timedelta
from pathlib import Path

from ogc import alerts, channels, codes, community, discord, health, images, promote, releases, sources, tumblr, weekly, wikidata
from ogc.channels import price_line
from ogc.releases import date_label
from ogc.model import compute_status, dedupe, iso, merge, now_utc, parse_iso, validate
from ogc import history as price_log
from ogc.site import Site

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OFFERS_FILE = DATA / "offers.json"
PUBLISHED_FILE = DATA / "telegram_publicados.json"
SOCIAL_FILE = DATA / "redes_publicados.json"
RELEASES_FILE = DATA / "lanzamientos.json"
F2P_FILE = DATA / "gratis_para_siempre.json"
WEEKLY_FILE = DATA / "resumenes.json"
ALERTS_FILE = DATA / "alertas.enc"  # cifrado: lleva números de chat de Telegram
BOT_FILE = DATA / "telegram_bot.json"
HISTORY_FILE = DATA / "historial_precios.json"
EPIC_NEXT_FILE = DATA / "epic_proximos.json"
POLL_FILE = DATA / "encuesta.json"
HEALTH_FILE = DATA / "salud.json"
IMG_DIR = DATA / "img"
EPIC_ARCHIVE_FILE = DATA / "epic_regalados.json"
DAILY_FILE = DATA / "oferta_del_dia.json"
CODES_FILE = DATA / "codigos.json"
DOCS = ROOT / "docs"


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def save_history(path, hist):
    """Un juego por línea: el archivo crece poco y los cambios se leen fácil en GitHub."""
    lines = [f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False, separators=(',', ':'))}" for k, v in sorted(hist.items())]
    Path(path).write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


def fixture_fetch(folder):
    def fetch(url):
        if "featuredcategories" in url:
            name = "steam_featured.json"
        elif "appdetails" in url:
            name = "steam_appdetails.json"
        elif "itunes.apple.com" in url:
            name = "codes_itunes.json"
        elif "seria.moe" in url or "ennead.cc" in url:
            name = "codes_seria.json" if "seria.moe" in url else "codes_ennead.json"
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

    # Última oportunidad: un recordatorio, una sola vez, de lo bueno que termina en menos de 24 horas
    last_call = load_json(SOCIAL_FILE, {}).get("ultima", [])
    reminded = 0
    for offer in candidates:
        ends = parse_iso(offer.get("expiresAt"))
        big = offer.get("currentPrice") == 0 or (offer.get("discountPercentage") or 0) >= 75
        if (args.no_send or reminded >= 2 or not big or not ends or offer["id"] in last_call or offer["id"] not in published
                or not timedelta(hours=1) < ends - now <= timedelta(hours=24)):
            continue
        if channels.send_telegram(offer, prefix="⏰ <b>ÚLTIMA OPORTUNIDAD</b> · termina en menos de 24 horas\n"):
            last_call.append(offer["id"])
            reminded += 1
    status["Recordatorios de última oportunidad"] = str(reminded)

    offers.sort(key=lambda o: (o.get("currentPrice") != 0, -(o.get("discountPercentage") or 0)))
    DATA.mkdir(exist_ok=True)
    save_json(OFFERS_FILE, {"updatedAt": iso(now), "offers": offers})
    save_json(PUBLISHED_FILE, {"enviados": published_list[-3000:]})  # en orden de envío: se olvidan los más viejos
    previous_releases = load_json(RELEASES_FILE, {}).get("games", [])
    games, status["Fuente lanzamientos (Steam)"] = releases.update(previous_releases, now, sources.get_json)
    games, status["Fuente juegos grandes y de consola (Wikidata)"] = wikidata.add_consoles(games, previous_releases, now, sources.get_json)
    games = releases.mark_date_changes(games, previous_releases, now)
    save_json(RELEASES_FILE, {"updatedAt": iso(now), "games": games})
    try:
        epic_next = sources.epic_upcoming(sources.get_json)
        save_json(EPIC_NEXT_FILE, {"updatedAt": iso(now), "games": epic_next})
        status["Próximos gratis de Epic"] = f"OK, {len(epic_next)} anunciados"
    except Exception as exc:
        epic_next = load_json(EPIC_NEXT_FILE, {}).get("games", [])
        status["Próximos gratis de Epic"] = f"Falló ({type(exc).__name__}); se usa la lista anterior"
    epic_archive = load_json(EPIC_ARCHIVE_FILE, {})
    for o in offers:
        if o["storeId"] == "epic" and o.get("currentPrice") == 0:
            epic_archive[o["id"]] = {k: o.get(k) for k in ("title", "image", "officialUrl", "startsAt", "expiresAt", "originalPrice", "currency")}
    save_json(EPIC_ARCHIVE_FILE, epic_archive)
    f2p, status["Fuente gratis para siempre (Steam)"] = releases.free_to_play(sources.get_json, load_json(F2P_FILE, {}).get("games", []))
    save_json(F2P_FILE, {"updatedAt": iso(now), "games": f2p})

    price_history = price_log.record(load_json(HISTORY_FILE, {}), offers, now)
    save_history(HISTORY_FILE, price_history)
    status["Historial de precios"] = f"{len(price_history)} juegos seguidos"

    site = Site(cfg, stores, ads, DOCS)
    site.history = price_history
    site.daily = load_json(DAILY_FILE, {})
    site.assign_pages(offers, games)
    base = cfg["url_web"].rstrip("/") + "/"
    social = load_json(SOCIAL_FILE, {"bluesky": [], "mastodon": [], "discord": [], "tumblr": []})
    social["ultima"] = last_call
    posted = {"bluesky": 0, "mastodon": 0, "discord": 0, "tumblr": 0}
    if not args.no_send:
        for offer in candidates:
            if not worth_sending(offer) or offer["id"] not in site.detail:
                continue
            link = base + site.detail[offer["id"]]
            for net, send in (("bluesky", promote.send_bluesky), ("mastodon", promote.send_mastodon),
                              ("tumblr", promote.send_tumblr)):
                if offer["id"] in social.setdefault(net, []) or posted[net] >= cfg.get("maximo_posts_redes_por_ejecucion", 3):
                    continue
                if net == "tumblr" and not tumblr.can_post(social.setdefault("tumblr_horas", []), now, cfg.get("tumblr", {})):
                    continue
                if send(offer, link):
                    social[net].append(offer["id"])
                    posted[net] += 1
                    if net == "tumblr":
                        social["tumblr_horas"].append(iso(now))
        dc = discord.Discord(guild=str(cfg.get("discord_servidor", "")))
        if dc.ready:
            counts = discord.publish(dc, candidates, games, lambda x: base + site.detail[x["id"]] if x["id"] in site.detail else "",
                                     social, cfg.get("maximo_posts_redes_por_ejecucion", 3), price_line, date_label, worth_sending)
            posted["discord"] = sum(counts.values())
        social = {k: v[-3000:] for k, v in social.items()}
        save_json(SOCIAL_FILE, social)
    ready = {"bluesky": bool(os.environ.get("BLUESKY_HANDLE", "").strip() and os.environ.get("BLUESKY_APP_PASSWORD", "").strip()),
             "mastodon": bool(os.environ.get("MASTODON_URL") and os.environ.get("MASTODON_TOKEN")),
             "discord": discord.Discord(guild=str(cfg.get("discord_servidor", ""))).ready, "tumblr": tumblr.ready()}
    for net, label in (("bluesky", "Bluesky"), ("mastodon", "Mastodon"), ("discord", "Discord"), ("tumblr", "Tumblr")):
        status[f"{label} en esta ejecución"] = f"{posted[net]} publicadas" if ready[net] else "no configurado"
        if net == "tumblr" and ready[net] and tumblr.LAST_ERROR:
            status[f"{label} en esta ejecución"] += f" (último error: {tumblr.LAST_ERROR})"
        if net == "tumblr" and not ready[net] and len(tumblr.missing()) < 5:
            status[f"{label} en esta ejecución"] += " (falta " + ", ".join(tumblr.missing()) + ")"
        print(f"{label}: {status[f'{label} en esta ejecución']}")

    history = load_json(WEEKLY_FILE, {"semanas": []})["semanas"]
    if weekly.is_due(now, history) and not args.no_send:
        snap = weekly.snapshot(now, *weekly.pick(offers, games, now))
        done = weekly.publish(snap, base + "resumen-semanal.html", discord.Discord(guild=str(cfg.get("discord_servidor", ""))),
                              promote.bluesky_post, cfg.get("enlace_kofi"))
        history = [snap] + history[: weekly.KEEP - 1]
        save_json(WEEKLY_FILE, {"semanas": history})
        polls = load_json(POLL_FILE, {})
        poll = community.send_poll(snap, discord.Discord(guild=str(cfg.get("discord_servidor", ""))))
        save_json(POLL_FILE, {"current": poll, "previous": ([polls["current"]] if polls.get("current") else []) + polls.get("previous", [])[:10]})
        status["Resumen semanal"] = f"Publicado esta ejecución en {', '.join(done) or 'ninguna red'}"
    else:
        status["Resumen semanal"] = f"Último: {history[0]['label']}" if history else "Sale el viernes"
    print(f"Resumen semanal: {status['Resumen semanal']}")
    bot_info = load_json(BOT_FILE, {})
    if not args.no_send:
        name = alerts.bot_username()
        if name and name != bot_info.get("username"):
            bot_info = {"username": name}
            save_json(BOT_FILE, bot_info)
        link_for = lambda x: base + site.detail[x["id"]] if x["id"] in site.detail else ""
        polls = load_json(POLL_FILE, {})
        on_poll = (lambda p: community.apply_poll_update(polls["current"], p)) if polls.get("current") else None
        status["Alertas de Telegram"] = alerts.run(str(ALERTS_FILE), offers, games, link_for, now, on_poll=on_poll)
        if polls:
            save_json(POLL_FILE, polls)
        print(f"Alertas: {status['Alertas de Telegram']}")
    code_state, new_codes, status["Códigos de canje (HoYoverse)"] = codes.update(load_json(CODES_FILE, {}), now, sources.get_json)
    if new_codes and not args.no_send:
        sent_codes = codes.announce(code_state, new_codes, base, discord.Discord(guild=str(cfg.get("discord_servidor", ""))))
        status["Códigos de canje (HoYoverse)"] += f"; {sent_codes} nuevos anunciados"
    save_json(CODES_FILE, code_state)
    print(f"Códigos: {status['Códigos de canje (HoYoverse)']}")
    health_state = load_json(HEALTH_FILE, {})
    if not args.no_send and not args.fixtures:
        checks = {"Epic": "epic" not in failed, "CheapShark": "cheapshark" not in failed}
        for key, label in (("Fuente lanzamientos (Steam)", "Steam (lanzamientos)"), ("Fuente juegos grandes y de consola (Wikidata)", "Wikidata"),
                           ("Fuente gratis para siempre (Steam)", "Steam (gratis para siempre)")):
            checks[label] = str(status.get(key, "")).startswith("OK")
        checks["Códigos (HoYoverse)"] = any(g.get("lastOk") == iso(now) for g in code_state["games"].values())
        health_state = health.track_sources(health_state, checks, now)
        health_state = health.check_links(health_state, offers, now, health.head_status)
        health_state = health.monthly_report(health_state, now, health.month_stats(
            now, price_history, epic_archive, history, status.get("Alertas de Telegram"), offers))
        save_json(HEALTH_FILE, health_state)
    if "linksChecked" in health_state:
        status["Enlaces revisados hoy"] = f"{health_state['linksChecked']} revisados, {len(health_state.get('linksBroken', []))} rotos"
    down = [n for n, s in health_state.get("sources", {}).items() if s.get("fails")]
    status["Fuentes con fallas seguidas"] = ", ".join(f"{n} ({health_state['sources'][n]['fails']})" for n in down) or "ninguna"
    site.f2p, site.weekly_history, site.bot = f2p, history, bot_info.get("username", "")
    site.epic_next, site.epic_archive = epic_next, epic_archive
    site.poll = load_json(POLL_FILE, {})
    site.codes = code_state
    site.dotd_image = (IMG_DIR / "oferta-del-dia.jpg").exists()
    site.build(offers, status, now, games)
    daily = getattr(site, "daily", None) or {}
    dotd = next((o for o in offers if o["id"] == daily.get("id")), None)
    if dotd and daily.get("imageFor") != dotd["id"] and images.available() and not args.fixtures:
        try:
            cover = sources.get_bytes(dotd["image"]) if dotd.get("image") else None
        except Exception as exc:
            print(f"Imagen del día: no se pudo bajar la portada ({type(exc).__name__})", file=sys.stderr)
            cover = None
        jpg = images.offer_card(dotd, cover, site.pesos)
        if jpg:
            IMG_DIR.mkdir(exist_ok=True)
            (IMG_DIR / "oferta-del-dia.jpg").write_bytes(jpg)
            daily["imageFor"] = dotd["id"]
    if IMG_DIR.exists():
        shutil.copytree(IMG_DIR, DOCS / "img", dirs_exist_ok=True)
    if dotd and community.daily_due(now, daily) and not args.no_send:
        today_games = [g for g in games if g.get("precision") == "day" and g.get("date") == now.astimezone(channels.CO_TZ).strftime("%Y-%m-%d")]
        free_now = [o for o in offers if o.get("currentPrice") == 0]
        jpg = (IMG_DIR / "oferta-del-dia.jpg").read_bytes() if daily.get("imageFor") == dotd["id"] else None
        text = community.daily_text(dotd, free_now, sorted(today_games, key=lambda g: g.get("rank") or 9999), base + "oferta-del-dia.html")
        if community.send_daily(text, jpg, dotd.get("image") or ""):
            daily["sentDate"] = now.astimezone(channels.CO_TZ).strftime("%Y-%m-%d")
            status["Resumen diario"] = "Enviado hoy"
    if daily:
        save_json(DAILY_FILE, daily)

    if not args.no_send and not args.fixtures and cfg.get("indexnow_key"):
        new_ids = {o["id"] for o in offers if (o.get("createdAt") or "") >= iso(now)[:13]} | \
            {g["id"] for g in games if g["id"] not in {p.get("id") for p in previous_releases}}
        urls = [base, base + "ofertas.html", base + "juegos-gratis.html", base + "lanzamientos.html"] + \
            [base + site.detail[i] for i in sorted(new_ids) if i in site.detail]
        urls += [base + "codigos.html"] + [base + codes.GAMES[gid]["page"] for gid in sorted({gid for gid, _ in new_codes})]
        ok = promote.indexnow(base, cfg["indexnow_key"], urls)
        print(f"IndexNow: {len(urls)} URL {'aceptadas' if ok else 'no enviadas'}")
    print(f"{len(offers)} ofertas; {rejected} rechazadas; {sent_now} enviadas a Telegram; fuentes con error: {sorted(failed) or 'ninguna'}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-send", action="store_true", help="no publicar en Telegram ni Discord")
    parser.add_argument("--fixtures", help="carpeta con epic.json, cheapshark.json y rate.json")
    sys.exit(run(parser.parse_args()))
