import unittest
from datetime import datetime, timezone

from ogc import trailers

NOW = datetime(2026, 10, 27, 1, 0, tzinfo=timezone.utc)
MOVIE = {"movies": [{"name": "Tráiler", "thumbnail": "https://x/p.jpg", "hls_h264": "https://video.akamai.steamstatic.com/a/hls.m3u8"}]}


class TrailersTest(unittest.TestCase):
    def test_usa_calendario_y_pide_lo_que_falta(self):
        offers = [{"id": "a", "steamAppID": 10}, {"id": "b", "steamAppID": 20}, {"id": "c"}]
        games = [{"id": "steam-10", "trailer": {"hls": "https://v/10.m3u8"}, "verifiedAt": "2026-10-26T00:00:00Z"}]
        asked = []

        def fetch(url):
            asked.append(url)
            return {"20": {"success": True, "data": dict(MOVIE, type="game")}}

        cache, status = trailers.update(offers, games, {}, NOW, fetch)
        self.assertEqual(len(asked), 1)
        self.assertIn("appids=20", asked[0])
        out = trailers.attach([dict(o) for o in offers], cache)
        self.assertEqual(out[0]["trailer"]["hls"], "https://v/10.m3u8")
        self.assertTrue(out[1]["trailer"]["hls"].endswith("hls.m3u8"))
        self.assertNotIn("trailer", out[2])
        self.assertIn("2 ofertas con tráiler", status)

    def test_no_repite_y_tolera_fallos(self):
        offers = [{"id": "a", "steamAppID": 30}]
        cache, _ = trailers.update(offers, [], {"30": {"trailer": {}, "at": "2026-10-20T00:00:00Z"}}, NOW,
                                   lambda url: self.fail("no debía pedir"))
        self.assertIn("30", cache)

        def broken(url):
            raise OSError("caído")
        cache, status = trailers.update([{"id": "b", "steamAppID": 40}], [], {}, NOW, broken)
        self.assertNotIn("40", cache)
        self.assertIn("1 fallaron", status)


if __name__ == "__main__":
    unittest.main()
