import unittest

from ogc import channels, sources


EPIC = {"data": {"Catalog": {"searchStore": {"elements": [
    {"id": "abc", "title": "Juego Próximo", "productSlug": "juego-proximo", "keyImages": [{"type": "OfferImageWide", "url": "https://cdn1.epicgames.com/a.png"}],
     "price": {"totalPrice": {"discountPrice": 1999, "originalPrice": 1999}},
     "promotions": {"promotionalOffers": [], "upcomingPromotionalOffers": [{"promotionalOffers": [
         {"startDate": "2026-10-29T15:00:00.000Z", "endDate": "2026-11-05T15:00:00.000Z", "discountSetting": {"discountPercentage": 0}}]}]}},
    {"id": "def", "title": "Solo descuento", "price": {"totalPrice": {"discountPrice": 999, "originalPrice": 1999}},
     "promotions": {"upcomingPromotionalOffers": [{"promotionalOffers": [
         {"startDate": "2026-10-29T15:00:00.000Z", "endDate": "2026-11-05T15:00:00.000Z", "discountSetting": {"discountPercentage": 50}}]}]}},
]}}}}


class TestGratis(unittest.TestCase):
    def test_proximos_de_epic(self):
        out = sources.epic_upcoming(lambda url: EPIC)
        self.assertEqual([g["title"] for g in out], ["Juego Próximo"])
        self.assertEqual(out[0]["url"], "https://store.epicgames.com/es-ES/p/juego-proximo")
        self.assertEqual(out[0]["startsAt"][:10], "2026-10-29")

    def test_aviso_de_juego_grande(self):
        base = {"title": "X", "store": "Epic", "destinationUrl": "https://x", "regions": ["CO"], "currentPrice": 0}
        self.assertIn("JUEGO GRANDE", channels.telegram_caption(dict(base, originalPrice=29.99, currency="USD")))
        self.assertNotIn("JUEGO GRANDE", channels.telegram_caption(dict(base, originalPrice=4.99, currency="USD")))
        self.assertIn("JUEGO GRANDE", channels.telegram_caption(dict(base, originalPrice=89000, currency="COP")))
        self.assertTrue(channels.telegram_caption(dict(base, originalPrice=29.99, currency="USD"), "⏰ ÚLTIMA\n").startswith("⏰ ÚLTIMA"))


if __name__ == "__main__":
    unittest.main()
