import unittest
from datetime import datetime, timedelta, timezone

from ogc import health

NOW = datetime(2026, 10, 25, 15, tzinfo=timezone.utc)


class FakeApi:
    def __init__(self):
        self.calls = []

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        return {"number": 7} if path == "/issues" else {}


class TestSalud(unittest.TestCase):
    def test_aviso_cuando_cae_un_dia_y_se_cierra_al_volver(self):
        api, st = FakeApi(), {}
        for i in range(5):
            st = health.track_sources(st, {"Epic": False}, NOW + timedelta(hours=4 * i), api)
        self.assertEqual(api.calls, [])
        st = health.track_sources(st, {"Epic": False}, NOW + timedelta(hours=24), api)
        self.assertEqual(api.calls[0][1], "/issues")
        self.assertEqual(st["sources"]["Epic"]["issue"], 7)
        st = health.track_sources(st, {"Epic": False}, NOW + timedelta(hours=28), api)
        self.assertEqual(len(api.calls), 1)  # no se repite el aviso
        st = health.track_sources(st, {"Epic": True}, NOW + timedelta(hours=32), api)
        self.assertEqual([c[0] for c in api.calls[1:]], ["POST", "PATCH"])
        self.assertEqual(st["sources"]["Epic"]["fails"], 0)

    def test_enlaces_una_vez_al_dia_y_solo_404(self):
        offers = [{"id": "a", "title": "A", "officialUrl": "https://x/a"}, {"id": "b", "title": "B", "officialUrl": "https://x/b"},
                  {"id": "c", "title": "C", "officialUrl": "https://x/search?q=c"}]
        codes = {"https://x/a": 200, "https://x/b": 404}
        st = health.check_links({}, offers, NOW, codes.get)
        self.assertEqual(st["linksChecked"], 2)
        self.assertEqual([b["id"] for b in st["linksBroken"]], ["b"])
        again = health.check_links(st, offers, NOW + timedelta(hours=4), lambda u: 1 / 0)
        self.assertEqual(again["linksChecked"], 2)

    def test_informe_mensual(self):
        api, st = FakeApi(), {}
        st = health.monthly_report(st, NOW, {"x": 1}, api)
        self.assertEqual(api.calls, [])  # la primera vez solo se marca el mes
        st = health.monthly_report(st, datetime(2026, 11, 1, 14, tzinfo=timezone.utc), {"Juegos": 3}, api)
        self.assertEqual(api.calls[0][2]["title"], "Informe de octubre de 2026")
        st = health.monthly_report(st, datetime(2026, 11, 2, 14, tzinfo=timezone.utc), {"Juegos": 3}, api)
        self.assertEqual(len(api.calls), 1)


if __name__ == "__main__":
    unittest.main()
