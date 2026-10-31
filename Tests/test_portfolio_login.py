import base64
import os
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from casino.config import TABLES_DIR
from casino.games import load_games
from casino.web.server import CasinoApp
from Tests.helpers import SECURITY_BODY, Browser, DatabaseTestCase, serve_in_background


KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = base64.b64encode(KEY.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)).decode()
PORTFOLIO_ENV = {"PORTFOLIO_SSO_URL": "http://portfolio.test", "PORTFOLIO_SSO_PUBLIC_KEY": PUBLIC_KEY}


def issue(sub, aud="casino", expires_in=300):
    now = int(time.time())
    return jwt.encode({"iss": "portfolio", "aud": aud, "sub": sub, "name": f"player{sub}", "iat": now,
                       "exp": now + expires_in}, KEY, algorithm="RS256")


class PortfolioBrowser(Browser):
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
        self.base = serve_in_background(self, CasinoApp(self.db, load_games(TABLES_DIR)))

    def session(self, browser):
        return browser.request("/api/session")[2]

    def test_the_callback_keeps_the_scheme_of_the_app_address(self):
        location, _ = CasinoApp(self.db, load_games(TABLES_DIR)).portfolio_authorize_url("https://casino.ronovo.io/")
        self.assertEqual(parse_qs(urlsplit(location).query)["return"], ["https://casino.ronovo.io/sso/callback"])

    def test_first_login_asks_before_making_an_account(self):
        phone = PortfolioBrowser(self.base)
        session = self.session(phone)
        self.assertTrue(session["portfolio"])
        self.assertEqual(session["portfolio_url"], "http://portfolio.test")
        self.assertEqual(phone.portfolio_login("1"), 303)
        session = self.session(phone)
        self.assertIsNone(session["user"])
        self.assertEqual(session["portfolio_pending"], "player1")

    def test_a_new_account_is_shared_by_every_device(self):
        phone = PortfolioBrowser(self.base)
        phone.portfolio_login("1")
        status, _, body = phone.request("/api/portfolio/new", "POST", {})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["user"], "player1")
        status, _, body = phone.request("/api/characters", "POST", {"name": "Lucky", "difficulty": "Medium"})
        self.assertEqual(status, 200, body)

        laptop = PortfolioBrowser(self.base)
        laptop.portfolio_login("1")
        session = self.session(laptop)
        self.assertEqual(session["user"], "player1")
        self.assertIsNone(session["portfolio_pending"])
        self.assertEqual([c["name"] for c in session["characters"]], ["Lucky"])

    def test_an_existing_account_can_be_linked_once(self):
        laptop = PortfolioBrowser(self.base)
        laptop.request("/api/register", "POST", {"username": "Gambler", "password": "hunter22", **SECURITY_BODY})
        laptop.request("/api/characters", "POST", {"name": "Lucky", "difficulty": "Medium"})

        phone = PortfolioBrowser(self.base)
        phone.portfolio_login("3")
        status, _, body = phone.request("/api/portfolio/link", "POST", {"username": "Gambler", "password": "wrong!"})
        self.assertEqual(status, 400)
        status, _, body = phone.request("/api/portfolio/link", "POST", {"username": "Gambler", "password": "hunter22"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["user"], "Gambler")

        tablet = PortfolioBrowser(self.base)
        tablet.portfolio_login("3")
        self.assertEqual([c["name"] for c in self.session(tablet)["characters"]], ["Lucky"])

        other = PortfolioBrowser(self.base)
        other.portfolio_login("4")
        status, _, body = other.request("/api/portfolio/link", "POST", {"username": "Gambler", "password": "hunter22"})
        self.assertEqual((status, body["error"]), (400, "That account is already linked to another portfolio account."))

    def test_a_taken_name_gets_a_number(self):
        PortfolioBrowser(self.base).request("/api/register", "POST", {"username": "player2", "password": "hunter22", **SECURITY_BODY})
        browser = PortfolioBrowser(self.base)
        browser.portfolio_login("2")
        self.assertEqual(browser.request("/api/portfolio/new", "POST", {})[2]["user"], "player22")

    def test_cancel_and_unknown_choices(self):
        browser = PortfolioBrowser(self.base)
        self.assertEqual(browser.request("/api/portfolio/new", "POST", {})[0], 400)
        browser.portfolio_login("5")
        browser.request("/api/logout", "POST", {})
        self.assertIsNone(self.session(browser)["portfolio_pending"])
        self.assertEqual(browser.request("/api/portfolio/new", "POST", {})[0], 400)

    def test_portfolio_accounts_have_no_usable_password(self):
        browser = PortfolioBrowser(self.base)
        browser.portfolio_login("6")
        browser.request("/api/portfolio/new", "POST", {})
        browser.request("/api/logout", "POST", {})
        self.assertEqual(browser.request("/api/login", "POST", {"username": "player6", "password": ""})[0], 400)

    def test_the_page_may_ask_the_portfolio_who_is_logged_in(self):
        _, headers, _ = PortfolioBrowser(self.base).request("/")
        self.assertIn("connect-src 'self' http://portfolio.test;", headers["Content-Security-Policy"])

    def test_bad_callbacks_are_refused(self):
        browser = PortfolioBrowser(self.base)
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
            self.assertEqual(Browser(serve_in_background(self, app)).request("/sso/login")[0], 404)


if __name__ == "__main__":
    unittest.main()
