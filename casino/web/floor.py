"""The casino floor as a JSON service: every request a seated player can make, independent of HTTP."""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from casino.cashier import break_chips, color_up, smaller_than
from casino.config import load_starting_chips
from casino.engine.bets import BetError, is_whole
from casino.engine.chips import CHIP_VALUES, fmt_credits
from casino.engine.db import Character, Database
from casino.engine.game import Game, Round
from casino.engine.session import Session
from casino.engine.wallet import Wallet
from casino.games import GAME_TYPES


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Seat:
    """One character's live state. Requests for the same character take the lock so they run one at a time."""
    session: Session
    rounds: dict[str, Round] = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)
    # Tables this character has started a round at since sitting down there.
    played: set[str] = field(default_factory=set)
    lock: threading.RLock = field(default_factory=threading.RLock)


class Floor:
    def __init__(self, db: Database, games: Sequence[Game],
                 rng_factory: Callable[[], random.Random] = random.SystemRandom):
        self.db = db
        self.games = {game.table.key: game for game in games}
        self.cheapest = min((game.min_buy_in for game in games), default=1)
        self._rng_factory = rng_factory
        self._seats: dict[int, Seat] = {}
        self._lock = threading.Lock()

    def seat(self, character: Character) -> Seat:
        with self._lock:
            seat = self._seats.get(character.id)
            if seat is None:
                session = Session(self.db, character, Wallet.load(self.db, character.id), rng=self._rng_factory())
                seat = self._seats[character.id] = Seat(session)
                # Stakes still on record belong to rounds that died with a previous server process.
                refund = self.db.take_open_stakes(character.id)
                if refund:
                    session.wallet.deposit(refund)
                    seat.notices.append(f"A round was interrupted last time. Your {fmt_credits(refund)} stake "
                                        "has been returned.")
            return seat

    def _game(self, key: str) -> Game:
        if key not in self.games:
            raise ApiError(404, "There is no such table.")
        return self.games[key]

    def _broke(self, seat: Seat) -> bool:
        return not seat.rounds and seat.session.wallet.total < self.cheapest

    def _reply(self, seat: Seat, **body: Any) -> dict[str, Any]:
        session = seat.session
        notices, seat.notices = seat.notices, []
        player = {"name": session.character.name, "difficulty": session.character.difficulty,
                  "credits": session.wallet.total, "chips": session.wallet.chips.as_dict(),
                  "broke": self._broke(seat)}
        return {"player": player, "achievements": session.pop_achievements(), "notices": notices, **body}

    # ------------------------------------------------------------------ tables
    def lobby(self, seat: Seat) -> dict[str, Any]:
        tables = [{**game.summary(), "in_progress": key in seat.rounds} for key, game in self.games.items()]
        return self._reply(seat, tables=tables)

    def table(self, seat: Seat, key: str) -> dict[str, Any]:
        game = self._game(key)
        current = seat.rounds.get(key)
        return self._reply(seat, table=game.info(), betting=game.betting_view(seat.session),
                           round=current.view() if current else None)

    def start(self, seat: Seat, key: str, data: Any) -> dict[str, Any]:
        game = self._game(key)
        if key in seat.rounds:
            raise ApiError(409, "Finish the round you have in progress first.")
        if not isinstance(data, Mapping):
            raise ApiError(400, "Bets must be sent as an object.")
        def begin() -> Round:
            # Chips may have changed outside this server since the seat was made, e.g. a CharacterTool import.
            seat.session.wallet.reload()
            started = game.start(seat.session, data)
            if not started.finished:
                self.db.set_open_stake(seat.session.character.id, key, started.staked)
            return started

        try:
            current = self._in_one_transaction(seat, begin)
        except BetError as error:
            raise ApiError(400, str(error)) from None
        seat.played.add(key)
        if not current.finished:
            seat.rounds[key] = current
        return self._reply(seat, round=current.view(), betting=game.betting_view(seat.session))

    def act(self, seat: Seat, key: str, action: Any) -> dict[str, Any]:
        game = self._game(key)
        current = seat.rounds.get(key)
        if current is None:
            raise ApiError(409, "You have no round in progress at this table.")
        def play() -> None:
            current.act(action)
            self.db.set_open_stake(seat.session.character.id, key, 0 if current.finished else current.staked)

        try:
            self._in_one_transaction(seat, play)
        except BetError as error:
            raise ApiError(400, str(error)) from None
        if current.finished:
            del seat.rounds[key]
        return self._reply(seat, round=current.view(), betting=game.betting_view(seat.session))

    def _in_one_transaction(self, seat: Seat, work: Callable[[], Any]) -> Any:
        """Runs work as one database transaction. If it fails part-way, the chips in the database and in memory
        go back to how they were before it started."""
        try:
            with self.db.transaction():
                return work()
        except BaseException:
            seat.session.wallet.reload()
            raise

    def leave(self, seat: Seat, key: str) -> dict[str, Any]:
        game = self._game(key)
        if key not in seat.rounds and key not in seat.played:
            game.leave(seat.session)
        seat.played.discard(key)
        return self._reply(seat)

    # ------------------------------------------------------------------ character
    def profile(self, seat: Seat) -> dict[str, Any]:
        session = seat.session
        names = {game_type.game_key: game_type.display_name for game_type in GAME_TYPES.values()}
        stats = [{"game": names.get(key, key.title()), **row}
                 for key, row in self.db.get_stats(session.character.id).items()]
        categories: dict[str, list[dict[str, Any]]] = {}
        for achievement in self.db.achievements(session.character.id):
            shown = {"unlocked": achievement.unlocked}
            if achievement.unlocked:
                shown.update(display_name=achievement.display_name, description=achievement.description,
                             date_unlocked=achievement.date_unlocked)
            categories.setdefault(achievement.category, []).append(shown)
        achievements = [{"category": category, "items": items} for category, items in categories.items()]
        return self._reply(seat, stats=stats, categories=achievements)

    def start_over(self, seat: Seat) -> dict[str, Any]:
        if not self._broke(seat):
            raise ApiError(400, "Starting over is only for players who can't afford any table.")
        seat.session.wallet.reset(load_starting_chips(seat.session.character.difficulty))
        return self._reply(seat)

    def exchange(self, seat: Seat, data: Any) -> dict[str, Any]:
        """Break chips into a smaller color or color small chips up. The rack's total never changes."""
        wallet = seat.session.wallet
        if not isinstance(data, Mapping):
            raise ApiError(400, "That exchange isn't possible.")
        action, color, into, count = data.get("action"), data.get("color"), data.get("into"), data.get("count")
        if (action not in ("break", "color_up") or not isinstance(into, str) or into not in CHIP_VALUES
                or not is_whole(count) or count < 1):
            raise ApiError(400, "That exchange isn't possible.")
        if action == "break":
            if (not isinstance(color, str) or color not in CHIP_VALUES or CHIP_VALUES[into] >= CHIP_VALUES[color]
                    or count > wallet.chips[color]):
                raise ApiError(400, "You can only break chips you have into a smaller color.")
            wallet.exchange(break_chips(wallet.chips, color, count, into))
        else:
            if count > smaller_than(wallet.chips, into).total // CHIP_VALUES[into]:
                raise ApiError(400, "You don't have enough smaller chips for that.")
            wallet.exchange(color_up(wallet.chips, into, count))
        return self._reply(seat)
