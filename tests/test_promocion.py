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
        self.assertFalse(promote.indexnow("https://x/", "", ["https://x/"]))

    def test_bluesky_marca_el_enlace(self):
        calls = []

        def fake_post(url, payload, headers=None, form=False):
            calls.append(payload)
            return {"did": "did:plc:1", "accessJwt": "t"}
        link = "https://mpereira17-uc.github.io/ofertas-gamer-co/oferta-juego.html"
        with mock.patch.dict(os.environ, {"BLUESKY_HANDLE": "a.bsky.social", "BLUESKY_APP_PASSWORD": "x"}), \
                mock.patch.object(promote, "_post", side_effect=fake_post), \
                mock.patch.object(promote, "bluesky_thumb", return_value={"$type": "blob", "size": 1}):
            self.assertTrue(promote.send_bluesky(OFFER, link))
        record = calls[1]["record"]
        self.assertLessEqual(len(record["text"]), 300)
        self.assertEqual(record["embed"]["external"]["thumb"]["$type"], "blob")
        span = record["facets"][0]["index"]
        self.assertEqual(record["text"].encode()[span["byteStart"]:span["byteEnd"]].decode(), link)


if __name__ == "__main__":
    unittest.main()
