"""Promoción automática por canales oficiales y gratuitos.

- IndexNow: avisa a Bing, Yandex y otros buscadores de las páginas nuevas (no necesita cuenta).
- Bluesky: publica con la API oficial (AT Protocol) si existen BLUESKY_HANDLE y BLUESKY_APP_PASSWORD.
- Mastodon: publica con la API oficial si existen MASTODON_URL y MASTODON_TOKEN.
- Discord: publica con un webhook oficial del canal si existe DISCORD_WEBHOOK_URL.

Sin los secretos no se publica nada. Nunca se imprimen tokens ni contraseñas.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .channels import price_line

INDEXNOW_URL = "https://api.indexnow.org/indexnow"
BSKY = "https://bsky.social/xrpc/"
DISCORD_PREFIXES = ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")


def _post(url, payload, headers=None, form=False):
    data = urllib.parse.urlencode(payload).encode() if form else json.dumps(payload).encode()
    hdrs = {"Content-Type": "application/x-www-form-urlencoded" if form else "application/json; charset=utf-8"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


def indexnow(base, key, urls):
    """Avisa a los buscadores de las URL nuevas o cambiadas. Devuelve True si se aceptó."""
    if not key or not urls:
        return False
    host = urllib.parse.urlparse(base).hostname
    try:
        _post(INDEXNOW_URL, {"host": host, "key": key, "keyLocation": f"{base}{key}.txt", "urlList": urls[:10000]})
        return True
    except Exception as exc:
        print(f"IndexNow falló: {type(exc).__name__}", file=sys.stderr)
        return False


def post_text(offer, page_url):
    head = "🎁 GRATIS" if offer.get("currentPrice") == 0 else f"🔥 -{offer.get('discountPercentage') or 0}%"
    text = f"{head} · {offer['title']} en {offer['store']}\n{price_line(offer)}\n"
    if offer.get("affiliate"):
        text += "Enlace de afiliado.\n"
    text += "#videojuegos #ofertas #gaming\n"
    return text, page_url


def send_bluesky(offer, page_url):
    handle = (os.environ.get("BLUESKY_HANDLE") or "").strip().lstrip("@")
    password = (os.environ.get("BLUESKY_APP_PASSWORD") or "").strip()
    if not handle or not password:
        return False
    text, link = post_text(offer, page_url)
    text = text[: 300 - len(link) - 1] + link
    start = len(text[: text.rindex(link)].encode("utf-8"))
    try:
        session = _post(BSKY + "com.atproto.server.createSession", {"identifier": handle, "password": password})
        record = {
            "$type": "app.bsky.feed.post", "text": text, "langs": ["es"],
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "facets": [{"index": {"byteStart": start, "byteEnd": start + len(link.encode("utf-8"))},
                        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}]}],
            "embed": {"$type": "app.bsky.embed.external",
                      "external": {"uri": link, "title": offer["title"], "description": price_line(offer)}},
        }
        _post(BSKY + "com.atproto.repo.createRecord",
              {"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
              headers={"Authorization": f"Bearer {session['accessJwt']}"})
        return True
    except Exception as exc:
        print(f"Bluesky falló con '{offer['title']}': {type(exc).__name__}", file=sys.stderr)
        return False


def send_mastodon(offer, page_url):
    base, token = os.environ.get("MASTODON_URL", "").rstrip("/"), os.environ.get("MASTODON_TOKEN")
    if not base.startswith("https://") or not token:
        return False
    text, link = post_text(offer, page_url)
    try:
        _post(base + "/api/v1/statuses", {"status": (text + link)[:500], "language": "es", "visibility": "public"},
              headers={"Authorization": f"Bearer {token}"}, form=True)
        return True
    except Exception as exc:
        print(f"Mastodon falló con '{offer['title']}': {type(exc).__name__}", file=sys.stderr)
        return False


def send_discord(offer, page_url):
    hook = (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()
    if not hook.startswith(DISCORD_PREFIXES):
        return False
    text, link = post_text(offer, page_url)
    embed = {"title": offer["title"][:250], "url": link, "description": text.strip()[:2000], "color": 0x22C55E}
    if (offer.get("image") or "").startswith("https://"):
        embed["image"] = {"url": offer["image"]}
    try:
        _post(hook, {"username": "Ofertas Gamer CO", "embeds": [embed], "allowed_mentions": {"parse": []}},
              headers={"User-Agent": "OfertasGamerCO (https://ofertas-gamer-co.pages.dev, 1.0)"})
        return True
    except Exception as exc:
        print(f"Discord falló con '{offer['title']}': {type(exc).__name__}", file=sys.stderr)
        return False
