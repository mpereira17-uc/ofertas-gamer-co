import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bot
from ogc import channels

FIX = str(Path(__file__).resolve().parent / "fixtures")


class TestBot(unittest.TestCase):
    def test_telegram_no_repite_ofertas(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sent = []
            with mock.patch.multiple(bot, DATA=tmp, OFFERS_FILE=tmp / "offers.json",
                                     PUBLISHED_FILE=tmp / "pub.json", DOCS=tmp / "docs"), \
                    mock.patch.object(channels, "send_telegram", side_effect=lambda o: sent.append(o["id"]) or True), \
                    mock.patch.object(channels, "send_discord", return_value=False):
                args = argparse.Namespace(fixtures=FIX, no_send=False)
                bot.run(args)
                first = list(sent)
                bot.run(args)
            self.assertTrue(first)
            self.assertEqual(sent, first, "la segunda ejecución no debe publicar nada")
            self.assertEqual(len(set(first)), len(first))
            data = json.loads((tmp / "offers.json").read_text())
            self.assertTrue(all(o["telegramPublishedAt"] for o in data["offers"]))
            self.assertTrue((tmp / "docs" / "whatsapp.html").exists())


if __name__ == "__main__":
    unittest.main()
