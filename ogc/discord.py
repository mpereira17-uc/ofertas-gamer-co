"""Publicación en Discord con la API oficial.

- Con DISCORD_BOT_TOKEN (y el servidor en config/site.json) cada cosa va a su canal:
  ofertas → 🔥・ofertas, juegos gratis → 🎁・juegos-gratis, lanzamientos → 📅・lanzamientos.
- Sin bot, pero con DISCORD_WEBHOOK_URL, todo va al canal del webhook.
- La primera vez (sin historial) publica de una vez lo que ya existe; después solo lo nuevo.
Nunca se imprimen tokens ni la URL del webhook.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://discord.com/api/v10"
WEBHOOK_PREFIXES = ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")
CHANNELS = {"ofertas": "・ofertas", "gratis": "・juegos-gratis", "lanzamientos": "・lanzamientos"}
GREEN, GOLD, BLUE = 0x22C55E, 0xF59E0B, 0x3B82F6
BACKFILL = {"ofertas": 40, "gratis": 20, "lanzamientos": 30}


def _request(method, url, payload=None, token=None):
    headers = {"Content-Type": "application/json", "User-Agent": "DiscordBot (https://ofertas-gamer-co.pages.dev, 1.0)"}
    if token:
        headers["Authorization"] = f"Bot {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    for _ in range(5):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(float(json.loads(exc.read() or b"{}").get("retry_after", 2)) + 0.5)
    raise RuntimeError("Discord siguió limitando las peticiones")


def offer_embed(offer, link, price_line):
    free = offer.get("currentPrice") == 0
    head = "🎁 GRATIS" if free else f"🔥 -{offer.get('discountPercentage') or 0}%"
    lines = [f"**{head}** en {offer['store']}", price_line(offer)]
    if offer.get("affiliate"):
        lines.append("_Enlace de afiliado._")
    embed = {"title": offer["title"][:250], "url": link, "description": "\n".join(lines)[:2000],
             "color": GOLD if free else GREEN, "footer": {"text": "Ofertas Gamer CO · confirma el precio en la tienda"}}
    if (offer.get("image") or "").startswith("https://"):
        embed["image"] = {"url": offer["image"]}
    return embed


def game_embed(game, link, date_label):
    lines = [f"📅 **{date_label(game.get('date'), game.get('precision'))}**"]
    if game.get("genres"):
        lines.append(" · ".join(game["genres"]))
    if game.get("description"):
        lines.append(game["description"][:300])
    embed = {"title": game["title"][:250], "url": link, "description": "\n".join(lines)[:2000], "color": BLUE,
             "footer": {"text": f"{game.get('store', 'Steam')} · fecha según la tienda"}}
    if (game.get("image") or "").startswith("https://"):
        embed["image"] = {"url": game["image"]}
    return embed


class Discord:
    def __init__(self, env=os.environ, guild="", request=_request):
        self.token = (env.get("DISCORD_BOT_TOKEN") or "").strip()
        self.hook = (env.get("DISCORD_WEBHOOK_URL") or "").strip()
        self.guild = (env.get("DISCORD_GUILD_ID") or guild or "").strip()
        self.request = request
        self._ids = None
        if not self.hook.startswith(WEBHOOK_PREFIXES):
            self.hook = ""
        if not self.guild.isdigit():
            self.token = ""

    @property
    def ready(self):
        return bool(self.token or self.hook)

    def channel_ids(self):
        if self._ids is None:
            chans = self.request("GET", f"{API}/guilds/{self.guild}/channels", token=self.token)
            self._ids = {key: next((c["id"] for c in chans if c.get("type") == 0 and c["name"].endswith(suffix)), None)
                         for key, suffix in CHANNELS.items()}
        return self._ids

    def post(self, kind, embeds):
        """Publica en lotes de hasta 10 tarjetas por mensaje. Devuelve cuántas salieron."""
        sent = 0
        for i in range(0, len(embeds), 10):
            payload = {"embeds": embeds[i:i + 10], "allowed_mentions": {"parse": []}}
            try:
                if self.token:
                    cid = self.channel_ids().get(kind) or self.channel_ids().get("ofertas")
                    if not cid:
                        return sent
                    self.request("POST", f"{API}/channels/{cid}/messages", payload, token=self.token)
                else:
                    self.request("POST", self.hook, dict(payload, username="Ofertas Gamer CO"))
                sent += len(embeds[i:i + 10])
            except Exception as exc:
                print(f"Discord falló ({kind}): {type(exc).__name__}", file=sys.stderr)
                return sent
        return sent

    def post_raw(self, kind, payload):
        """Un mensaje con cualquier contenido oficial de Discord (por ejemplo, una encuesta). True si salió."""
        payload = dict(payload, allowed_mentions={"parse": []})
        try:
            if self.token:
                cid = self.channel_ids().get(kind) or self.channel_ids().get("ofertas")
                if not cid:
                    return False
                self.request("POST", f"{API}/channels/{cid}/messages", payload, token=self.token)
            elif self.hook:
                self.request("POST", self.hook, dict(payload, username="Ofertas Gamer CO"))
            else:
                return False
            return True
        except Exception as exc:
            print(f"Discord falló ({kind}): {type(exc).__name__}", file=sys.stderr)
            return False


def publish(dc, offers, games, link_for, history, limit, price_line, date_label, worth=lambda o: True):
    """Publica ofertas, gratis y lanzamientos que aún no estén en el historial. Devuelve el conteo por tipo."""
    counts = {}
    first = {k: not history.get(f"discord_{k}") for k in CHANNELS}
    free = [o for o in offers if o.get("currentPrice") == 0]
    paid = [o for o in offers if o.get("currentPrice") != 0 and worth(o)]
    upcoming = sorted((g for g in games if g.get("date") and g.get("precision") == "day" and g.get("comingSoon")),
                      key=lambda g: g["date"])
    for kind, items, make in (("gratis", free, lambda o, l: offer_embed(o, l, price_line)),
                              ("ofertas", paid, lambda o, l: offer_embed(o, l, price_line)),
                              ("lanzamientos", upcoming, lambda g, l: game_embed(g, l, date_label))):
        done = history.setdefault(f"discord_{kind}", [])
        todo = [x for x in items if x["id"] not in done and link_for(x)]
        todo = todo[:BACKFILL[kind] if first[kind] else limit]
        sent = dc.post(kind, [make(x, link_for(x)) for x in todo]) if todo else 0
        done.extend(x["id"] for x in todo[:sent])
        counts[kind] = sent
    return counts
