import unittest
from datetime import datetime, timezone

from ogc import userreviews

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
DATA = {"success": 1, "reviews": [
    {"review": "[h1]Excelente[/h1] Un juego <b>increíble</b> con mucha historia y combates muy buenos, lo recomiendo. https://spam.example", "voted_up": True,
     "votes_up": 12, "timestamp_created": 1763900000, "author": {"steamid": "765611", "playtime_forever": 1250}},
    {"review": "malo", "voted_up": False, "votes_up": 99, "author": {"playtime_forever": 10}},
    {"review": "No me gustó para nada, se cierra solo y el rendimiento es muy malo en mi PC de gama media.", "voted_up": False,
     "votes_up": 40, "timestamp_created": 1760000000, "author": {"playtime_forever": 90}},
]}


class ResenasTest(unittest.TestCase):
    def test_limpia_ordena_y_no_guarda_nombres(self):
        cache, status = userreviews.update([{"id": "a", "steamAppID": 10}], {}, NOW, lambda url: DATA)
        items = cache["10"]["items"]
        self.assertEqual(len(items), 2)  # la reseña de una palabra se descarta
        self.assertFalse(items[0]["up"])  # la más votada como útil va primero
        self.assertEqual(items[1]["hours"], 21)
        self.assertNotIn("[h1]", items[1]["text"])
        self.assertNotIn("<b>", items[1]["text"])
        self.assertNotIn("spam.example", items[1]["text"])
        self.assertNotIn("steamid", str(items))
        out = userreviews.attach([{"id": "a", "steamAppID": 10}], cache)
        self.assertEqual(len(out[0]["userReviews"]), 2)
        self.assertIn("OK", status)

    def test_si_steam_redirige_no_se_publica_nada_y_para_de_insistir(self):
        asked = []

        def broken(url):
            asked.append(url)
            raise ValueError("redirige a la portada")
        offers = [{"id": str(i), "steamAppID": i} for i in range(1, 30)]
        cache, status = userreviews.update(offers, {}, NOW, broken)
        self.assertEqual(len(asked), userreviews.MAX_FAILS)
        self.assertEqual(cache, {})
        self.assertIn("Sin respuesta", status)
        self.assertNotIn("userReviews", userreviews.attach(offers, cache)[0])

    def test_respuesta_sin_exito_no_cuenta(self):
        cache, _ = userreviews.update([{"id": "a", "steamAppID": 5}], {}, NOW, lambda url: {"success": 2})
        self.assertNotIn("5", cache)


if __name__ == "__main__":
    unittest.main()
