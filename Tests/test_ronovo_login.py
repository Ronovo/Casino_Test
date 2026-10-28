import base64
import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from casino.config import TABLES_DIR
from casino.games import load_games
from casino.web.server import CasinoApp, make_server
from Tests.helpers import DatabaseTestCase
from casino.security_questions import QUESTIONS

SECURITY = (QUESTIONS[0], "rex")
SECURITY_BODY = {"question": QUESTIONS[0], "answer": "rex"}

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = base64.b64encode(KEY.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)).decode()
RONOVO_ENV = {"RONOVO_SSO_URL": "http://ronovo.test", "RONOVO_SSO_PUBLIC_KEY": PUBLIC_KEY}


def issue(sub, aud="casino", expires_in=300):
    now = int(time.time())
    return jwt.encode({"iss": "ronovo", "aud": aud, "sub": sub, "name": f"player{sub}", "iat": now,
                       "exp": now + expires_in}, KEY, algorithm="RS256")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Browser:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), NoRedirect)

    def request(self, path, method="GET", json_body=None, form=None):
        """Status, headers and decoded JSON body (or None), without following redirects."""
        data, headers = None, {}
        if json_body is not None:
            data, headers = json.dumps(json_body).encode(), {"Content-Type": "application/json"}
        if form is not None:
            data, headers = urlencode(form).encode(), {"Content-Type": "application/x-www-form-urlencoded"}
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(req)
        except urllib.error.HTTPError as error:
            response = error
        body = response.read()
        is_json = response.headers.get("Content-Type", "").startswith("application/json")
        return response.status, response.headers, json.loads(body) if is_json else None

    def start_ronovo_login(self):
        status, headers, _ = self.request("/sso/login")
        assert status == 303, status
        location = urlsplit(headers["Location"])
        query = parse_qs(location.query)
        assert f"{location.scheme}://{location.netloc}{location.path}" == "http://ronovo.test/sso/authorize"
        assert query["app"] == ["casino"] and query["return"] == [self.base + "/sso/callback"]
        return query["state"][0]

    def ronovo_login(self, sub, token=None):
        state = self.start_ronovo_login()
        return self.request("/sso/callback", "POST", form={"state": state, "token": token or issue(sub)})[0]


class RonovoLoginTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, RONOVO_ENV)
        env.start()
        self.addCleanup(env.stop)
        server = make_server(CasinoApp(self.db, load_games(TABLES_DIR)), "127.0.0.1", 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"

    def session(self, browser):
        return browser.request("/api/session")[2]

    def test_first_login_makes_an_account_that_every_device_shares(self):
        phone = Browser(self.base)
        self.assertTrue(self.session(phone)["ronovo"])
        self.assertEqual(phone.ronovo_login("1"), 303)
        self.assertEqual(self.session(phone)["user"], "player1")
        status, _, body = phone.request("/api/characters", "POST", {"name": "Lucky", "difficulty": "Medium"})
        self.assertEqual(status, 200, body)

        laptop = Browser(self.base)
        laptop.ronovo_login("1")
        session = self.session(laptop)
        self.assertEqual(session["user"], "player1")
        self.assertEqual([c["name"] for c in session["characters"]], ["Lucky"])

    def test_a_taken_name_gets_a_number(self):
        Browser(self.base).request("/api/register", "POST", {"username": "player2", "password": "hunter22", **SECURITY_BODY})
        browser = Browser(self.base)
        browser.ronovo_login("2")
        self.assertEqual(self.session(browser)["user"], "player22")

    def test_ronovo_accounts_have_no_usable_password(self):
        browser = Browser(self.base)
        browser.ronovo_login("4")
        browser.request("/api/logout", "POST", {})
        self.assertEqual(browser.request("/api/login", "POST", {"username": "player4", "password": ""})[0], 400)

    def test_bad_callbacks_are_refused(self):
        browser = Browser(self.base)
        browser.start_ronovo_login()
        self.assertEqual(browser.request("/sso/callback", "POST", form={"state": "wrong", "token": issue("1")})[0], 400)
        self.assertEqual(browser.ronovo_login("1", issue("1", aud="space-online")), 400)
        self.assertEqual(browser.ronovo_login("1", issue("1", expires_in=-10)), 400)
        self.assertIsNone(self.session(browser)["user"])


class RonovoOffTests(DatabaseTestCase):
    def test_ronovo_login_is_off_without_config(self):
        with mock.patch.dict(os.environ, {"RONOVO_SSO_URL": "", "RONOVO_SSO_PUBLIC_KEY": ""}):
            app = CasinoApp(self.db, load_games(TABLES_DIR))
            self.assertFalse(app.dispatch("GET", "session", {}, None).body["ronovo"])
            server = make_server(app, "127.0.0.1", 0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                browser = Browser(f"http://127.0.0.1:{server.server_address[1]}")
                self.assertEqual(browser.request("/sso/login")[0], 404)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
