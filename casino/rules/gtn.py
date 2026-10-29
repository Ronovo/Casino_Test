"""Guess the Number bet resolution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from casino.engine.bets import Outcome



@dataclass(frozen=True)
class Difficulty:
    name: str
    max_number: int

    @property
    def scale(self) -> int:
        """10 for 1-100, 100 for 1-1000, and so on. Long-shot payouts scale with it."""
        return max(1, self.max_number // 10)

    @property
    def half(self) -> int:
        return self.max_number // 2

    @property
    def range_size(self) -> int:
        return 2 * self.scale

    @property
    def digits(self) -> int:
        return len(str(self.max_number))


@dataclass(frozen=True)
class Resolution:
    outcome: Outcome
    ratio: float
    detail: str


def ratio_for(kind: str, tier: str, difficulty: Difficulty, paytable: Mapping[str, float]) -> float:
    """Exact and lucky-number payouts scale with the range; the others have fixed odds at every difficulty."""
    base = paytable[tier]
    return base * difficulty.scale if kind in ("pick", "lucky") and tier != "close" else base


def resolve(kind: str, selection: Any, number: int, difficulty: Difficulty,
            paytable: Mapping[str, float]) -> Resolution:
    lose = Resolution(Outcome.LOSE, 0, "")
    match kind:
        case "pick":
            if selection == number:
                return Resolution(Outcome.WIN, ratio_for(kind, "exact", difficulty, paytable), "Spot on!")
            if abs(selection - number) <= difficulty.scale:
                return Resolution(Outcome.WIN, ratio_for(kind, "close", difficulty, paytable),
                                  f"Close! Within {difficulty.scale}.")
            return lose
        case "high_low":
            is_high = number > difficulty.half
            if (selection == "High") == is_high:
                return Resolution(Outcome.WIN, paytable["high_low"], f"The number is {selection.lower()}.")
            return lose
        case "even_odd":
            is_even = number % 2 == 0
            if (selection == "Even") == is_even:
                return Resolution(Outcome.WIN, paytable["even_odd"], f"The number is {selection.lower()}.")
            return lose
        case "range":
            if selection <= number < selection + difficulty.range_size:
                return Resolution(Outcome.WIN, paytable["range"], "In range!")
            return lose
        case "lucky":
            first, second = selection
            if number == first:
                return Resolution(Outcome.WIN, ratio_for(kind, "lucky_1", difficulty, paytable), "Jackpot: lucky #1!")
            if number == second:
                return Resolution(Outcome.WIN, ratio_for(kind, "lucky_2", difficulty, paytable), "Lucky #2 hits!")
            return lose
    raise ValueError(f"Unknown bet kind: {kind}")
