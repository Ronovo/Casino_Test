"""Game and Round base classes plus table configuration: a scenario is a Game type plus a TableConfig."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, ClassVar, Iterable, Mapping

from casino.engine.bets import BetError, Settlement, format_ratio
from casino.engine.session import Session


@dataclass(frozen=True)
class TableConfig:
    key: str
    game: str
    title: str
    version: str = "1.0"
    order: int = 100
    min_bet: int = 1
    max_bet: int | None = None
    description: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    paytable: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TableConfig":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown table config keys: {', '.join(sorted(unknown))}")
        return cls(**data)

    @classmethod
    def from_file(cls, path: str | Path) -> "TableConfig":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def pay_rows(rows: Iterable[tuple[str, float]]) -> list[list[str]]:
    return [[label, format_ratio(ratio)] for label, ratio in rows]


def pay_section(title: str | None, rows: Iterable[Iterable[str]]) -> dict[str, Any]:
    return {"title": title, "rows": [list(row) for row in rows]}


class Round(ABC):
    """One round at a table, from the stakes going down to the last bet being settled."""

    def __init__(self, game: "Game", session: Session):
        self.game = game
        self.session = session
        self.settlements: list[Settlement] = []
        self.notes: list[str] = []
        self.finished = False

    @property
    @abstractmethod
    def staked(self) -> int:
        """Credits taken from the wallet for this round so far."""

    @abstractmethod
    def table_view(self) -> dict[str, Any]:
        """What the player can see on the table right now."""

    def actions(self) -> list[dict[str, str]]:
        """Moves open to the player, as {"id", "label"}. Rounds with no decisions have none."""
        return []

    def perform(self, action: str) -> None:
        """Apply one of the moves listed by actions()."""
        raise NotImplementedError

    def act(self, action: Any) -> None:
        if self.finished:
            raise BetError("This round is over.")
        if action not in [item["id"] for item in self.actions()]:
            raise BetError("That move isn't available right now.")
        self.perform(action)

    @property
    def net(self) -> int:
        return sum(s.net for s in self.settlements)

    def finish(self, settlements: Iterable[Settlement], notes: Iterable[str] = ()) -> None:
        self.settlements = list(settlements)
        self.notes = list(notes)
        self.finished = True
        self.session.finish_round(self.game.game_key, self.net)

    def view(self) -> dict[str, Any]:
        view = {"finished": self.finished, "actions": [] if self.finished else self.actions(), **self.table_view()}
        if self.finished:
            view["result"] = {"net": self.net, "notes": self.notes,
                              "settlements": [s.as_dict() for s in self.settlements]}
        return view


class Game(ABC):
    game_key: ClassVar[str]
    display_name: ClassVar[str]

    def __init__(self, table: TableConfig):
        self.table = table

    @property
    def title(self) -> str:
        return self.table.title

    @property
    def min_buy_in(self) -> int:
        return self.table.min_bet

    def setting(self, name: str, default: Any = None) -> Any:
        return self.table.settings.get(name, default)

    @abstractmethod
    def rules_pages(self) -> list[list[str]]:
        """How-to-play text, one list of lines per page."""

    @abstractmethod
    def paytable(self) -> list[dict[str, Any]]:
        """This table's payouts as pay_section() blocks."""

    @abstractmethod
    def start(self, session: Session, data: Mapping[str, Any]) -> Round:
        """Validate the bets in `data`, take the stakes and begin a round. Raises BetError on a bad bet."""

    def layout(self) -> dict[str, Any]:
        """Fixed details a client needs to draw this table's betting area."""
        return {}

    def betting_view(self, session: Session) -> dict[str, Any]:
        """Details that change from round to round and are shown before betting."""
        return {}

    def leave(self, session: Session) -> None:
        """The player got up from the table without a round in progress."""

    def summary(self) -> dict[str, Any]:
        table = self.table
        return {"key": table.key, "game": self.game_key, "title": table.title, "version": table.version,
                "description": table.description, "min_bet": table.min_bet, "max_bet": table.max_bet,
                "min_buy_in": self.min_buy_in}

    def info(self) -> dict[str, Any]:
        return {**self.summary(), "rules": self.rules_pages(), "paytable": self.paytable(), "layout": self.layout()}

    def take_stakes(self, session: Session, total: int) -> None:
        if not session.wallet.can_afford(total):
            raise BetError("You don't have enough chips to cover that.")
        session.wallet.withdraw(total)
