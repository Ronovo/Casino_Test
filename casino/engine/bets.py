"""Bets, outcomes and settlement: the single path by which winnings reach a wallet."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import TYPE_CHECKING, Any, Callable, Hashable, Mapping

from casino.engine.chips import fmt_credits

if TYPE_CHECKING:
    from casino.engine.wallet import Wallet


class Outcome(Enum):
    WIN = "win"
    LOSE = "lose"
    PUSH = "push"


class BetError(ValueError):
    """A bet or move the table can't accept. The message is shown to the player."""


@dataclass
class Bet:
    name: str
    amount: int
    selection: Any = None

    @property
    def label(self) -> str:
        return self.name if self.selection is None else f"{self.name} ({self.selection})"


def is_whole(value: Any) -> bool:
    """An int from the client's JSON. true and false are ints to Python, so they are refused."""
    return isinstance(value, int) and not isinstance(value, bool)


def read_stake(value: Any, label: str, minimum: int = 1, maximum: int | None = None, optional: bool = False) -> int:
    """Validate a stake sent by a client. Optional stakes may be missing or 0, meaning no bet."""
    if optional and value in (None, 0):
        return 0
    if not is_whole(value):
        raise BetError(f"{label}: the stake must be a whole number of credits.")
    if value < max(minimum, 1):
        raise BetError(f"{label}: the minimum stake is {fmt_credits(max(minimum, 1))}.")
    if maximum is not None and value > maximum:
        raise BetError(f"{label}: the maximum stake is {fmt_credits(maximum)}.")
    return value


def add_stake(bet: Bet, value: Any, minimum: int, maximum: int | None) -> None:
    """Add a client's stake to a bet that may already hold chips, keeping the total inside the table maximum."""
    bet.amount += read_stake(value, bet.label, minimum, maximum)
    if maximum is not None and bet.amount > maximum:
        raise BetError(f"{bet.label}: the maximum stake is {fmt_credits(maximum)}.")


def gather_slip(items: Any, read_spot: Callable[[Mapping[str, Any]], tuple[Hashable, str, Any]],
                minimum: int, maximum: int | None) -> dict[Hashable, Bet]:
    """Bets sent as a list of objects with an "amount"; stakes on the same spot add up. read_spot turns one object
    into (spot, bet name, selection), raising BetError for a spot that isn't on the board."""
    if not isinstance(items, list) or not items:
        raise BetError("Place at least one bet first.")
    slip: dict[Hashable, Bet] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise BetError("That bet isn't on the board.")
        spot, name, selection = read_spot(item)
        add_stake(slip.setdefault(spot, Bet(name, 0, selection)), item.get("amount"), minimum, maximum)
    return slip


def format_ratio(ratio: float) -> str:
    fraction = Fraction(str(ratio)).limit_denominator(100)
    return f"{fraction.numerator:,}:{fraction.denominator:,}"


def payout(amount: int, outcome: Outcome, ratio: float = 1) -> int:
    """Credits handed back for a bet: stake plus winnings (rounded down), the stake alone, or nothing."""
    if outcome is Outcome.WIN:
        return amount + int(amount * Fraction(str(ratio)))
    if outcome is Outcome.PUSH:
        return amount
    return 0


@dataclass(frozen=True)
class Settlement:
    bet: Bet
    outcome: Outcome
    ratio: float
    returned: int

    @property
    def net(self) -> int:
        return self.returned - self.bet.amount

    def as_dict(self) -> dict[str, Any]:
        # A losing bet that still hands credits back is a surrender.
        result = "surrender" if self.outcome is Outcome.LOSE and self.returned else self.outcome.value
        return {"label": self.bet.label, "amount": self.bet.amount, "result": result,
                "ratio": format_ratio(self.ratio) if self.outcome is Outcome.WIN else None,
                "returned": self.returned, "net": self.net}


def settle(wallet: "Wallet", bet: Bet, outcome: Outcome, ratio: float = 1, returned: int | None = None) -> Settlement:
    """Pay a bet into the wallet. `returned` overrides the normal payout (e.g. surrender returns half)."""
    if returned is None:
        returned = payout(bet.amount, outcome, ratio)
    wallet.deposit(returned)
    return Settlement(bet, outcome, ratio, returned)
