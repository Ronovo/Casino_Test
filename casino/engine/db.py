"""SQLite persistence: accounts and their logins, characters, chip racks, per-game stats, achievements, the credits
on a table mid-round (so a lost round can be refunded) and saved per-table state such as a racing season."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from casino.engine.chips import CHIP_VALUES, COLORS, Chips

SCHEMA = """
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    portfolio_sub TEXT UNIQUE,
    security_question TEXT,
    security_answer_hash TEXT,
    reset_failures INTEGER NOT NULL DEFAULT 0,
    reset_locked_until REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Logins (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    character_id INTEGER REFERENCES Characters (id),
    expires_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users (id)
);

CREATE TABLE IF NOT EXISTS Characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL COLLATE NOCASE,
    difficulty TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES Users (id)
);

CREATE TABLE IF NOT EXISTS PlayerChips (
    p_chip_id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    white INTEGER NOT NULL DEFAULT 0,
    red INTEGER NOT NULL DEFAULT 0,
    green INTEGER NOT NULL DEFAULT 0,
    black INTEGER NOT NULL DEFAULT 0,
    purple INTEGER NOT NULL DEFAULT 0,
    orange INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (character_id) REFERENCES Characters (id)
);

CREATE TABLE IF NOT EXISTS GameStats (
    character_id INTEGER NOT NULL,
    game_key TEXT NOT NULL,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    pushes INTEGER NOT NULL DEFAULT 0,
    net_credits INTEGER NOT NULL DEFAULT 0,
    biggest_win INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, game_key),
    FOREIGN KEY (character_id) REFERENCES Characters (id)
);

