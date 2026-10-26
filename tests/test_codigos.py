import unittest
from datetime import datetime, timedelta, timezone

from ogc import codes

NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


def fetcher(seria, ennead):
    def fetch(url):
        data = seria if "seria" in url else ennead
        if isinstance(data, Exception):
            raise data
        return data
    return fetch


SERIA = {"codes": [{"code": "abc123def", "rewards": "Primogem x60, Mora x5000", "status": "OK"}]}
ENNEAD = {"active": [{"code": "ABC123DEF", "rewards": ["Primogem x60"]}, {"code": "SECOND2026", "rewards": []}],
          "inactive": [{"code": "OLDONE111"}]}


class CodesTest(unittest.TestCase):
    def test_first_run_seeds_without_announcing(self):
        state, fresh, report = codes.update({}, NOW, fetcher(SERIA, ENNEAD))
        self.assertEqual(fresh, [])
        live = [c["code"] for c in codes.active_codes(state, "genshin")]
        self.assertEqual(sorted(live), ["ABC123DEF", "SECOND2026"])
        self.assertEqual(state["games"]["genshin"]["codes"]["ABC123DEF"]["rewards"], ["Protogemas ×60", "Mora ×5000"])
        self.assertEqual([c["code"] for c in codes.expired_codes(state, "genshin")], ["OLDONE111"])
        self.assertIn("2 activos", report)

    def test_new_code_is_announced_once(self):
        state, _, _ = codes.update({}, NOW, fetcher(SERIA, ENNEAD))
        more = dict(ENNEAD, active=ENNEAD["active"] + [{"code": "BRANDNEW99", "rewards": ["Primogem x100"]}])
        later = NOW + timedelta(hours=4)
        state, fresh, _ = codes.update(state, later, fetcher(SERIA, more))
        self.assertEqual(fresh[0][1], "BRANDNEW99")
        sent = []
        self.assertEqual(codes.announce(state, fresh, "https://x.dev/", send=lambda t: sent.append(t) or True), 3)
        self.assertIn("BRANDNEW99", sent[0])
        self.assertIn("gift?code=BRANDNEW99", sent[0])
        state, fresh, _ = codes.update(state, later + timedelta(hours=4), fetcher(SERIA, more))
        self.assertEqual(fresh, [])

    def test_expired_and_failed_sources(self):
        state, _, _ = codes.update({}, NOW, fetcher(SERIA, ENNEAD))
        # Solo responde una fuente: lo que falta en ella no se da por vencido
        state, _, _ = codes.update(state, NOW + timedelta(hours=4), fetcher(SERIA, OSError("caída")))
        self.assertEqual(len(codes.active_codes(state, "genshin")), 2)
        # Las dos responden y una lo marca vencido
        gone = {"active": [{"code": "ABC123DEF"}], "inactive": [{"code": "SECOND2026"}]}
        state, _, _ = codes.update(state, NOW + timedelta(hours=8), fetcher(SERIA, gone))
        self.assertEqual([c["code"] for c in codes.active_codes(state, "genshin")], ["ABC123DEF"])
        # Ninguna responde: se conserva la lista
        state2, _, report = codes.update(state, NOW + timedelta(hours=12), fetcher(OSError(), OSError()))
        self.assertEqual(state2["games"]["genshin"], state["games"]["genshin"])
        self.assertIn("se conserva", report)

    def test_invalid_codes_are_dropped(self):
        a, _ = codes.from_seria({"codes": [{"code": "no vale", "status": "OK"}, {"code": "<script>", "status": "OK"}]})
        self.assertEqual(a, {})


if __name__ == "__main__":
    unittest.main()
