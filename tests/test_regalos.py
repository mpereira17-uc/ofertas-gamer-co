import unittest
from datetime import datetime, timezone

from ogc import giveaways

NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
RAW = [{"id": 1, "title": "Landfall Archives Steam Giveaway", "worth": "$4.99", "image": "https://img/a.jpg", "type": "Game",
        "platforms": "PC, Steam", "end_date": "2026-11-02 23:59:00", "status": "Active", "open_giveaway_url": "https://www.gamerpower.com/open/a"},
       {"id": 2, "title": "Loot Giveaway", "type": "DLC", "platforms": "PC", "end_date": "N/A", "open_giveaway_url": "https://www.gamerpower.com/open/b"},
       {"id": 3, "title": "Viejo (GOG) Giveaway", "type": "Game", "platforms": "PC, GOG", "end_date": "2026-10-01 00:00:00", "open_giveaway_url": "https://www.gamerpower.com/open/c"},
       {"id": 4, "title": "Juego Luna Giveaway", "worth": "N/A", "type": "Game", "platforms": "PC, Amazon Luna", "end_date": "N/A", "open_giveaway_url": "https://www.gamerpower.com/open/d"}]


class RegalosTest(unittest.TestCase):
    def test_normaliza_y_filtra(self):
        items, status = giveaways.update(lambda url: RAW, [], NOW)
        self.assertEqual([g["title"] for g in items], ["Landfall Archives", "Juego Luna"])  # sin DLC ni vencidos
        self.assertEqual(items[0]["group"], "steam")
        self.assertEqual(items[0]["endsOn"], "2026-11-02")
        self.assertEqual(items[1]["group"], "amazon")
        self.assertEqual(items[1]["worth"], "")  # "N/A" no se muestra
        self.assertIn("2 regalos", status)

    def test_recuerda_primera_vez_y_terminados(self):
        first, _ = giveaways.update(lambda url: RAW, [], NOW)
        first[0]["firstSeen"] = "2026-10-25T10:00:00Z"
        later, _ = giveaways.update(lambda url: RAW[:1], first, NOW)
        self.assertEqual(later[0]["firstSeen"], "2026-10-25T10:00:00Z")
        gone = [g for g in later if not g["active"]]
        self.assertEqual([g["title"] for g in gone], ["Juego Luna"])

    def test_fuente_caida_conserva(self):
        first, _ = giveaways.update(lambda url: RAW, [], NOW)
        def boom(url):
            raise OSError("caída")
        kept, status = giveaways.update(boom, first, NOW)
        self.assertEqual(len(kept), 2)
        self.assertIn("falló", status)


if __name__ == "__main__":
    unittest.main()