CREATE TABLE IF NOT EXISTS Achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS CharacterAchievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    date_unlocked TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES Characters (id),
    FOREIGN KEY (achievement_id) REFERENCES Achievements (id),
    UNIQUE (character_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS OpenStakes (
    character_id INTEGER NOT NULL,
    table_key TEXT NOT NULL,
    amount INTEGER NOT NULL,
    PRIMARY KEY (character_id, table_key),
    FOREIGN KEY (character_id) REFERENCES Characters (id)
);

CREATE TABLE IF NOT EXISTS TableState (
    character_id INTEGER NOT NULL,
    table_key TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (character_id, table_key),
    FOREIGN KEY (character_id) REFERENCES Characters (id)
);
"""

STAT_FIELDS = ("wins", "losses", "pushes", "net_credits", "biggest_win")
# Expired logins are swept once they are this many seconds older than a newly issued one.
LOGIN_PURGE_MARGIN = 60 * 60 * 24 * 60


class DuplicateCharacter(ValueError):
    """A character with that name already exists."""


class DuplicateUser(ValueError):
    """An account with that username already exists."""


@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str


@dataclass(frozen=True)
class Character:
    id: int
    name: str
    difficulty: str
    user_id: int


@dataclass(frozen=True)
class Achievement:
    name: str
    category: str
    display_name: str
    description: str
    unlocked: bool = False
    date_unlocked: str | None = None


class Database:
    def __init__(self, path: str | Path, durable: bool = True):
        """`durable=False` skips the disk flush on every commit: much faster, but only safe for throwaway data."""
        self.path = str(path)
        self.durable = durable
        self._local = threading.local()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """A connection that commits on success, rolls back on error and is always closed. Inside transaction() it is
        that transaction's connection instead, so the writes commit or roll back together."""
        shared = getattr(self._local, "conn", None)
        if shared is not None:
            yield shared
            return
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if not self.durable:
            conn.execute("PRAGMA synchronous = OFF")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Every database write made on this thread inside the block commits as one, or not at all."""
        if getattr(self._local, "conn", None) is not None:
            yield
            return
        with self.connect() as conn:
            self._local.conn = conn
            try:
                yield
            finally:
                self._local.conn = None

    # ------------------------------------------------------------------ setup
    def initialize(self, achievements_path: str | Path | None = None) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        if achievements_path:
            self.sync_achievements(achievements_path)

    def sync_achievements(self, path: str | Path) -> None:
        """Upsert achievements from JSON so edits to the file reach existing databases."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        with self.connect() as conn:
            for category, achievements in data.items():
                for item in achievements:
                    conn.execute(
                        """INSERT INTO Achievements (name, category, display_name, description)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(name) DO UPDATE SET category = excluded.category,
                               display_name = excluded.display_name, description = excluded.description""",
                        (item["name"], category, item["displayName"], item["description"]),
                    )

    # ------------------------------------------------------------------ accounts
    def create_user(self, username: str, password_hash: str, portfolio_sub: str | None = None) -> User:
        with self.connect() as conn:
            try:
                cursor = conn.execute("INSERT INTO Users (username, password_hash, portfolio_sub) VALUES (?, ?, ?)",
                                      (username, password_hash, portfolio_sub))
            except sqlite3.IntegrityError:
                raise DuplicateUser(username) from None
        return User(cursor.lastrowid, username, password_hash)

    def _find_user(self, column: str, value: str) -> User | None:
        with self.connect() as conn:
            row = conn.execute(f"SELECT id, username, password_hash FROM Users WHERE {column} = ?",
                               (value,)).fetchone()
        return User(*row) if row else None

    def get_user(self, username: str) -> User | None:
        return self._find_user("username", username)

    def link_portfolio(self, user_id: int, sub: str) -> bool:
        """Links an account to a portfolio account. False when the account is already linked to one."""
        with self.connect() as conn:
            try:
                return conn.execute("UPDATE Users SET portfolio_sub = ? WHERE id = ? AND portfolio_sub IS NULL",
                                    (sub, user_id)).rowcount == 1
            except sqlite3.IntegrityError:
                raise DuplicateUser(sub) from None

    def get_portfolio_user(self, sub: str) -> User | None:
        return self._find_user("portfolio_sub", sub)

    def add_login(self, token_hash: str, user_id: int, expires_at: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM Logins WHERE expires_at < ?", (expires_at - LOGIN_PURGE_MARGIN,))
            conn.execute("INSERT INTO Logins (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                         (token_hash, user_id, expires_at))

    def get_login(self, token_hash: str, now: int) -> tuple[User, int | None] | None:
        """The account behind a login token and the character it is playing, if the token is still valid."""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT U.id, U.username, U.password_hash, L.character_id
                   FROM Logins L JOIN Users U ON U.id = L.user_id
                   WHERE L.token_hash = ? AND L.expires_at > ?""",
                (token_hash, now),
            ).fetchone()
        return (User(row[0], row[1], row[2]), row[3]) if row else None

    def set_login_character(self, token_hash: str, character_id: int | None) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE Logins SET character_id = ? WHERE token_hash = ?", (character_id, token_hash))

    def delete_login(self, token_hash: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM Logins WHERE token_hash = ?", (token_hash,))

    # ------------------------------------------------------------------ security questions
    def set_security_question(self, user_id: int, question: str, answer_hash: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE Users SET security_question = ?, security_answer_hash = ? WHERE id = ?",
                         (question, answer_hash, user_id))

    def get_reset(self, username: str) -> tuple[int, str, str, int, float] | None:
        """Id, security question, answer hash, wrong answers so far and lock time of an account that has a question."""
        with self.connect() as conn:
            row = conn.execute(
                """SELECT id, security_question, security_answer_hash, reset_failures, reset_locked_until
                   FROM Users WHERE username = ? AND security_answer_hash IS NOT NULL""", (username,)).fetchone()
        return tuple(row) if row else None

    def count_reset_try(self, user_id: int, now: float) -> int | None:
        """Count one more reset try and return the count so far, or None while resets are locked. It is one
        statement, so tries sent at the same moment each get their own count."""
        with self.connect() as conn:
            row = conn.execute("""UPDATE Users SET reset_failures = reset_failures + 1
                                  WHERE id = ? AND reset_locked_until <= ? RETURNING reset_failures""",
                               (user_id, now)).fetchone()
        return row[0] if row else None

    def lock_resets(self, user_id: int, until: float) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE Users SET reset_failures = 0, reset_locked_until = ? WHERE id = ?", (until, user_id))

    def reset_password(self, user_id: int, password_hash: str) -> None:
        """Set a new password and log the account out everywhere."""
        with self.connect() as conn:
            conn.execute("UPDATE Users SET password_hash = ?, reset_failures = 0, reset_locked_until = 0 WHERE id = ?",
                         (password_hash, user_id))
            conn.execute("DELETE FROM Logins WHERE user_id = ?", (user_id,))

    # ------------------------------------------------------------------ characters
    @staticmethod
    def _character(row: sqlite3.Row) -> Character:
        return Character(row["id"], row["name"], row["difficulty"], row["user_id"])

    def list_characters(self, user_id: int) -> list[Character]:
        with self.connect() as conn:
            rows = conn.execute("SELECT id, name, difficulty, user_id FROM Characters WHERE user_id = ? ORDER BY name",
                                (user_id,)).fetchall()
        return [self._character(row) for row in rows]

    def create_character(self, name: str, difficulty: str, chips: Chips, user_id: int) -> Character:
        with self.connect() as conn:
            try:
                cursor = conn.execute("INSERT INTO Characters (name, difficulty, user_id) VALUES (?, ?, ?)",
                                      (name, difficulty, user_id))
            except sqlite3.IntegrityError:
                raise DuplicateCharacter(name) from None
            character = Character(cursor.lastrowid, name, difficulty, user_id)
            self._write_chips(conn, character.id, chips)
        return character

    # ------------------------------------------------------------------ chips
    def character_credits(self, user_id: int) -> dict[int, int]:
        """The credits each of an account's characters holds, in one query."""
        values = " + ".join(f"P.{color.lower()} * {CHIP_VALUES[color]}" for color in COLORS)
        with self.connect() as conn:
            rows = conn.execute(f"""SELECT C.id, COALESCE({values}, 0) FROM Characters C
                                    LEFT JOIN PlayerChips P ON P.character_id = C.id WHERE C.user_id = ?""",
                                (user_id,)).fetchall()
        return {row[0]: row[1] for row in rows}

    def load_chips(self, character_id: int) -> Chips:
        with self.connect() as conn:
            row = conn.execute(
                f"SELECT {', '.join(c.lower() for c in COLORS)} FROM PlayerChips WHERE character_id = ?",
                (character_id,),
            ).fetchone()
        return Chips(dict(row)) if row else Chips()

    def save_chips(self, character_id: int, chips: Chips) -> None:
        with self.connect() as conn:
            self._write_chips(conn, character_id, chips)

    @staticmethod
    def _write_chips(conn: sqlite3.Connection, character_id: int, chips: Chips) -> None:
        values = chips.as_dict(lowercase=True)
        assignments = ", ".join(f"{color} = :{color}" for color in values)
        cursor = conn.execute(
            f"UPDATE PlayerChips SET {assignments} WHERE character_id = :character_id",
            {**values, "character_id": character_id},
        )
        if cursor.rowcount == 0:
            conn.execute(
                f"INSERT INTO PlayerChips (character_id, {', '.join(values)}) "
                f"VALUES (:character_id, {', '.join(':' + color for color in values)})",
                {**values, "character_id": character_id},
            )

    # ------------------------------------------------------------------ stats
    def record_round(self, character_id: int, game_key: str, net: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO GameStats (character_id, game_key, wins, losses, pushes, net_credits, biggest_win)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(character_id, game_key) DO UPDATE SET
                       wins = wins + excluded.wins,
                       losses = losses + excluded.losses,
                       pushes = pushes + excluded.pushes,
                       net_credits = net_credits + excluded.net_credits,
                       biggest_win = MAX(biggest_win, excluded.biggest_win)""",
                (character_id, game_key, int(net > 0), int(net < 0), int(net == 0), net, max(net, 0)),
            )

    def get_stats(self, character_id: int) -> dict[str, dict[str, int]]:
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT game_key, {', '.join(STAT_FIELDS)} FROM GameStats WHERE character_id = ? ORDER BY game_key",
                (character_id,),
            ).fetchall()
        return {row["game_key"]: {field: row[field] for field in STAT_FIELDS} for row in rows}

    # ------------------------------------------------------------------ achievements
    def unlock_achievement(self, character_id: int, name: str) -> Achievement | None:
        """Unlock an achievement. Returns it if newly unlocked, None if the character already had it."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, name, category, display_name, description FROM Achievements WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown achievement: {name}")
            cursor = conn.execute(
                "INSERT OR IGNORE INTO CharacterAchievements (character_id, achievement_id) VALUES (?, ?)",
                (character_id, row["id"]),
            )
        if cursor.rowcount == 0:
            return None
        return Achievement(row["name"], row["category"], row["display_name"], row["description"], True)

    def achievements(self, character_id: int) -> list[Achievement]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT A.name, A.category, A.display_name, A.description, CA.date_unlocked
                   FROM Achievements A
                   LEFT JOIN CharacterAchievements CA ON CA.achievement_id = A.id AND CA.character_id = ?
                   ORDER BY A.category, A.id""",
                (character_id,),
            ).fetchall()
        return [
            Achievement(row["name"], row["category"], row["display_name"], row["description"],
                        row["date_unlocked"] is not None, row["date_unlocked"])
            for row in rows
        ]

    # ------------------------------------------------------------------ rounds in progress
    def set_open_stake(self, character_id: int, table_key: str, amount: int) -> None:
        """Record credits sitting on a table mid-round so they can be handed back if the round is lost."""
        with self.connect() as conn:
            if amount:
                conn.execute("INSERT OR REPLACE INTO OpenStakes (character_id, table_key, amount) VALUES (?, ?, ?)",
                             (character_id, table_key, amount))
            else:
                conn.execute("DELETE FROM OpenStakes WHERE character_id = ? AND table_key = ?",
                             (character_id, table_key))

    def take_open_stakes(self, character_id: int) -> int:
        """Remove and return the total of a character's recorded open stakes."""
        with self.connect() as conn:
            total = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM OpenStakes WHERE character_id = ?",
                                 (character_id,)).fetchone()[0]
            conn.execute("DELETE FROM OpenStakes WHERE character_id = ?", (character_id,))
        return total

    # ------------------------------------------------------------------ saved table state
    def load_table_state(self, character_id: int, table_key: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT data FROM TableState WHERE character_id = ? AND table_key = ?",
                               (character_id, table_key)).fetchone()
        return json.loads(row[0]) if row else None

    def save_table_state(self, character_id: int, table_key: str, state: dict) -> None:
        with self.connect() as conn:
            conn.execute("INSERT OR REPLACE INTO TableState (character_id, table_key, data) VALUES (?, ?, ?)",
                         (character_id, table_key, json.dumps(state)))
