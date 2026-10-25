import unittest

from scripts import discord_setup


class FakeDiscord:
    def __init__(self, channels=()):
        self.channels = list(channels)
        self.messages = {}
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and path.endswith("/channels"):
            return self.channels
        if method == "POST" and path.endswith("/channels"):
            chan = dict(payload, id=str(len(self.channels) + 100))
            self.channels.append(chan)
            return chan
        cid = path.split("/")[2]
        if method == "GET":
            return [dict(m, id="m", author={"bot": True}) for m in self.messages.get(cid, [])]
        if method == "PATCH":
            return {}
        self.messages.setdefault(cid, []).append(payload)
        return {}


class TestDiscordSetup(unittest.TestCase):
    def test_crea_todo_y_no_repite(self):
        fake = FakeDiscord()
        created, posted, ids = discord_setup.setup("t", "1", api=fake)
        self.assertIn("🔥・ofertas", created)
        self.assertEqual(len(posted), 3)
        ofertas = next(c for c in fake.channels if c["name"] == "🔥・ofertas")
        self.assertEqual(ofertas["permission_overwrites"][0]["id"], "1")
        welcome = fake.messages[ids["👋・bienvenida"]][0]["embeds"][0]["description"]
        self.assertIn(f"<#{ids['🔥・ofertas']}>", welcome)
        self.assertNotIn("<#ofertas>", welcome)
        self.assertIn("discord-banner.png", fake.messages[ids["👋・bienvenida"]][0]["embeds"][0]["image"]["url"])

        again = discord_setup.setup("t", "1", api=fake)
        self.assertEqual(again[:2], ([], []))
        self.assertFalse([c for c in fake.calls if c[0] in ("DELETE", "PUT")])  # nunca borra

    def test_imagenes_del_bot(self):
        calls = []

        def api(method, path, token, payload=None):
            calls.append((method, path, payload))
            return {"avatar": None, "banner": None} if path == "/users/@me" else {"icon": "x", "features": []}
        done = discord_setup.branding("t", "1", api)
        self.assertEqual(done, ["foto y banner del bot"])
        patch = next(c for c in calls if c[0] == "PATCH")
        self.assertTrue(patch[2]["avatar"].startswith("data:image/png;base64,"))



if __name__ == "__main__":
    unittest.main()
