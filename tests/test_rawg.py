import unittest
from datetime import datetime, timezone

from ogc import rawg

NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def item(i, name, released, plats, tba=False):
    return {"id": i, "slug": name.lower().replace(" ", "-"), "name": name, "released": released, "tba": tba,
            "background_image": "https://media.rawg.io/x.jpg", "genres": [{"name": "Action"}],
            "platforms": [{"platform": {"name": p}} for p in plats]}


PAGE = {"next": None, "results": [
    item(1, "Juego Consola", "2026-11-10", ["PlayStation 5", "Xbox Series S/X", "Nintendo Switch"]),
    item(2, "Juego Compartido", "2026-11-20", ["PC", "PlayStation 5"]),
    item(3, "Sin Fecha", None, ["PlayStation 5"], tba=True),
]}


class TestRawg(unittest.TestCase):
    def test_sin_clave_no_consulta(self):
        def fail(url):
            raise AssertionError("no debía consultar")
        steam = [{"id": "steam-1", "slug": "a", "title": "A", "platforms": ["Windows"], "rank": 1}]
        games, status = rawg.add_consoles(steam, [], NOW, fail, env={})
        self.assertEqual(games, steam)
        self.assertIn("RAWG_API_KEY", status)

    def test_une_sin_repetir_y_suma_consolas(self):
        urls = []

        def fetch(url):
            urls.append(url)
            return PAGE
        steam = [{"id": "steam-9", "slug": "juego-compartido", "title": "Juego Compartido", "platforms": ["Windows"], "rank": 1}]
        games, status = rawg.add_consoles(steam, [], NOW, fetch, env={"RAWG_API_KEY": "k"})
        self.assertTrue(status.startswith("OK"))
        self.assertEqual([g["id"] for g in games], ["steam-9", "rawg-1", "rawg-3"])  # el compartido queda con la ficha de Steam
        self.assertIsNone(games[2]["date"])  # sin fecha exacta: "por confirmar", nunca una fecha inventada
        self.assertEqual(games[0]["platforms"], ["Windows", "PlayStation"])
        self.assertEqual(games[1]["platforms"], ["PlayStation", "Xbox", "Switch"])
        self.assertEqual([g["rank"] for g in games], [1, 2, 3])
        self.assertTrue(games[1]["url"].startswith("https://rawg.io/games/"))
        self.assertIn("ordering=-added", urls[0])

    def test_rawg_caido_conserva_lo_anterior(self):
        def broken(url):
            raise OSError("sin red")
        old = [dict(rawg.to_game(PAGE["results"][0], NOW))]
        games, status = rawg.add_consoles([], old, NOW, broken, env={"RAWG_API_KEY": "k"})
        self.assertEqual([g["id"] for g in games], ["rawg-1"])
        self.assertIn("Falló", status)


if __name__ == "__main__":
    unittest.main()
