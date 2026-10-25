import json
import unittest
from unittest import mock

from ogc import tumblr

ENV = {"TUMBLR_BLOG": "ofertasgamerco", "TUMBLR_CONSUMER_KEY": "ck", "TUMBLR_CONSUMER_SECRET": "cs",
       "TUMBLR_TOKEN": "tk", "TUMBLR_TOKEN_SECRET": "ts"}


class TumblrTest(unittest.TestCase):
    def test_sin_claves_no_publica(self):
        self.assertFalse(tumblr.ready({}))
        self.assertFalse(tumblr.post("t", "https://x", "T", "d", env={"TUMBLR_BLOG": "x"}))

    def test_nombre_del_blog(self):
        self.assertEqual(tumblr.blog({"TUMBLR_BLOG": "ofertasgamerco"}), "ofertasgamerco.tumblr.com")
        self.assertEqual(tumblr.blog({"TUMBLR_BLOG": "https://ofertasgamerco.tumblr.com/"}), "ofertasgamerco.tumblr.com")

    def test_firma_estable(self):
        a = tumblr.oauth_header("POST", "https://api.tumblr.com/v2/blog/b/posts", "ck", "cs", "tk", "ts", "n", 1)
        b = tumblr.oauth_header("POST", "https://api.tumblr.com/v2/blog/b/posts", "ck", "cs", "tk", "ts", "n", 1)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("OAuth ") and "oauth_signature=" in a and "cs" not in a.split("oauth_signature")[0].replace("oauth_consumer_key", ""))

    def test_publica_npf(self):
        sent = {}

        class Resp:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake(req, timeout=0):
            sent["url"], sent["body"] = req.full_url, json.loads(req.data)
            return Resp()
        with mock.patch("urllib.request.urlopen", fake):
            self.assertTrue(tumblr.post("🎁 GRATIS", "https://sitio/o.html", "Juego", "Gratis", "https://img/x.jpg", env=ENV))
        self.assertIn("ofertasgamerco.tumblr.com/posts", sent["url"])
        self.assertEqual([c["type"] for c in sent["body"]["content"]], ["image", "text", "link"])


if __name__ == "__main__":
    unittest.main()
