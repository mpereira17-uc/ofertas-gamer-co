import unittest
from datetime import datetime, timezone

from ogc import community, images


class TestComunidad(unittest.TestCase):
    def test_resumen_diario_una_vez_desde_las_7(self):
        early = datetime(2026, 10, 25, 11, tzinfo=timezone.utc)  # 6 a. m. en Colombia
        later = datetime(2026, 10, 25, 13, tzinfo=timezone.utc)  # 8 a. m.
        self.assertFalse(community.daily_due(early, {}))
        self.assertTrue(community.daily_due(later, {}))
        self.assertFalse(community.daily_due(later, {"sentDate": "2026-10-25"}))

    def test_texto_diario(self):
        dotd = {"title": "Juego <A>", "discountPercentage": 90, "currentPrice": 1.0, "currency": "USD", "store": "Steam"}
        text = community.daily_text(dotd, [{"title": "Gratis 1"}], [{"title": "Estreno"}], "https://x/oferta-del-dia.html")
        self.assertIn("Juego &lt;A&gt;", text)
        self.assertIn("Gratis 1", text)
        self.assertIn("Estreno", text)

    def test_encuesta(self):
        snap = {"week": "2026-S44", "free": [{"title": "A"}], "deals": [{"title": "B"}, {"title": "A"}], "games": [{"title": "C"}]}
        self.assertEqual(community.poll_options(snap), ["A", "B", "C", "Otro / ninguno"])
        self.assertEqual(community.poll_options({"free": [{"title": "A"}]}), [])
        state = {"telegram": "p1"}
        community.apply_poll_update(state, {"id": "p1", "total_voter_count": 3, "options": [{"text": "A", "voter_count": 2}, {"text": "B", "voter_count": 1}]})
        self.assertEqual(state["votes"], {"A": 2, "B": 1})
        community.apply_poll_update(state, {"id": "otra", "total_voter_count": 99, "options": []})
        self.assertEqual(state["total"], 3)

    @unittest.skipUnless(images.available(), "sin Pillow")
    def test_imagen(self):
        jpg = images.offer_card({"title": "Juego", "currentPrice": 0, "currency": "USD", "store": "Epic"}, None, str)
        self.assertTrue(jpg.startswith(b"\xff\xd8"))


if __name__ == "__main__":
    unittest.main()
