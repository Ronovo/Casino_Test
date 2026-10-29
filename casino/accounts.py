"""Player accounts: registration, password checks, login tokens and the characters an account owns."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from collections import deque

from ronovo_portfolio_auth import security_questions
from ronovo_portfolio_auth.login_limiter import LockedOut, LoginLimiter

from casino.config import DIFFICULTIES, load_starting_chips
from casino.engine.bets import is_whole
from casino.engine.db import Character, Database, DuplicateCharacter, DuplicateUser, User

PBKDF2_ROUNDS = 600_000
LOGIN_LIFETIME = 60 * 60 * 24 * 30
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,20}")
MIN_PASSWORD, MAX_PASSWORD = 6, 128
MAX_CHARACTER_NAME = 30
MAX_CHARACTERS = 8
PORTFOLIO_CHOICE_SECONDS = 600
REGISTRATION_WINDOW_SECONDS = 600
MAX_REGISTRATIONS = 20
NO_ACCOUNT = "There is no account with that username."


class AccountError(ValueError):
    """A sign-up, login or character request that can't be honoured. The message is shown to the player."""


def hash_password(password: str, salt: bytes | None = None, rounds: int | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    rounds = rounds or PBKDF2_ROUNDS
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, _ = stored.split("$")
        candidate = hash_password(password, bytes.fromhex(salt), int(rounds))
    except ValueError:
        return False
    return hmac.compare_digest(candidate, stored)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Accounts:
    def __init__(self, db: Database):
        self.db = db
        self._logins = LoginLimiter()
        self._pending: dict[str, tuple[str, str, float]] = {}
        self._lock = threading.Lock()
        self.max_registrations = MAX_REGISTRATIONS
        self._registrations: deque[float] = deque()

    # ------------------------------------------------------------------ sign up and login
    def register(self, username: object, password: object, question: object, answer: object) -> User:
        if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
            raise AccountError("Usernames are 3 to 20 letters, digits, dashes or underscores.")
        _check_password(password)
        _check_security_answer(question, answer)
        self._count_registration()
        try:
            with self.db.transaction():
                user = self.db.create_user(username, hash_password(password))
                self.db.set_security_question(user.id, question,
                                              hash_password(security_questions.normalize_answer(answer)))
        except DuplicateUser:
            raise AccountError("That username is already taken.") from None
        return user

    def _count_registration(self) -> None:
        """Allows max_registrations new accounts in any window, across the whole casino."""
        with self._lock:
            now = time.monotonic()
            while self._registrations and self._registrations[0] <= now - REGISTRATION_WINDOW_SECONDS:
                self._registrations.popleft()
            if len(self._registrations) >= self.max_registrations:
                raise AccountError("Too many new accounts right now. Try again in a few minutes.")
            self._registrations.append(now)

    def authenticate(self, username: object, password: object) -> User:
        if not isinstance(username, str) or not isinstance(password, str):
            raise AccountError("Wrong username or password.")
        user = self.db.get_user(username)
        try:
            valid = self._logins.attempt(username, lambda: user is not None and verify_password(
                password, user.password_hash))
        except LockedOut as locked:
            raise AccountError(str(locked)) from None
        if not valid:
            raise AccountError("Wrong username or password.")
        return user

    def issue_token(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        self.db.add_login(_token_hash(token), user.id, int(time.time()) + LOGIN_LIFETIME)
        return token

    def logout(self, token: str) -> None:
        self.db.delete_login(_token_hash(token))

    # ------------------------------------------------------------------ security questions and resets
    def _reset_account(self, username: object) -> tuple[int, str, str, int, float]:
        """Usernames are public (registering says when one is taken), so this says plainly when there is no such
        account, and when the account logs in with the portfolio and has no question."""
        if not isinstance(username, str) or not username.strip():
            raise AccountError("Enter your username.")
        if self.db.get_user(username.strip()) is None:
            raise AccountError(NO_ACCOUNT)
        found = self.db.get_reset(username.strip())
        if found is None:
            raise AccountError("That account logs in with the portfolio and has no security question.")
        return found

    def security_question(self, username: object) -> str:
        return self._reset_account(username)[1]

    def reset_password(self, username: object, answer: object, password: object) -> None:
        """Set a new password when the security answer is right. Too many wrong answers lock resets for a while."""
        _check_password(password)
        user_id, _, answer_hash, _, _ = self._reset_account(username)
        tries = self.db.count_reset_try(user_id, time.time())
        if tries is None or tries > security_questions.MAX_RESET_FAILURES:
            raise AccountError(f"Too many wrong answers. Try again in "
                               f"{security_questions.RESET_LOCK_SECONDS // 60} minutes.")
        if not verify_password(security_questions.normalize_answer(answer), answer_hash):
            if tries == security_questions.MAX_RESET_FAILURES:
                self.db.lock_resets(user_id, time.time() + security_questions.RESET_LOCK_SECONDS)
            raise AccountError("That answer is wrong.")
        self.db.reset_password(user_id, hash_password(password))

    def hold_portfolio_login(self, sub: str, username: str) -> str:
        """The first portfolio login here asks whether to link an account the player already has or make a new one,
        so it waits here, under a code kept in the browser's cookie, until they choose."""
        code = secrets.token_urlsafe(24)
        now = time.monotonic()
        with self._lock:
            self._pending = {c: held for c, held in self._pending.items() if held[2] > now}
            self._pending[code] = (sub, username, now + PORTFOLIO_CHOICE_SECONDS)
        return code

    def held_portfolio_login(self, code: str | None) -> tuple[str, str] | None:
        """The portfolio account (sub, username) waiting under a code, or None"""
        with self._lock:
            held = self._pending.get(code or "")
        return held[:2] if held and held[2] > time.monotonic() else None

    def drop_portfolio_login(self, code: str | None) -> None:
        with self._lock:
            self._pending.pop(code or "", None)

    def link_portfolio(self, user: User, sub: str) -> None:
        try:
            linked = self.db.link_portfolio(user.id, sub)
        except DuplicateUser:
            raise AccountError("Your portfolio account is already linked to another casino account.") from None
        if not linked:
            raise AccountError("That account is already linked to another portfolio account.")

    def portfolio_user(self, sub: str, username: str) -> User:
        """A new account linked to a portfolio account and named after it. Its password is random and never shown,
        so logging in with the portfolio account is the only way in."""
        user = self.db.get_portfolio_user(sub)
        base = username if USERNAME_PATTERN.fullmatch(username) else "player"
        n = 1
        while user is None:
            name = base if n == 1 else f"{base[:20 - len(str(n))]}{n}"
            try:
                user = self.db.create_user(name, hash_password(secrets.token_urlsafe(32)), sub)
            except DuplicateUser:
                # Either the name is taken, or a second login for this portfolio account got there first.
                user = self.db.get_portfolio_user(sub)
                n += 1
        return user

    def resolve(self, token: str | None) -> tuple[User, Character | None] | None:
        """The account a token belongs to and the character it has sat down as."""
        if not token:
            return None
        found = self.db.get_login(_token_hash(token), int(time.time()))
        if found is None:
            return None
        user, character_id = found
        return user, self._owned_character(user, character_id)

    # ------------------------------------------------------------------ characters
    def create_character(self, user: User, name: object, difficulty: object) -> Character:
        if not isinstance(name, str) or not name.strip():
            raise AccountError("Give your character a name.")
        name = " ".join(name.split())
        if len(name) > MAX_CHARACTER_NAME:
            raise AccountError(f"Please keep names to {MAX_CHARACTER_NAME} characters or fewer.")
        if difficulty not in DIFFICULTIES:
            raise AccountError("Pick a difficulty.")
        if len(self.db.list_characters(user.id)) >= MAX_CHARACTERS:
            raise AccountError(f"An account can hold {MAX_CHARACTERS} characters.")
        try:
            return self.db.create_character(name, difficulty, load_starting_chips(difficulty), user.id)
        except DuplicateCharacter:
            raise AccountError(f"'{name}' is already taken. Try another name.") from None

    def select_character(self, token: str, user: User, character_id: object) -> Character | None:
        """Sit down as one of the account's characters, or stand up with character_id None."""
        if character_id is None:
            self.db.set_login_character(_token_hash(token), None)
            return None
        character = self._owned_character(user, character_id)
        if character is None:
            raise AccountError("That character isn't on your account.")
        self.db.set_login_character(_token_hash(token), character.id)
        return character

    def _owned_character(self, user: User, character_id: object) -> Character | None:
        if not is_whole(character_id):
            return None
        return next((c for c in self.db.list_characters(user.id) if c.id == character_id), None)


def _check_password(password: object) -> None:
    if not isinstance(password, str) or not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        raise AccountError(f"Passwords are {MIN_PASSWORD} to {MAX_PASSWORD} characters long.")


def _check_security_answer(question: object, answer: object) -> None:
    problem = security_questions.problem(question, answer) if isinstance(answer, str) else "Answer your security question."
    if problem:
        raise AccountError(problem)
