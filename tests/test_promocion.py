import os
import unittest
from unittest import mock

from ogc import promote

OFFER = {"id": "cs-1", "title": "Juego", "store": "Steam", "currentPrice": 2.5, "originalPrice": 10,
         "discountPercentage": 75, "currency": "USD", "copApproximation": None, "affiliate": False}


class TestPromocion(unittest.TestCase):
    def test_sin_secretos_no_publica(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(promote.send_bluesky(OFFER, "https://x/oferta-juego.html"))
            self.assertFalse(promote.send_mastodon(OFFER, "https://x/oferta-juego.html"))
            self.assertFalse(promote.send_discord(OFFER, "https://x/oferta-juego.html"))
        self.assertFalse(promote.indexnow("https://x/", "", ["https://x/"]))

    def test_bluesky_marca_el_enlace(self):
        calls = []

        def fake_post(url, payload, headers=None, form=False):
            calls.append(payload)
            return {"did": "did:plc:1", "accessJwt": "t"}
        link = "https://mpereira17-uc.github.io/ofertas-gamer-co/oferta-juego.html"
        with mock.patch.dict(os.environ, {"BLUESKY_HANDLE": "a.bsky.social", "BLUESKY_APP_PASSWORD": "x"}), \
                mock.patch.object(promote, "_post", side_effect=fake_post):
            self.assertTrue(promote.send_bluesky(OFFER, link))
        record = calls[1]["record"]
        self.assertLessEqual(len(record["text"]), 300)
        span = record["facets"][0]["index"]
        self.assertEqual(record["text"].encode()[span["byteStart"]:span["byteEnd"]].decode(), link)

    def test_discord_solo_webhook_oficial(self):
        calls = []
        with mock.patch.object(promote, "_post", side_effect=lambda url, payload, **kw: calls.append((url, payload))):
            with mock.patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://evil.example/api/webhooks/1/x"}):
                self.assertFalse(promote.send_discord(OFFER, "https://x/oferta-juego.html"))
            with mock.patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/1/x"}):
                self.assertTrue(promote.send_discord(OFFER, "https://x/oferta-juego.html"))
        self.assertEqual(len(calls), 1)
        embed = calls[0][1]["embeds"][0]
        self.assertEqual(embed["url"], "https://x/oferta-juego.html")
        self.assertEqual(calls[0][1]["allowed_mentions"], {"parse": []})


if __name__ == "__main__":
    unittest.main()
