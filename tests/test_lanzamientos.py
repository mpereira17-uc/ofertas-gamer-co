import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ogc import releases

FIX = Path(__file__).resolve().parent / "fixtures"


def fetch(url):
    name = "steam_featured.json" if "featuredcategories" in url else "steam_appdetails.json"
    return json.loads((FIX / name).read_text())


class TestLanzamientos(unittest.TestCase):
    now = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)

    def test_fechas_de_steam(self):
        self.assertEqual(releases.parse_release("14 Nov, 2030"), ("2030-11-14", "day"))
        self.assertEqual(releases.parse_release("Nov 14, 2030"), ("2030-11-14", "day"))
        self.assertEqual(releases.parse_release("March 2031"), ("2031-03-01", "month"))
        self.assertEqual(releases.parse_release("Coming soon"), (None, None))
        self.assertEqual(releases.parse_release("Q2 2031"), (None, None))

    def test_etiquetas(self):
        self.assertEqual(releases.date_label("2026-11-14", "day"), "Sábado 14 de noviembre de 2026")
        self.assertEqual(releases.date_label("2031-03-01", "month"), "Marzo de 2031")
        self.assertEqual(releases.date_label(None, None), "Fecha por confirmar")
        self.assertEqual(releases.relative_label("2026-10-26", "day", self.now), "mañana")
        self.assertEqual(releases.relative_label("2026-10-20", "day", self.now), "hace 5 días")
        self.assertEqual(releases.relative_label("2031-03-01", "month", self.now), "")

    def test_solo_juegos_con_datos_seguros(self):
        games = releases.steam_releases(self.now, fetch)
        titles = {g["title"] for g in games}
        self.assertNotIn("Pack de Trajes", titles)
        self.assertNotIn("Clásico Reciente", titles)  # salió hace más de 45 días
        self.assertEqual(len(games), 3)
        misterio = next(g for g in games if g["title"].startswith("Misterio"))
        self.assertEqual(misterio["image"], "")
        self.assertIsNone(misterio["date"])
        for g in games:
            self.assertTrue(g["url"].startswith("https://store.steampowered.com/app/"))
            self.assertNotIn("<", g["description"])

    def test_ids_de_la_busqueda_popular(self):
        data = {"items": [{"name": "A", "logo": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1001/capsule_sm_120.jpg?t=1"},
                          {"name": "B", "logo": "https://cdn.example/sin-id.jpg"},
                          {"name": "A otra vez", "logo": "https://x/steam/apps/1001/a.jpg"}]}
        self.assertEqual(releases.search_ids(data), [1001])

    def test_steam_caido_conserva_lo_anterior(self):
        def broken(url):
            raise OSError("sin red")
        old = [{"id": "steam-1", "title": "Anterior"}]
        games, status = releases.update(old, self.now, broken)
        self.assertEqual(games, old)
        self.assertIn("Falló", status)


if __name__ == "__main__":
    unittest.main()
