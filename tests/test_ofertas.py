import json
import os
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from ogc import affiliates, channels, model, sources

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
CFG = json.loads((ROOT / "config" / "site.json").read_text())
STORES = {s["id"]: s for s in json.loads((ROOT / "config" / "stores.json").read_text())["stores"]}


def fetch(url):
    name = "epic.json" if "epicgames" in url else "cheapshark.json"
    return json.loads((FIX / name).read_text())


class TestOfertas(unittest.TestCase):
    def setUp(self):
        self.now = model.now_utc()
        self.epic = sources.epic_free_games(STORES, 4000, self.now, CFG, fetch=fetch)
        self.deals = sources.cheapshark_deals(STORES, 4000, self.now, CFG, fetch=fetch)

    def test_todas_las_ofertas_generadas_son_validas(self):
        for offer in self.epic + self.deals:
            self.assertEqual(model.validate(offer, STORES), [], offer["title"])

    def test_filtra_tienda_desconocida_y_poco_descuento(self):
        titles = {o["title"] for o in self.deals}
        self.assertNotIn("Tienda desconocida", titles)
        self.assertNotIn("Poco descuento", titles)

    def test_imagen_insegura_se_descarta(self):
        witcher = next(o for o in self.deals if o["title"].startswith("The Witcher"))
        # La miniatura http:// se descarta; queda la portada https de Steam por su steamAppID.
        self.assertTrue(witcher["image"].startswith("https://"))
        self.assertNotIn("imageSmall", witcher)

    def test_portada_grande_de_steam(self):
        hollow = next(o for o in self.deals if o["title"] == "Hollow Knight" and o.get("imageSmall"))
        self.assertTrue(hollow["image"].endswith("/367520/header.jpg"))
        self.assertIn("capsule_sm_120", hollow["imageSmall"])

    def test_enlaces_oficiales_sin_afiliacion(self):
        for offer in self.epic + self.deals:
            self.assertFalse(offer["affiliate"])
            self.assertEqual(offer["destinationUrl"], offer["officialUrl"])
            self.assertIn(model.host(offer["officialUrl"]), STORES[offer["storeId"]]["domains"])

    def test_vencida_y_sin_tasa(self):
        expired = [o for o in self.epic if o["title"] == "Juego Vencido"]
        self.assertEqual(expired[0]["status"], "Vencido")
        no_rate = sources.cheapshark_deals(STORES, None, self.now, CFG, fetch=fetch)
        self.assertTrue(all(o["copApproximation"] is None for o in no_rate))

    def test_rechaza_registros_peligrosos(self):
        bad = dict(self.deals[0], officialUrl="http://store.steampowered.com/app/1/", destinationUrl="http://x")
        self.assertTrue(model.validate(bad, STORES))
        bad = dict(self.deals[0], officialUrl="https://evil.example.com/", destinationUrl="https://evil.example.com/")
        self.assertIn("dominio no autorizado: evil.example.com", model.validate(bad, STORES))
        bad = dict(self.deals[0], title="")
        self.assertIn("falta title", model.validate(bad, STORES))
        bad = dict(self.deals[0], discountPercentage=99)
        self.assertIn("descuento no coincide con los precios", model.validate(bad, STORES))

    def test_descuento_con_datos_incompletos(self):
        self.assertIsNone(model.discount(None, 5))
        self.assertIsNone(model.discount(10, 12))
        self.assertEqual(model.discount(20, 5), 75)

    def test_sin_duplicados(self):
        unique = model.dedupe(self.deals)
        self.assertEqual(sum(1 for o in unique if o["title"] == "Hollow Knight"), 1)

    def test_fuente_caida_conserva_ultima_version(self):
        merged = model.merge(self.deals, {"epic": self.epic}, {"cheapshark"}, self.now, CFG)
        self.assertTrue(any(o["source"] == "cheapshark" for o in merged))
        later = self.now + timedelta(hours=CFG["horas_retener_oferta_sin_confirmar"] + 1)
        merged = model.merge(self.deals, {"epic": self.epic}, {"cheapshark"}, later, CFG)
        self.assertFalse(any(o["source"] == "cheapshark" for o in merged))

    def test_conserva_fecha_de_creacion(self):
        old = [dict(self.deals[0], createdAt="2026-01-01T00:00:00Z")]
        merged = model.merge(old, {"cheapshark": [dict(self.deals[0])]}, set(), self.now, CFG)
        self.assertEqual(merged[0]["createdAt"], "2026-01-01T00:00:00Z")

    def test_afiliado_solo_si_aprobado(self):
        store = dict(STORES["gmg"], affiliateUrl="https://greenmangaming.sjv.io/c/1/2/3?u={url}")
        self.assertEqual(affiliates.build_destination("https://www.greenmangaming.com/x", store)[1], False)
        store["approved"] = True
        url, aff, net = affiliates.build_destination("https://www.greenmangaming.com/x", store)
        self.assertTrue(aff)
        self.assertEqual(net, "Impact")
        self.assertTrue(url.startswith("https://greenmangaming.sjv.io/c/1/2/3?u=https%3A%2F%2F"))
        with mock.patch.dict(os.environ, {"GMG_AFFILIATE_URL": "https://otro.example/?u={url}"}):
            self.assertTrue(affiliates.build_destination("https://www.greenmangaming.com/x", store)[0].startswith("https://otro.example/"))

    def test_telegram_incluye_datos_y_escapa(self):
        offer = next(o for o in self.deals if "script" in o["title"])
        text = channels.telegram_caption(offer)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("Fanatical", text)
        self.assertIn("Vigencia", text)
        self.assertNotIn("afiliado", text.lower())

    def test_telegram_sin_secretos_no_envia(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(channels.send_telegram(self.deals[0]))


if __name__ == "__main__":
    unittest.main()
