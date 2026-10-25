"""Promoción automática por canales oficiales y gratuitos.

- IndexNow: avisa a Bing, Yandex y otros buscadores de las páginas nuevas (no necesita cuenta).
- Bluesky: publica con la API oficial (AT Protocol) si existen BLUESKY_HANDLE y BLUESKY_APP_PASSWORD.
- Mastodon: publica con la API oficial si existen MASTODON_URL y MASTODON_TOKEN.
- Tumblr: publica con la API oficial (ver ogc/tumblr.py) si existen TUMBLR_BLOG y sus cuatro secretos.

Sin los secretos no se publica nada. Nunca se imprimen tokens ni contraseñas.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import tumblr
from .channels import price_line

INDEXNOW_URL = "https://api.indexnow.org/indexnow"
BSKY = "https://bsky.social/xrpc/"


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


def bluesky_thumb(image, jwt):
    """Sube la portada del juego para que la tarjeta de Bluesky la muestre. Sin imagen, devuelve None."""
    if not (image or "").startswith("https://"):
        return None
    try:
        req = urllib.request.Request(image, headers={"User-Agent": "Mozilla/5.0 OfertasGamerCO"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            kind = resp.headers.get_content_type()
            data = resp.read(1_000_001)
        if not kind.startswith("image/") or len(data) > 976_000:
            return None
        req = urllib.request.Request(BSKY + "com.atproto.repo.uploadBlob", data=data, method="POST",
                                     headers={"Content-Type": kind, "Authorization": f"Bearer {jwt}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["blob"]
    except Exception as exc:
        print(f"Bluesky: no se pudo subir la imagen ({type(exc).__name__})", file=sys.stderr)
        return None


def bluesky_post(text, link, title, description, image=None):
    """Publica un texto con tarjeta de enlace (y portada si hay). Devuelve True si salió."""
    handle = (os.environ.get("BLUESKY_HANDLE") or "").strip().lstrip("@")
    password = (os.environ.get("BLUESKY_APP_PASSWORD") or "").strip()
    if not handle or not password:
        return False
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
                      "external": {"uri": link, "title": title[:300], "description": description[:300]}},
        }
        thumb = bluesky_thumb(image, session["accessJwt"])
        if thumb:
            record["embed"]["external"]["thumb"] = thumb
        _post(BSKY + "com.atproto.repo.createRecord",
              {"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
              headers={"Authorization": f"Bearer {session['accessJwt']}"})
        return True
    except Exception as exc:
        print(f"Bluesky falló con '{title}': {type(exc).__name__}", file=sys.stderr)
        return False


def send_bluesky(offer, page_url):
    text, link = post_text(offer, page_url)
    return bluesky_post(text, link, offer["title"], price_line(offer), offer.get("image"))


def send_tumblr(offer, page_url):
    if tumblr.LAST_ERROR:  # si Tumblr ya rechazó una, no insistir en esta ejecución
        return False
    text, link = post_text(offer, page_url)
    text = text.split("#")[0]  # en Tumblr las etiquetas van aparte
    return tumblr.post(text, link, offer["title"], price_line(offer), offer.get("image"))


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

