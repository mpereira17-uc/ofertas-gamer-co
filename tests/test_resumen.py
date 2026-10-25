import unittest
from datetime import datetime, timezone
from unittest import mock

from ogc import weekly

FRI_10AM_CO = datetime(2026, 10, 30, 15, tzinfo=timezone.utc)  # viernes 10 a. m. en Colombia
THU = datetime(2026, 10, 29, 15, tzinfo=timezone.utc)

OFFERS = [
    {"id": "a", "title": "Gratis <b>", "store": "Epic", "currentPrice": 0, "currency": "USD", "status": "Gratuito"},
    {"id": "b", "title": "Buen Descuento", "store": "Steam", "currentPrice": 2.0, "originalPrice": 20.0, "currency": "USD",
     "discountPercentage": 90, "status": "Activo", "image": "https://x/b.jpg"},
    {"id": "c", "title": "Poco Descuento", "store": "GOG", "currentPrice": 9.0, "originalPrice": 10.0, "currency": "USD",
     "discountPercentage": 10, "status": "Activo"},
]
GAMES = [{"id": "g1", "title": "Estreno", "date": "2026-11-02", "precision": "day", "rank": 1},
         {"id": "g2", "title": "Lejano", "date": "2027-05-01", "precision": "day", "rank": 2}]


class TestResumen(unittest.TestCase):
    def test_solo_el_viernes_y_una_vez(self):
        self.assertTrue(weekly.is_due(FRI_10AM_CO, []))
        self.assertFalse(weekly.is_due(THU, []))
        self.assertFalse(weekly.is_due(datetime(2026, 10, 30, 12, tzinfo=timezone.utc), []))  # 7 a. m. en Colombia
        done = [{"week": weekly.week_key(FRI_10AM_CO)}]
        self.assertFalse(weekly.is_due(FRI_10AM_CO, done))

    def test_elige_y_escapa(self):
        snap = weekly.snapshot(FRI_10AM_CO, *weekly.pick(OFFERS, GAMES, FRI_10AM_CO))
        self.assertEqual([o["id"] for o in snap["free"]], ["a"])
        self.assertEqual([o["id"] for o in snap["deals"]], ["b"])  # el de 10% no entra
        self.assertEqual([g["id"] for g in snap["games"]], ["g1"])  # solo lo de esta semana
        text = weekly.telegram_text(snap, "https://sitio/resumen-semanal.html")
        self.assertIn("Gratis &lt;b&gt;", text)
        self.assertNotIn("Gratis <b>", text)
        self.assertEqual(weekly.page_name(snap), "resumen-2026-s44.html")

    def test_publica_en_cada_red(self):
        snap = weekly.snapshot(FRI_10AM_CO, *weekly.pick(OFFERS, GAMES, FRI_10AM_CO))
        dc = mock.Mock(ready=True)
        dc.post.return_value = 1
        sky = mock.Mock(return_value=True)
        with mock.patch.object(weekly, "send_telegram_text", return_value=True):
            done = weekly.publish(snap, "https://sitio/r.html", dc, sky)
        self.assertEqual(done, ["Telegram", "Discord", "Bluesky"])
        self.assertEqual(dc.post.call_args[0][0], "ofertas")
        self.assertEqual(sky.call_args[0][4], "https://x/b.jpg")


if __name__ == "__main__":
    unittest.main()
