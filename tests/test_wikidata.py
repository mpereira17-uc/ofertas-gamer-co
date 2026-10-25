import unittest
from datetime import datetime, timezone

from ogc import wikidata

NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def row(qid, name, dates, links, plats, steam="", es="", yt=""):
    r = {"g": {"value": f"http://www.wikidata.org/entity/{qid}"}, "gLabel": {"value": name},
         "dates": {"value": dates}, "links": {"value": str(links)},
         "plats": {"value": plats}, "gens": {"value": "videojuego de acción"}}
    for key, value in (("steam", steam), ("es", es), ("yt", yt)):
        if value:
            r[key] = {"value": value}
    return r


DATA = {"results": {"bindings": [
    row("Q1", "Grand Theft Auto VI", "2027-05-01T00:00:00Z#11|2026-11-19T00:00:00Z#11", 80, "http://www.wikidata.org/entity/Q63184502=|http://www.wikidata.org/entity/Q98973368=Xbox Series X and Series S",
        es="https://es.wikipedia.org/wiki/Grand_Theft_Auto_VI", yt="QdBZY2fkU-0"),
    row("Q2", "Juego Compartido", "2026-12-01T00:00:00Z#10", 30, "Microsoft Windows|PlayStation 5", steam="555"),
    row("Q3", "Solo Año", "2027-01-01T00:00:00Z#9", 20, "Nintendo Switch 2"),
    row("Q1", "Grand Theft Auto VI", "2026-11-19T00:00:00Z#11", 80, "PlayStation 5"),
    row("Q4", "Q4", "2026-12-01T00:00:00Z#11", 10, ""),
]}}


class TestWikidata(unittest.TestCase):
    def test_lee_fechas_sin_inventar(self):
        games = wikidata.fetch_games(NOW, lambda url: DATA)
        self.assertEqual([g["id"] for g in games], ["wd-Q1", "steam-555", "wd-Q3"])  # sin repetir ni juegos sin nombre
        gta, shared, year = games
        self.assertEqual((gta["date"], gta["precision"]), ("2026-11-19", "day"))
        self.assertEqual(gta["platforms"], ["PlayStation", "Xbox"])
        self.assertEqual(gta["youtube"], "QdBZY2fkU-0")
        self.assertEqual(gta["url"], "https://es.wikipedia.org/wiki/Grand_Theft_Auto_VI")
        self.assertEqual((shared["date"], shared["precision"]), ("2026-12-01", "month"))
        self.assertTrue(shared["image"].startswith("https://shared.akamai.steamstatic.com/"))
        self.assertIsNone(year["date"])  # solo se sabe el año: "por confirmar"
        self.assertEqual(year["platforms"], ["Switch"])

    def test_une_con_steam(self):
        steam = [{"id": "steam-555", "slug": "otro-nombre", "title": "Shared", "platforms": ["Windows"], "rank": 1},
                 {"id": "steam-7", "slug": "b", "title": "B", "platforms": ["Windows"], "rank": 2}]
        games, status = wikidata.add_consoles(steam, [], NOW, lambda url: DATA)
        self.assertTrue(status.startswith("OK"))
        ids = [g["id"] for g in games]
        self.assertEqual(ids.count("steam-555"), 1)
        self.assertEqual(ids[:3], ["steam-555", "wd-Q1", "steam-7"])
        self.assertIn("PlayStation", games[0]["platforms"])
        self.assertEqual([g["rank"] for g in games], list(range(1, len(games) + 1)))

    def test_portada_y_resumen(self):
        games = wikidata.fetch_games(NOW, lambda url: DATA)
        asked = []

        def fetch(url):
            asked.append(url)
            return {"extract": "Un  juego de mundo abierto.", "originalimage": {"source": "https://upload.wikimedia.org/a.png"}}
        out = wikidata.enrich(games, [], fetch)
        gta = out[0]
        self.assertEqual(gta["image"], "https://i.ytimg.com/vi/QdBZY2fkU-0/maxresdefault.jpg")  # primero el tráiler oficial
        self.assertEqual(gta["description"], "Un juego de mundo abierto.")
        self.assertEqual(len(asked), 1)  # solo el que tiene artículo en español
        again = wikidata.enrich(wikidata.fetch_games(NOW, lambda url: DATA), out, lambda url: 1 / 0)
        self.assertEqual(again[0]["description"], "Un juego de mundo abierto.")  # se reutiliza sin volver a pedir

    def test_caido_conserva_lo_anterior(self):
        def broken(url):
            raise OSError("sin red")
        old = [{"id": "wd-Q1", "slug": "gta", "title": "GTA", "platforms": ["PlayStation"], "source": "wikidata"}]
        games, status = wikidata.add_consoles([], old, NOW, broken)
        self.assertEqual([g["id"] for g in games], ["wd-Q1"])
        self.assertIn("Falló", status)


if __name__ == "__main__":
    unittest.main()
