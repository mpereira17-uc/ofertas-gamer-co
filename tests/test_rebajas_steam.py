import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ogc.site import Site

ROOT = Path(__file__).resolve().parent.parent


class SteamEventsTest(unittest.TestCase):
    def test_eventos_oficiales_ordenados_y_sin_los_que_terminaron(self):
        cfg = json.loads((ROOT / "config" / "steam_eventos.json").read_text())
        self.assertTrue(cfg["fuente"].startswith("https://partner.steamgames.com/"))
        starts = [x["inicio"] for x in cfg["eventos"]]
        self.assertEqual(starts, sorted(starts))
        site = Site.__new__(Site)
        site.steam_cfg = cfg
        evs = site.steam_events(datetime(2026, 12, 20, 15, tzinfo=timezone.utc))
        self.assertNotIn("Auto-Battler RPG Fest", [x["nombre"] for x in evs])
        winter = next(x for x in evs if x["tipo"] == "rebaja")
        self.assertTrue(winter["live"])


if __name__ == "__main__":
    unittest.main()
