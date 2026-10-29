"""Chip denominations and the immutable Chips value type used wherever money moves."""
from __future__ import annotations

from typing import Mapping

CHIP_VALUES: dict[str, int] = {
    "White": 1,
    "Red": 5,
    "Green": 25,
    "Black": 100,
    "Purple": 500,
    "Orange": 1000,
}
COLORS: tuple[str, ...] = tuple(CHIP_VALUES)


def fmt_credits(amount: int) -> str:
    return f"{amount:,} cr"


class InsufficientChips(ValueError):
    """Raised when an operation would leave a negative chip count or balance."""


class Chips:
    """A count of chips per color. Arithmetic returns new objects and never goes negative."""

    __slots__ = ("_counts",)

    def __init__(self, counts: Mapping[str, int] | None = None, **kwargs: int):
        merged = {color: 0 for color in COLORS}
        for source in (counts or {}, kwargs):
            for color, count in source.items():
                key = color.capitalize()
                if key not in CHIP_VALUES:
                    raise KeyError(f"Unknown chip color: {color}")
                if int(count) < 0:
                    raise InsufficientChips(f"Negative chip count for {key}: {count}")
                merged[key] += int(count)
        self._counts = merged

    @classmethod
    def make_change(cls, credits: int) -> "Chips":
        """The fewest chips worth exactly `credits`."""
        if credits < 0:
            raise ValueError("Cannot make change for a negative amount")
        counts = {}
        for color in reversed(COLORS):
            counts[color], credits = divmod(credits, CHIP_VALUES[color])
        return cls(counts)

    @property
    def total(self) -> int:
        return sum(count * CHIP_VALUES[color] for color, count in self._counts.items())

    def split_off(self, amount: int) -> tuple["Chips", "Chips"]:
        """Take exactly `amount` credits out of this stack, breaking a bigger chip for change if needed.

        Returns (taken, remaining). taken.total == amount, and the totals always add up to self.total.
        """
        if amount < 0:
            raise ValueError("Cannot take a negative amount")
        if amount > self.total:
            raise InsufficientChips(f"Need {amount} credits but only {self.total} available")
        owed = amount
        taken = {}
        for color in reversed(COLORS):
            taken[color] = min(self._counts[color], owed // CHIP_VALUES[color])
            owed -= taken[color] * CHIP_VALUES[color]
        taken_chips = Chips(taken)
        left = self - taken_chips
        if owed:
            # Greedy selection guarantees every chip still on the rack is worth more than what is owed,
            # so breaking the smallest one always covers it.
            color = next(c for c in COLORS if left[c] and CHIP_VALUES[c] > owed)
            left = left - Chips({color: 1}) + Chips.make_change(CHIP_VALUES[color] - owed)
            taken_chips = taken_chips + Chips.make_change(owed)
        return taken_chips, left

    def as_dict(self, lowercase: bool = False) -> dict[str, int]:
        if lowercase:
            return {color.lower(): count for color, count in self._counts.items()}
        return dict(self._counts)

    def __getitem__(self, color: str) -> int:
        return self._counts[color.capitalize()]

    def __add__(self, other: "Chips") -> "Chips":
        return Chips({color: self._counts[color] + other[color] for color in COLORS})

    def __sub__(self, other: "Chips") -> "Chips":
        result = {color: self._counts[color] - other[color] for color in COLORS}
        short = [color for color, count in result.items() if count < 0]
        if short:
            raise InsufficientChips(f"Not enough {', '.join(short)} chips")
        return Chips(result)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Chips) and self._counts == other._counts

    def __hash__(self) -> int:
        return hash(tuple(self._counts.values()))

    def __repr__(self) -> str:
        parts = ", ".join(f"{color}={count}" for color, count in self._counts.items() if count)
        return f"Chips({parts})"
