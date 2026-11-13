import unittest
from datetime import datetime, timezone

from ogc import gamepass

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
SIGL = [{"siglId": "x", "title": "Agregados recientemente"}, {"id": "9MTGCZ84M503"}, {"id": "9NWWL1CBWFCG"}, {"id": "<script>"}]


def product(pid, title, poster="//store-images.s-microsoft.com/image/apps.1.poster"):
    return {"ProductId": pid, "LocalizedProperties": [{"ProductTitle": title, "PublisherName": "Estudio",
            "Images": [{"ImagePurpose": "Poster", "Uri": poster}]}]}


def fetcher(products, all_pc=None):
    def fetch(url):
        if "displaycatalog" in url:
            return {"Products": products}
        if "609d944c" in url:
            return all_pc if all_pc is not None else [{"siglId": "y"}] + [{"id": f"9ABCDEFGH{i:03d}"} for i in range(400)]
        return SIGL
    return fetch


class GamePassTest(unittest.TestCase):
    def test_lista_recientes_con_poster_y_enlace_oficial(self):
        state, status = gamepass.update({}, NOW, fetcher([product("9MTGCZ84M503", "Toxic Commando"), product("9NWWL1CBWFCG", "Thronefall")]))
        self.assertEqual([g["title"] for g in state["recent"]], ["Toxic Commando", "Thronefall"])
        self.assertEqual(state["recent"][0]["poster"], "https://store-images.s-microsoft.com/image/apps.1.poster?w=300")
        self.assertEqual(state["recent"][0]["url"], "https://www.microsoft.com/es-co/p/x/9MTGCZ84M503")
        self.assertEqual(state["total"], 400)
        self.assertIn("2 recientes", status)

    def test_primera_revision_no_marca_nuevos_y_despues_si(self):
        state, _ = gamepass.update({}, NOW, fetcher([product("9MTGCZ84M503", "Toxic Commando")]))
        self.assertIsNone(state["firstSeen"]["9MTGCZ84M503"])
        later, _ = gamepass.update(state, NOW, fetcher([product("9MTGCZ84M503", "Toxic Commando"), product("9NWWL1CBWFCG", "Thronefall")]))
        self.assertIsNone(later["firstSeen"]["9MTGCZ84M503"])
        self.assertEqual(later["firstSeen"]["9NWWL1CBWFCG"], "2026-11-13T12:00:00Z")

    def test_imagen_de_otro_dominio_se_descarta(self):
        state, _ = gamepass.update({}, NOW, fetcher([product("9MTGCZ84M503", "A", poster="https://evil.example/x.png"),
                                                     product("9NWWL1CBWFCG", "B")]))
        self.assertEqual([g["id"] for g in state["recent"]], ["9NWWL1CBWFCG"])

    def test_si_falla_conserva_lo_anterior(self):
        old = {"recent": [{"id": "1"}], "total": 5}

        def broken(url):
            raise OSError("caído")
        state, status = gamepass.update(old, NOW, broken)
        self.assertIs(state, old)
        self.assertIn("Falló", status)


if __name__ == "__main__":
    unittest.main()
