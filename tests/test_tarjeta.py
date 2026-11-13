import re
import unittest

from ogc.site import Site

STORES = {"steam": {"id": "steam", "name": "Steam", "active": True}}


def site():
    s = Site({"url_web": "https://ejemplo.dev/", "nombre": "Ofertas Gamer CO"}, STORES, {"ads_enabled": False, "slots": []}, "salida-prueba")
    s.rate = 3300
    return s


USD = {"id": "cs-1", "title": "Juego <b>raro</b>", "store": "Steam", "storeId": "steam", "currency": "USD", "currentPrice": 2.49,
       "originalPrice": 24.99, "discountPercentage": 90, "copApproximation": 8217, "image": "https://shared.fastly.steamstatic.com/h.jpg",
       "capsule": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1/library_600x900.jpg", "destinationUrl": "https://store.steampowered.com/app/1/",
       "status": "Disponible", "regions": []}


class TarjetaCajaTest(unittest.TestCase):
    def test_caja_con_portada_vertical_lomo_y_sticker(self):
        html = site().card(USD)
        self.assertIn('class="box store-steam tilt-', html)
        self.assertIn('src="https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1/library_600x900.jpg"', html)
        self.assertIn('data-fallback="https://shared.fastly.steamstatic.com/h.jpg"', html)
        self.assertIn('<span class="sticker">-90%</span>', html)
        self.assertNotIn("no-capsule", html)
        self.assertNotIn("<b>raro</b>", html)  # el título siempre va escapado

    def test_pesos_primero_con_aprox_y_precio_de_la_tienda_debajo(self):
        html = site().card(USD)
        self.assertRegex(html, r'<span class="now">\$8\.200 <small>aprox\.</small></span>')
        self.assertIn('<p class="store-price">US$2.49 en Steam <s>US$24.99</s></p>', html)

    def test_precio_en_pesos_exacto_sin_aprox(self):
        cop = dict(USD, id="ep-1", currency="COP", currentPrice=15999, originalPrice=31999, copApproximation=None, storeId="epic", store="Epic Games Store")
        html = site().card(cop)
        self.assertIn('<span class="now">$15.999 COP</span>', html)
        self.assertNotIn("aprox.", html.split('class="pricebox"')[1].split("</div>")[0])

    def test_sin_portada_vertical_usa_la_horizontal_con_el_nombre(self):
        html = site().card(dict(USD, capsule=None))
        self.assertIn("box store-steam tilt-", html)
        self.assertIn("no-capsule", html)
        self.assertIn('<span class="box-name" aria-hidden="true">Juego &lt;b&gt;raro&lt;/b&gt;</span>', html)

    def test_gratis_y_ganga(self):
        s = site()
        s.ganga = {"cs-1"}
        html = s.card(USD)
        self.assertIn('<span class="seal ganga">GANGA</span>', html)
        free = s.card(dict(USD, id="f", currentPrice=0, discountPercentage=100))
        self.assertIn('<span class="sticker free">GRATIS</span>', free)
        self.assertNotIn("GANGA", free)

    def test_inclinacion_fija_por_juego(self):
        a, b = site().card(USD), site().card(USD)
        self.assertEqual(re.search(r"tilt-\d", a).group(0), re.search(r"tilt-\d", b).group(0))

    def test_conserva_datos_para_filtros_y_sin_fecha_de_fin(self):
        html = site().card(USD)
        for attr in ("data-id=", "data-store=", "data-discount=", "data-cop=", "data-score="):
            self.assertIn(attr, html)
        self.assertIn("Sin fecha de fin", html)


if __name__ == "__main__":
    unittest.main()
