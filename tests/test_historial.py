import unittest
from datetime import datetime, timedelta, timezone

from ogc import history

NOW = datetime(2026, 10, 25, 15, tzinfo=timezone.utc)


def offer(price, store="steam", title="Hollow Knight"):
    return {"title": title, "storeId": store, "currency": "USD", "currentPrice": price, "originalPrice": 15.0}


class TestHistorial(unittest.TestCase):
    def test_guarda_el_menor_del_dia(self):
        h = history.record({}, [offer(9.0)], NOW)
        h = history.record(h, [offer(7.5)], NOW + timedelta(hours=4))
        h = history.record(h, [offer(8.0)], NOW + timedelta(hours=8))
        self.assertEqual(h["hollow-knight|steam|USD"]["points"], [["2026-10-25", 7.5]])

    def test_otras_tiendas_tambien(self):
        o = dict(offer(5.0), otherStores=[offer(6.0, store="gog")])
        h = history.record({}, [o], NOW)
        self.assertIn("hollow-knight|gog|USD", h)

    def test_minimo_solo_con_dos_semanas(self):
        h = history.record({}, [offer(10.0)], NOW - timedelta(days=5))
        h = history.record(h, [offer(5.0)], NOW)
        self.assertFalse(history.stats(h, offer(5.0), NOW)["isLow"])  # pocos días de datos: no se dice "mínimo"
        h = history.record({}, [offer(10.0)], NOW - timedelta(days=20))
        h = history.record(h, [offer(5.0)], NOW)
        st = history.stats(h, offer(5.0), NOW)
        self.assertTrue(st["isLow"])
        self.assertEqual(st["first"], "2026-10-05")
        self.assertFalse(history.stats(h, offer(6.0), NOW)["isLow"])

    def test_precio_que_nunca_cambio_no_es_minimo(self):
        h = history.record({}, [offer(5.0)], NOW - timedelta(days=30))
        h = history.record(h, [offer(5.0)], NOW)
        self.assertFalse(history.stats(h, offer(5.0), NOW)["isLow"])

    def test_se_olvidan_los_datos_muy_viejos(self):
        h = history.record({}, [offer(5.0)], NOW - timedelta(days=500))
        h = history.record(h, [offer(4.0, title="Otro")], NOW)
        self.assertNotIn("hollow-knight|steam|USD", h)

    def test_grafica(self):
        pts = [["2026-10-01", 10.0], ["2026-10-10", 5.0], ["2026-10-20", 8.0]]
        svg = history.chart_svg(pts, "USD", lambda v, c: f"US${v}")
        self.assertIn("<svg", svg)
        self.assertIn("mínimo US$5.0", svg)
        self.assertEqual(history.chart_svg(pts[:1], "USD", str), "")


if __name__ == "__main__":
    unittest.main()
