"""Tumblr: publica con la API oficial (v2, formato NPF) firmada con OAuth 1.0a.

Necesita la variable TUMBLR_BLOG (nombre del blog) y cuatro secretos: TUMBLR_CONSUMER_KEY,
TUMBLR_CONSUMER_SECRET, TUMBLR_TOKEN y TUMBLR_TOKEN_SECRET. Sin ellos no se publica nada.
Nunca se imprimen las claves.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.tumblr.com/v2/blog/{blog}/posts"
LAST_ERROR = ""
KEYS = ("TUMBLR_CONSUMER_KEY", "TUMBLR_CONSUMER_SECRET", "TUMBLR_TOKEN", "TUMBLR_TOKEN_SECRET")


def _q(s):
    return urllib.parse.quote(str(s), safe="~")


def blog(env=os.environ):
    name = (env.get("TUMBLR_BLOG") or "").strip().lstrip("@")
    if name.startswith("http"):
        name = urllib.parse.urlparse(name).hostname or ""
    return name if "." in name else (name + ".tumblr.com" if name else "")


def ready(env=os.environ):
    return bool(blog(env)) and all((env.get(k) or "").strip() for k in KEYS)


def missing(env=os.environ):
    """Nombres (nunca valores) de lo que falta configurar."""
    names = [] if (env.get("TUMBLR_BLOG") or "").strip() else ["TUMBLR_BLOG (variable)"]
    return names + [k for k in KEYS if not (env.get(k) or "").strip()]


def oauth_header(method, url, ck, cs, tk, ts, nonce=None, stamp=None):
    """Cabecera OAuth 1.0a (HMAC-SHA1). El cuerpo JSON no entra en la firma."""
    params = {"oauth_consumer_key": ck, "oauth_nonce": nonce or secrets.token_hex(16),
              "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(stamp or int(time.time())),
              "oauth_token": tk, "oauth_version": "1.0"}
    norm = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(params.items()))
    base = "&".join((method.upper(), _q(url), _q(norm)))
    key = f"{_q(cs)}&{_q(ts)}".encode()
    params["oauth_signature"] = base64.b64encode(hmac.new(key, base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(params.items()))


def npf(text, link, title, description, image=None, tags=()):
    content = []
    if (image or "").startswith("https://"):
        content.append({"type": "image", "media": [{"url": image}], "alt_text": title[:200]})
    content.append({"type": "text", "text": text.strip()})
    content.append({"type": "link", "url": link, "title": title[:200], "description": description[:300]})
    return {"content": content, "tags": ",".join(tags), "state": "published"}


def post(text, link, title, description, image=None, tags=("videojuegos", "ofertas", "gaming", "juegos gratis", "colombia"),
         env=os.environ):
    if not ready(env):
        return False
    url = API.format(blog=blog(env))
    ck, cs, tk, ts = (env[k].strip() for k in KEYS)
    req = urllib.request.Request(url, method="POST", data=json.dumps(npf(text, link, title, description, image, tags)).encode(),
                                 headers={"Authorization": oauth_header("POST", url, ck, cs, tk, ts),
                                          "Content-Type": "application/json", "User-Agent": "ofertas-gamer-co-bot"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:  # nunca imprimir claves
        global LAST_ERROR
        code = getattr(exc, "code", "")
        detail = ""
        try:  # el mensaje de error de Tumblr no lleva claves
            body = json.loads(exc.read())
            detail = "; ".join(str(e.get("detail") or e.get("title") or "") for e in body.get("errors", []))[:200] \
                or str(body.get("meta", {}).get("msg", ""))[:100]
        except Exception:
            pass
        LAST_ERROR = f"{type(exc).__name__} {code} {detail}".strip()
        print(f"Tumblr falló con '{title}': {LAST_ERROR}", file=sys.stderr)
        return False
