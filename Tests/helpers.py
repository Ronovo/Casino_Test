"""Shared test fixtures: a throwaway database, seeded sessions and stacked shoes."""
from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

import casino.accounts
from casino.accounts import Accounts
from casino.config import ACHIEVEMENTS_PATH, TABLES_DIR, load_starting_chips
from casino.engine.cards import Shoe
from casino.engine.chips import Chips
from casino.engine.db import Database
from casino.engine.game import Game, Round, TableConfig
from casino.engine.session import Session
from casino.engine.wallet import Wallet
from ronovo_portfolio_auth.security_questions import QUESTIONS

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
        self.db_path = Path(self._tmp.name) / "test.db"
        self.db = Database(self.db_path, durable=False)
        self.db.initialize(ACHIEVEMENTS_PATH)
        self.owner = self.db.create_user("test-owner", "unused")

    def tearDown(self) -> None:
        # On Windows this fails if any connection was left open, which doubles as a leak check.
        self._tmp.cleanup()

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
