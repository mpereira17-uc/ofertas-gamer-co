import json
import unittest
import urllib.parse
from datetime import datetime, timezone

from ogc import capsules

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def items(*ids, hashed=False):
    out = []
    for i in ids:
        fmt = f"steam/apps/{i}/{'abc123/' if hashed else ''}${{FILENAME}}?t=1"
        out.append({"appid": i, "assets": {"asset_url_format": fmt, "library_capsule": "library_600x900.jpg"}})
    return {"response": {"store_items": out}}


class PortadasTest(unittest.TestCase):
    def test_pide_en_lotes_y_arma_la_url(self):
        offers = [{"id": str(i), "steamAppID": i} for i in range(1, 121)] + [{"id": "epic"}]
        asked = []

        def fetch(url):
            q = json.loads(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["input_json"][0])
            ids = [x["appid"] for x in q["ids"]]
            asked.append(ids)
            self.assertTrue(q["data_request"]["include_assets"])
            return items(*ids, hashed=True)

        cache, status = capsules.update(offers, {}, NOW, fetch)
        self.assertEqual([len(a) for a in asked], [50, 50, 20])
        self.assertEqual(cache["7"]["url"], "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/7/abc123/library_600x900.jpg?t=1")
        self.assertIn("120", status)
        out = capsules.attach([dict(o) for o in offers], cache)
        self.assertTrue(out[0]["capsule"].startswith("https://shared.fastly.steamstatic.com/"))
        self.assertNotIn("capsule", out[-1])

    def test_guarda_tambien_la_imagen_panoramica(self):
        def fetch(url):
            return {"response": {"store_items": [{"appid": 9, "assets": {"asset_url_format": "steam/apps/9/${FILENAME}?t=2",
                    "library_capsule": "library_600x900.jpg", "library_hero": "library_hero.jpg"}}]}}
        cache, _ = capsules.update([{"id": "a", "steamAppID": 9}], {}, NOW, fetch)
        out = capsules.attach([{"id": "a", "steamAppID": 9}], cache)
        self.assertEqual(out[0]["hero"], "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/9/library_hero.jpg?t=2")

    def test_pide_de_nuevo_lo_guardado_sin_panoramica(self):
        old = {"1": {"url": "https://shared.fastly.steamstatic.com/x/1.jpg", "at": "2026-11-12T00:00:00Z"}}
        asked = []
        capsules.update([{"id": "a", "steamAppID": 1}], old, NOW, lambda url: asked.append(url) or items(1))
        self.assertEqual(len(asked), 1)

    def test_no_repite_lo_vigente_y_renueva_lo_viejo(self):
        cache = {"1": {"url": "https://shared.fastly.steamstatic.com/x/1.jpg", "hero": "", "reviews": None, "at": "2026-11-10T00:00:00Z"},
                 "2": {"url": "https://shared.fastly.steamstatic.com/x/2.jpg", "at": "2026-10-01T00:00:00Z"}}
        asked = []

        def fetch(url):
            asked.append(url)
            return items(2)

        new, _ = capsules.update([{"id": "a", "steamAppID": 1}, {"id": "b", "steamAppID": 2}], cache, NOW, fetch)
        self.assertEqual(len(asked), 1)
        self.assertIn("%22appid%22%3A%202", asked[0])
        self.assertEqual(new["1"], cache["1"])

    def test_sin_portada_o_url_insegura_no_se_usa(self):
        def fetch(url):
            return {"response": {"store_items": [{"appid": 5, "assets": {}}, {"appid": 6, "assets": {"asset_url_format": "javascript:${FILENAME}", "library_capsule": "x.jpg"}}]}}
        cache, _ = capsules.update([{"id": "a", "steamAppID": 5}, {"id": "b", "steamAppID": 6}], {}, NOW, fetch)
        out = capsules.attach([{"id": "a", "steamAppID": 5}, {"id": "b", "steamAppID": 6}], cache)
        self.assertNotIn("capsule", out[0])
        self.assertNotIn("capsule", out[1])
        self.assertIn("5", cache)  # se recuerda que no tiene, para no preguntar en cada corrida

    def test_steam_caido_no_rompe_y_conserva_lo_guardado(self):
        def broken(url):
            raise OSError("caído")
        old = {"1": {"url": "https://shared.fastly.steamstatic.com/x/1.jpg", "at": "2026-10-01T00:00:00Z"}}
        cache, status = capsules.update([{"id": "a", "steamAppID": 1}], old, NOW, broken)
        self.assertEqual(cache["1"]["url"], old["1"]["url"])
        self.assertIn("falló", status)


if __name__ == "__main__":
    unittest.main()


class ResenasYDeckTest(unittest.TestCase):
    def test_guarda_resenas_y_steam_deck(self):
        def fetch(url):
            q = json.loads(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["input_json"][0])
            self.assertTrue(q["data_request"]["include_reviews"])
            self.assertTrue(q["data_request"]["include_platforms"])
            return {"response": {"store_items": [{"appid": 3, "assets": {}, "platforms": {"steam_deck_compat_category": 3},
                    "reviews": {"summary_filtered": {"review_count": 2821, "percent_positive": 92, "review_score_label": "Muy positivas"}}}]}}
        cache, _ = capsules.update([{"id": "a", "steamAppID": 3}], {}, NOW, fetch)
        out = capsules.attach([{"id": "a", "steamAppID": 3}], cache)[0]
        self.assertEqual(out["reviews"], {"label": "Muy positivas", "pct": 92, "count": 2821})
        self.assertEqual(out["deck"], "verified")

    def test_pocas_resenas_o_texto_raro_no_se_muestran(self):
        def fetch(url):
            return {"response": {"store_items": [
                {"appid": 4, "reviews": {"summary_filtered": {"review_count": 3, "percent_positive": 100, "review_score_label": "3 reseñas"}}},
                {"appid": 5, "reviews": {"summary_filtered": {"review_count": 900, "percent_positive": 80, "review_score_label": "<b>x</b>"}}}]}}
        cache, _ = capsules.update([{"id": "a", "steamAppID": 4}, {"id": "b", "steamAppID": 5}], {}, NOW, fetch)
        out = capsules.attach([{"id": "a", "steamAppID": 4}, {"id": "b", "steamAppID": 5}], cache)
        self.assertNotIn("reviews", out[0])
        self.assertNotIn("reviews", out[1])
