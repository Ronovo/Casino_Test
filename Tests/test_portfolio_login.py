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
from ronovo_portfolio_auth.security_questions import QUESTIONS

SECURITY_BODY = {"question": QUESTIONS[0], "answer": "rex"}

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = base64.b64encode(KEY.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)).decode()
PORTFOLIO_ENV = {"PORTFOLIO_SSO_URL": "http://portfolio.test", "PORTFOLIO_SSO_PUBLIC_KEY": PUBLIC_KEY}


def issue(sub, aud="casino", expires_in=300):
    now = int(time.time())
    return jwt.encode({"iss": "portfolio", "aud": aud, "sub": sub, "name": f"player{sub}", "iat": now,
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

    def start_portfolio_login(self):
        status, headers, _ = self.request("/sso/login")
        assert status == 303, status
        location = urlsplit(headers["Location"])
        query = parse_qs(location.query)
        assert f"{location.scheme}://{location.netloc}{location.path}" == "http://portfolio.test/sso/authorize"
        assert query["app"] == ["casino"] and query["return"] == [self.base + "/sso/callback"]
        return query["state"][0]

    def portfolio_login(self, sub, token=None):
        state = self.start_portfolio_login()
        return self.request("/sso/callback", "POST", form={"state": state, "token": token or issue(sub)})[0]


class PortfolioLoginTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, PORTFOLIO_ENV)
        env.start()
        self.addCleanup(env.stop)
        server = make_server(CasinoApp(self.db, load_games(TABLES_DIR)), "127.0.0.1", 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"

    def session(self, browser):
        return browser.request("/api/session")[2]

    def test_first_login_asks_before_making_an_account(self):
        phone = Browser(self.base)
        session = self.session(phone)
        self.assertTrue(session["portfolio"])
        self.assertEqual(session["portfolio_url"], "http://portfolio.test")
        self.assertEqual(phone.portfolio_login("1"), 303)
        session = self.session(phone)
        self.assertIsNone(session["user"])
        self.assertEqual(session["portfolio_pending"], "player1")

    def test_a_new_account_is_shared_by_every_device(self):
        phone = Browser(self.base)
        phone.portfolio_login("1")
        status, _, body = phone.request("/api/portfolio/new", "POST", {})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["user"], "player1")
        status, _, body = phone.request("/api/characters", "POST", {"name": "Lucky", "difficulty": "Medium"})
        self.assertEqual(status, 200, body)

        laptop = Browser(self.base)
        laptop.portfolio_login("1")
        session = self.session(laptop)
        self.assertEqual(session["user"], "player1")
        self.assertIsNone(session["portfolio_pending"])
        self.assertEqual([c["name"] for c in session["characters"]], ["Lucky"])

    def test_an_existing_account_can_be_linked_once(self):
        laptop = Browser(self.base)
        laptop.request("/api/register", "POST", {"username": "Gambler", "password": "hunter22", **SECURITY_BODY})
        laptop.request("/api/characters", "POST", {"name": "Lucky", "difficulty": "Medium"})

        phone = Browser(self.base)
        phone.portfolio_login("3")
        status, _, body = phone.request("/api/portfolio/link", "POST", {"username": "Gambler", "password": "wrong!"})
        self.assertEqual(status, 400)
        status, _, body = phone.request("/api/portfolio/link", "POST", {"username": "Gambler", "password": "hunter22"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["user"], "Gambler")

        tablet = Browser(self.base)
        tablet.portfolio_login("3")
        self.assertEqual([c["name"] for c in self.session(tablet)["characters"]], ["Lucky"])

        other = Browser(self.base)
        other.portfolio_login("4")
        status, _, body = other.request("/api/portfolio/link", "POST", {"username": "Gambler", "password": "hunter22"})
        self.assertEqual((status, body["error"]), (400, "That account is already linked to another portfolio account."))

    def test_a_taken_name_gets_a_number(self):
        Browser(self.base).request("/api/register", "POST", {"username": "player2", "password": "hunter22", **SECURITY_BODY})
        browser = Browser(self.base)
        browser.portfolio_login("2")
        self.assertEqual(browser.request("/api/portfolio/new", "POST", {})[2]["user"], "player22")

    def test_cancel_and_unknown_choices(self):
        browser = Browser(self.base)
        self.assertEqual(browser.request("/api/portfolio/new", "POST", {})[0], 400)
        browser.portfolio_login("5")
        browser.request("/api/logout", "POST", {})
        self.assertIsNone(self.session(browser)["portfolio_pending"])
        self.assertEqual(browser.request("/api/portfolio/new", "POST", {})[0], 400)

    def test_portfolio_accounts_have_no_usable_password(self):
        browser = Browser(self.base)
        browser.portfolio_login("6")
        browser.request("/api/portfolio/new", "POST", {})
        browser.request("/api/logout", "POST", {})
        self.assertEqual(browser.request("/api/login", "POST", {"username": "player6", "password": ""})[0], 400)

    def test_the_page_may_ask_the_portfolio_who_is_logged_in(self):
        _, headers, _ = Browser(self.base).request("/")
        self.assertIn("connect-src 'self' http://portfolio.test;", headers["Content-Security-Policy"])

    def test_bad_callbacks_are_refused(self):
        browser = Browser(self.base)
        browser.start_portfolio_login()
        self.assertEqual(browser.request("/sso/callback", "POST", form={"state": "wrong", "token": issue("1")})[0], 400)
        self.assertEqual(browser.portfolio_login("1", issue("1", aud="space-online")), 400)
        self.assertEqual(browser.portfolio_login("1", issue("1", expires_in=-10)), 400)
        session = self.session(browser)
        self.assertIsNone(session["user"])
        self.assertIsNone(session["portfolio_pending"])


class PortfolioOffTests(DatabaseTestCase):
    def test_portfolio_login_is_off_without_config(self):
        with mock.patch.dict(os.environ, {"PORTFOLIO_SSO_URL": "", "PORTFOLIO_SSO_PUBLIC_KEY": ""}):
            app = CasinoApp(self.db, load_games(TABLES_DIR))
            self.assertFalse(app.dispatch("GET", "session", {}, None).body["portfolio"])
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
