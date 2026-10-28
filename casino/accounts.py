"""Player accounts: registration, password checks, login tokens and the characters an account owns."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time

from casino.config import DIFFICULTIES, load_starting_chips
from casino.engine.db import Character, Database, DuplicateCharacter, DuplicateUser, User

PBKDF2_ROUNDS = 240_000
LOGIN_LIFETIME = 60 * 60 * 24 * 30
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,20}")
MIN_PASSWORD, MAX_PASSWORD = 6, 128
MAX_CHARACTER_NAME = 30
MAX_CHARACTERS = 8
# After this many wrong passwords in a row an account refuses logins for LOCKOUT_SECONDS.
MAX_FAILURES, LOCKOUT_SECONDS = 5, 60


class AccountError(ValueError):
    """A sign-up, login or character request that can't be honoured. The message is shown to the player."""


def hash_password(password: str, salt: bytes | None = None, rounds: int = PBKDF2_ROUNDS) -> str:
    salt = salt or secrets.token_bytes(16)
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
        self._failures: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ sign up and login
    def register(self, username: object, password: object) -> User:
        if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
            raise AccountError("Usernames are 3 to 20 letters, digits, dashes or underscores.")
        if not isinstance(password, str) or not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
            raise AccountError(f"Passwords are {MIN_PASSWORD} to {MAX_PASSWORD} characters long.")
        try:
            return self.db.create_user(username, hash_password(password))
        except DuplicateUser:
            raise AccountError("That username is already taken.") from None

    def login(self, username: object, password: object) -> str:
        """Check a password and return a new login token."""
        if not isinstance(username, str) or not isinstance(password, str):
            raise AccountError("Wrong username or password.")
        key = username.lower()
        with self._lock:
            failures, locked_until = self._failures.get(key, (0, 0.0))
            if time.monotonic() < locked_until:
                raise AccountError("Too many wrong passwords. Wait a minute and try again.")
        user = self.db.get_user(username)
        # A missing account still costs one hash so response time doesn't reveal which usernames exist.
        valid = verify_password(password, user.password_hash if user else hash_password(""))
        with self._lock:
            if user and valid:
                self._failures.pop(key, None)
            else:
                failures += 1
                locked = time.monotonic() + LOCKOUT_SECONDS if failures >= MAX_FAILURES else 0.0
                self._failures[key] = (0 if locked else failures, locked)
                raise AccountError("Wrong username or password.")
        return self.issue_token(user)

    def issue_token(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        self.db.add_login(_token_hash(token), user.id, int(time.time()) + LOGIN_LIFETIME)
        return token

    def logout(self, token: str) -> None:
        self.db.delete_login(_token_hash(token))

    def resolve(self, token: str | None) -> tuple[User, Character | None] | None:
        """The account a token belongs to and the character it has sat down as."""
        if not token:
            return None
        found = self.db.get_login(_token_hash(token), int(time.time()))
        if found is None:
            return None
        user, character_id = found
        character = next((c for c in self.db.list_characters(user.id) if c.id == character_id), None)
        return user, character

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
        character = next((c for c in self.db.list_characters(user.id) if c.id == character_id), None)
        if character is None:
            raise AccountError("That character isn't on your account.")
        self.db.set_login_character(_token_hash(token), character.id)
        return character

    def claim_character(self, character_name: str, username: str) -> Character:
        """Hand a character that predates accounts to a user. Run from the command line, never from the web."""
        user = self.db.get_user(username)
        if user is None:
            raise AccountError(f"No account named '{username}'. Register it in the web app first.")
        character = self.db.get_character(character_name)
        if character is None:
            raise AccountError(f"No character named '{character_name}'.")
        if character.user_id not in (None, user.id):
            raise AccountError(f"'{character_name}' already belongs to another account.")
        self.db.set_character_owner(character.id, user.id)
        return character
