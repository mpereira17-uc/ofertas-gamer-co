import unittest

from ogc import discord
from ogc.channels import price_line
from ogc.releases import date_label

OFFERS = [{"id": f"o{i}", "title": f"Juego {i}", "store": "Steam", "currentPrice": 0 if i < 2 else 5, "originalPrice": 20,
           "discountPercentage": 75, "currency": "USD", "copApproximation": None, "affiliate": False,
           "image": "https://img/x.jpg"} for i in range(30)]
GAMES = [{"id": f"g{i}", "title": f"Nuevo {i}", "date": f"2030-01-{i + 1:02d}", "precision": "day", "comingSoon": True,
          "genres": ["Acción"], "image": "https://img/g.jpg"} for i in range(5)]


class FakeApi:
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, payload=None, token=None):
        self.calls.append((method, url, payload))
        if method == "GET":
            return [{"id": "10", "type": 0, "name": "🔥・ofertas"}, {"id": "11", "type": 0, "name": "🎁・juegos-gratis"},
                    {"id": "12", "type": 0, "name": "📅・lanzamientos"}, {"id": "13", "type": 4, "name": "🎮 OFERTAS"}]
        return {}


class TestDiscord(unittest.TestCase):
    def run_publish(self, history, api):
        dc = discord.Discord(env={"DISCORD_BOT_TOKEN": "t"}, guild="1", request=api)
        return discord.publish(dc, OFFERS, GAMES, lambda x: f"https://x/{x['id']}.html", history, 3, price_line, date_label)

    def test_primera_vez_publica_lo_existente_y_luego_solo_lo_nuevo(self):
        api, history = FakeApi(), {}
        counts = self.run_publish(history, api)
        self.assertEqual(counts, {"gratis": 2, "ofertas": 28, "lanzamientos": 5})
        posts = [c for c in api.calls if c[0] == "POST"]
        self.assertTrue(all(len(p[2]["embeds"]) <= 10 for p in posts))
        self.assertEqual({p[1].split("/")[-2] for p in posts}, {"10", "11", "12"})
        self.assertEqual(posts[0][2]["embeds"][0]["image"]["url"], "https://img/x.jpg")
        again = self.run_publish(history, FakeApi())
        self.assertEqual(again, {"gratis": 0, "ofertas": 0, "lanzamientos": 0})

    def test_sin_configuracion_no_hace_nada(self):
        self.assertFalse(discord.Discord(env={}, guild="1").ready)
        self.assertFalse(discord.Discord(env={"DISCORD_WEBHOOK_URL": "https://evil.example/x"}, guild="1").ready)
        self.assertFalse(discord.Discord(env={"DISCORD_BOT_TOKEN": "t"}, guild="").ready)


if __name__ == "__main__":
    unittest.main()
