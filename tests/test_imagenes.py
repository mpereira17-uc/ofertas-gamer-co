import unittest

from ogc.site import light_image, light_images


class ImagenesLivianasTest(unittest.TestCase):
    def test_epic_se_pide_redimensionada(self):
        url = "https://cdn1.epicgames.com/spt-assets/abc/juego.png"
        self.assertEqual(light_image(url), url + "?resize=1&w=920")

    def test_otras_tiendas_no_cambian(self):
        url = "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1/header.jpg"
        self.assertEqual(light_image(url), url)

    def test_no_duplica_parametros_ni_acepta_http(self):
        con_query = "https://cdn1.epicgames.com/x.png?h=480"
        self.assertEqual(light_image(con_query), con_query)
        self.assertEqual(light_image("http://cdn1.epicgames.com/x.png"), "http://cdn1.epicgames.com/x.png")
        self.assertEqual(light_image(""), "")

    def test_no_modifica_los_datos_originales(self):
        datos = [{"id": "a", "image": "https://cdn1.epicgames.com/x.png"}, {"id": "b"}]
        copia = light_images(datos)
        self.assertEqual(datos[0]["image"], "https://cdn1.epicgames.com/x.png")
        self.assertTrue(copia[0]["image"].endswith("?resize=1&w=920"))
        self.assertIs(copia[1], datos[1])


if __name__ == "__main__":
    unittest.main()
