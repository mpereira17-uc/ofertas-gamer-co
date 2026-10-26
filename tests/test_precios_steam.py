import unittest
from datetime import datetime, timezone

from ogc import releases

NOW = datetime(2026, 10, 26, 23, 0, tzinfo=timezone.utc)


class SteamPricesTest(unittest.TestCase):
    def test_precio_con_descuento(self):
        entry = {"success": True, "data": {"price_overview": {"currency": "COP", "initial": 9990000, "final": 5994000, "discount_percent": 40}}}
        p = releases.steam_price(entry, NOW)
        self.assertEqual((p["final"], p["initial"], p["discount"]), (59940, 99900, 40))

    def test_sin_precio_o_moneda_rara(self):
        self.assertIsNone(releases.steam_price({"success": True, "data": []}, NOW))
        self.assertIsNone(releases.steam_price({"success": False}, NOW))
        self.assertIsNone(releases.steam_price({"success": True, "data": {"price_overview": {"currency": "USD", "final": 999}}}, NOW))

    def test_refresca_por_tandas_y_conserva_si_falla(self):
        games = [{"id": "steam-1"}, {"id": "steam-2", "price": {"final": 1}}, {"id": "wd-Q1"}]
        urls = []

        def fetch(url):
            urls.append(url)
            return {"1": {"success": True, "data": {"price_overview": {"currency": "COP", "initial": 100000, "final": 50000, "discount_percent": 50}}}}

        out, ok = releases.refresh_prices(games, NOW, fetch)
        self.assertEqual(len(urls), 1)
        self.assertIn("appids=1,2", urls[0])
        self.assertEqual(out[0]["price"]["discount"], 50)
        self.assertEqual(out[1]["price"], {"final": 1})  # Steam no respondió por él: se conserva
        self.assertEqual(ok, 1)

        def broken(url):
            raise OSError("caído")
        out, ok = releases.refresh_prices(games, NOW, broken)
        self.assertEqual((out[1]["price"], ok), ({"final": 1}, 0))


if __name__ == "__main__":
    unittest.main()
