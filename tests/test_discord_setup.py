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
            return self.messages.get(cid, [])
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

        again = discord_setup.setup("t", "1", api=fake)
        self.assertEqual(again[:2], ([], []))
        self.assertFalse([c for c in fake.calls if c[0] not in ("GET", "POST")])  # nunca borra ni edita


if __name__ == "__main__":
    unittest.main()
