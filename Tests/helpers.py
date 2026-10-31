"""Shared test fixtures: a throwaway database, seeded sessions, stacked shoes, a seated player and a real server."""
from __future__ import annotations

import json
import random
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode

from ronovo_portfolio_auth.security_questions import QUESTIONS

import casino.accounts
from casino.accounts import Accounts
from casino.config import ACHIEVEMENTS_PATH, TABLES_DIR, load_starting_chips
from casino.engine.cards import Shoe
from casino.engine.chips import Chips
from casino.engine.db import Character, Database
from casino.engine.game import Game, Round, TableConfig
from casino.engine.session import Session
from casino.engine.wallet import Wallet
from casino.games import load_games
from casino.web.floor import Floor, Seat
from casino.web.server import CasinoApp, make_server

# The real hashing cost would make every sign-up in the tests take a noticeable moment.
casino.accounts.PBKDF2_ROUNDS = 1_000

SECURITY = (QUESTIONS[0], "rex")
SECURITY_BODY = {"question": QUESTIONS[0], "answer": "rex"}


def login(accounts: Accounts, username: str, password: str) -> str:
    """A login token, the way the server makes one."""
    return accounts.issue_token(accounts.authenticate(username, password))


def table(filename: str) -> TableConfig:
    return TableConfig.from_file(TABLES_DIR / filename)


def play(game: Game, session: Session, bets: dict, *actions: str) -> Round:
    """Start a round, make the given moves and check that the round ended with them."""
    current = game.start(session, bets)
    for action in actions:
        current.act(action)
    assert current.finished, f"round still waiting for one of {[a['id'] for a in current.actions()]}"
    return current


def serve_in_background(test: unittest.TestCase, app: CasinoApp) -> str:
    """Serve the app on a free port until the test ends, and return its address."""
    server = make_server(app, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    test.addCleanup(server.server_close)
    test.addCleanup(server.shutdown)
    return f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Browser:
    """Keeps cookies like a browser, but doesn't follow redirects."""

    def __init__(self, base: str):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), NoRedirect)

    def request(self, path, method=None, json_body=None, form=None, raw=None, headers=None):
        """Status, headers and body, decoded when it is JSON. Bodies are sent as JSON unless they are a form."""
        data, content_type = raw, "application/json"
        if json_body is not None:
            data = json.dumps(json_body).encode()
        if form is not None:
            data, content_type = urlencode(form).encode(), "application/x-www-form-urlencoded"
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers=headers or {"Content-Type": content_type})
        try:
            response = self.opener.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read()
        if response.headers.get("Content-Type", "").startswith("application/json"):
            body = json.loads(body)
        return response.status, response.headers, body


class FixedRng(random.Random):
    """Returns a fixed value from randint/choice so number games are deterministic."""

    def __init__(self, value):
        super().__init__(0)
        self.value = value

    def randint(self, a, b):
        return self.value

    def choice(self, seq):
        if self.value not in seq:
            raise ValueError(f"{self.value!r} is not a valid choice")
        return self.value


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        # On Windows this fails if any connection was left open, which doubles as a leak check.
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / "test.db"
        self.db = Database(self.db_path, durable=False)
        self.db.initialize(ACHIEVEMENTS_PATH)
        self.owner = self.db.create_user("test-owner", "unused")

    def make_session(self, credits: int | None = 1000, cards=None, rng=None,
                     difficulty: str = "Medium", name: str = "Tester") -> Session:
        chips = load_starting_chips(difficulty) if credits is None else Chips.make_change(credits)
        character = self.db.create_character(name, difficulty, chips, self.owner.id)
        session = Session(self.db, character, Wallet.load(self.db, character.id), rng=rng or random.Random(0))
        if cards is not None:
            session.shoe_factory = lambda decks: Shoe.stacked(cards)
        return session

    def unlocked(self, session: Session) -> set[str]:
        return {a.name for a in self.db.achievements(session.character.id) if a.unlocked}


class AppTestCase(DatabaseTestCase):
    """A CasinoApp with seeded randomness and one logged-in, seated player."""

    def setUp(self):
        super().setUp()
        self.games = load_games(TABLES_DIR)
        self.app = CasinoApp(self.db, self.games, Floor(self.db, self.games, rng_factory=lambda: random.Random(7)))
        self.token = self.signup("Ronovo", "Ronovo Ronove", "Medium")

    def signup(self, username, character, difficulty):
        token = self.app.dispatch("POST", "register", {"username": username, "password": "hunter22", **SECURITY_BODY}, None).token
        reply = self.app.dispatch("POST", "characters", {"name": character, "difficulty": difficulty}, token)
        self.assertEqual(reply.status, 200, reply.body)
        return token

    def call(self, method, path, data=None, token="default", status=200):
        reply = self.app.dispatch(method, path, data or {}, self.token if token == "default" else token)
        self.assertEqual(reply.status, status, reply.body)
        return reply.body

    def character(self) -> Character:
        """The seated player's character."""
        return self.db.list_characters(self.app.accounts.resolve(self.token)[0].id)[0]

    def seat(self) -> Seat:
        return self.app.floor.seat(self.character())

    def stack(self, cards):
        self.seat().session.shoe_factory = lambda decks: Shoe.stacked(cards)
