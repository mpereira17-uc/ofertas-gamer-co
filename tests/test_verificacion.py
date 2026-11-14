import json
import unittest
import urllib.parse

from ogc import verify


def steam_item(appid, final, orig, pct, end=None):
    b = {"final_price_in_cents": final, "original_price_in_cents": orig, "discount_pct": pct}
    if end:
        b["active_discounts"] = [{"discount_end_date": end}]
    return {"appid": appid, "best_purchase_option": b}


def fetcher(steam=None, gog=None, fail_steam=False, fail_gog=False):
    def fetch(url):
        if "IStoreBrowseService" in url:
            if fail_steam:
                raise OSError("caído")
            q = json.loads(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["input_json"][0])
            assert q["context"]["country_code"] == "CO"
            return {"response": {"store_items": steam or []}}
        if "catalog.gog.com" in url:
            if fail_gog:
                raise OSError("caído")
            assert "countryCode=CO" in url
            return {"products": gog or []}
        raise AssertionError(url)
    return fetch


CIV = {"id": "cs-1", "title": "Sid Meier's Civilization IV", "store": "Steam", "storeId": "steam", "steamAppID": 3900,
       "currency": "USD", "currentPrice": 3.99, "originalPrice": 19.99, "discountPercentage": 80, "copApproximation": 13100}
DD = dict(CIV, id="cs-2", title="Darkest Dungeon", steamAppID=262060)
METRO_GOG = {"id": "cs-3", "title": "METRO 2033 Redux", "store": "GOG", "storeId": "gog", "currency": "USD", "currentPrice": 2.99,
             "originalPrice": 19.99, "discountPercentage": 85, "officialUrl": "https://www.gog.com/en/games?query=Metro",
             "destinationUrl": "https://www.gog.com/en/games?query=Metro"}
FANATICAL = {"id": "cs-4", "title": "Metro 2033 Redux", "store": "Fanatical", "storeId": "fanatical"}


class VerificacionTest(unittest.TestCase):
    def test_steam_usa_el_precio_oficial_de_colombia_en_pesos(self):
        out, _ = verify.run([CIV], fetcher(steam=[steam_item(3900, 800000, 4000000, 80, 1795111200)]))
        self.assertEqual(len(out), 1)
        o = out[0]
        self.assertEqual((o["currency"], o["currentPrice"], o["originalPrice"], o["discountPercentage"]), ("COP", 8000, 40000, 80))
        self.assertIsNone(o["copApproximation"])
        self.assertEqual(o["regions"], ["CO"])
        self.assertEqual(o["expiresAt"], "2026-11-19T18:00:00Z")

    def test_steam_con_numeros_como_texto(self):
        out, _ = verify.run([CIV], fetcher(steam=[steam_item(3900, "800000", "4000000", "80")]))
        self.assertEqual((out[0]["currentPrice"], out[0]["originalPrice"]), (8000, 40000))

    def test_steam_sin_descuento_en_colombia_no_se_publica(self):
        out, status = verify.run([DD], fetcher(steam=[steam_item(262060, 5880000, None, None)]))
        self.assertEqual(out, [])
        self.assertIn("0 de 1", status)

    def test_gog_confirma_titulo_pagina_y_precio(self):
        gog = [{"title": "Metro 2033", "price": {"finalMoney": {"amount": "2.99"}, "baseMoney": {"amount": "9.99"}}, "storeLink": "https://www.gog.com/en/game/metro_2033"},
               {"title": "METRO 2033 Redux", "price": {"finalMoney": {"amount": "2.05"}, "baseMoney": {"amount": "20.49"}},
                "storeLink": "https://www.gog.com/en/game/metro_2033_redux"}]
        out, _ = verify.run([METRO_GOG], fetcher(gog=gog), rate=4000)
        self.assertEqual(out[0]["destinationUrl"], "https://www.gog.com/en/game/metro_2033_redux")
        self.assertEqual((out[0]["currentPrice"], out[0]["originalPrice"], out[0]["discountPercentage"]), (2.05, 20.49, 90))
        self.assertEqual(out[0]["copApproximation"], 8200)

    def test_gog_sin_coincidencia_o_enlace_raro_no_se_publica(self):
        raro = [{"title": "METRO 2033 Redux", "price": {"finalMoney": {"amount": "2"}, "baseMoney": {"amount": "20"}}, "storeLink": "https://evil.example/x"}]
        self.assertEqual(verify.run([METRO_GOG], fetcher(gog=raro))[0], [])
        self.assertEqual(verify.run([METRO_GOG], fetcher(gog=[]))[0], [])

    def test_tiendas_sin_verificacion_no_se_publican(self):
        out, status = verify.run([FANATICAL], fetcher())
        self.assertEqual(out, [])
        self.assertIn("Fanatical 1", status)

    def test_si_steam_o_gog_no_responden_se_lanza_error(self):
        with self.assertRaises(RuntimeError):
            verify.run([CIV], fetcher(fail_steam=True))
        with self.assertRaises(RuntimeError):
            verify.run([METRO_GOG], fetcher(fail_gog=True))

    def test_normaliza_titulos(self):
        self.assertEqual(verify.norm("Sid Meier's Civilization® IV™"), verify.norm("Sid Meiers Civilization IV"))


if __name__ == "__main__":
    unittest.main()
