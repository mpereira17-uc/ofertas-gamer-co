import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from ogc import alerts

NOW = datetime(2026, 11, 19, 15, tzinfo=timezone.utc)
OFFERS = [
    {"id": "o1", "title": "Hollow Knight", "store": "Steam", "currentPrice": 4.99, "originalPrice": 14.99, "currency": "USD",
     "copApproximation": 15900, "discountPercentage": 67},
    {"id": "o2", "title": "Elden Ring", "store": "Steam", "currentPrice": 29.99, "originalPrice": 59.99, "currency": "USD",
     "copApproximation": 95400, "discountPercentage": 50},
]
GAMES = [{"id": "wd-Q1", "title": "Grand Theft Auto VI", "date": "2026-11-19", "precision": "day", "url": "https://es.wikipedia.org/wiki/GTA"}]


class FakeTelegram:
    def __init__(self, updates=()):
        self.updates, self.sent = list(updates), []

    def __call__(self, method, payload):
        if method == "getUpdates":
            return {"result": [u for u in self.updates if u["update_id"] >= payload["offset"]]}
        self.sent.append((payload["chat_id"], payload["text"]))
        return {"ok": True}


def msg(uid, chat, text, kind="private"):
    return {"update_id": uid, "message": {"chat": {"id": chat, "type": kind}, "text": text}}


class TestAlertas(unittest.TestCase):
    def test_cifrado(self):
        data = {"subs": {"123": [{"q": "zelda"}]}}
        blob = alerts.encrypt(data, "token-secreto")
        self.assertNotIn("123", blob)
        self.assertNotIn("zelda", blob)
        self.assertEqual(alerts.decrypt(blob, "token-secreto"), data)
        with self.assertRaises(ValueError):
            alerts.decrypt(blob, "otro-token")

    def test_texto(self):
        self.assertEqual(alerts.parse_alert("elden ring 50.000"), ("elden ring", 50000))
        self.assertEqual(alerts.parse_alert("hollow knight"), ("hollow knight", None))
        self.assertTrue(alerts.matches("hollow", "Hollow Knight: Silksong"))
        self.assertTrue(alerts.matches("pokémon", "Pokemon Legends"))
        self.assertFalse(alerts.matches("ring", "Ringo Starr"))

    def test_flujo_completo(self):
        tg = FakeTelegram([msg(1, 111, "/alerta hollow knight 20000"), msg(2, 111, "/alerta elden ring 50000"),
                           msg(3, 222, "/estreno grand theft auto"), msg(4, -5, "/alerta spam", "group")])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "alertas.enc")
            env = {"TELEGRAM_BOT_TOKEN": "t"}
            status = alerts.run(path, OFFERS, GAMES, lambda x: "https://sitio/" + x["id"], NOW, env, tg)
            self.assertIn("3 mensajes", status)
            texts = [t for c, t in tg.sent if c == 111]
            self.assertTrue(any("Hollow Knight" in t and "Bajó" in t for t in texts))  # 15.900 < 20.000
            self.assertFalse(any("Elden Ring</b> en" in t for t in texts))  # 95.400 > 50.000
            self.assertTrue(any("Hoy sale Grand Theft Auto VI" in t for c, t in tg.sent if c == 222))
            self.assertNotIn(-5, [c for c, _ in tg.sent])  # los grupos se ignoran
            with open(path) as fh:
                self.assertNotIn("111", fh.read())  # el archivo va cifrado
            before = len(tg.sent)
            alerts.run(path, OFFERS, GAMES, lambda x: "https://sitio/" + x["id"], NOW, env, tg)
            self.assertEqual(len(tg.sent), before)  # no repite avisos ni comandos

    def test_boton_de_la_pagina(self):
        tg = FakeTelegram([msg(1, 9, "/start o_" + alerts.short_id("o1"))])
        store = {"offset": 0, "subs": {}}
        al = alerts.Alerts(store, "t", OFFERS, GAMES, lambda x: "", NOW, tg)
        al.read_messages()
        self.assertEqual(store["subs"]["9"][0]["q"], "Hollow Knight")
        self.assertEqual(al.check(), 0)  # la oferta que ya vio no se repite

    def test_sin_token_no_hace_nada(self):
        self.assertEqual(alerts.run("/no/existe", [], [], None, NOW, env={}), "no configurado")


if __name__ == "__main__":
    unittest.main()
