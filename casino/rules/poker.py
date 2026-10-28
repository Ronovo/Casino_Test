"""Poker hand evaluation with full tie-breaking, plus Ultimate Texas Hold'em helpers."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import Sequence

from casino.engine.cards import RANK_NAMES, Card

CATEGORY_NAMES = {
    1: "High Card", 2: "Pair", 3: "Two Pair", 4: "Three of a Kind", 5: "Straight",
    6: "Flush", 7: "Full House", 8: "Four of a Kind", 9: "Straight Flush", 10: "Royal Flush",
}
VALUE_NAMES = {value: RANK_NAMES.get(rank, rank) for value, rank in
               zip(range(2, 15), ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"))}


def _plural(value: int) -> str:
    return VALUE_NAMES[value] + "s"


@dataclass(frozen=True, order=True)
class HandRank:
    category: int
    tiebreak: tuple[int, ...]
    cards: tuple[Card, ...] = field(compare=False, default=())

    @property
    def name(self) -> str:
        return CATEGORY_NAMES[self.category]

    @property
    def description(self) -> str:
        top = self.tiebreak[0] if self.tiebreak else 0
        match self.category:
            case 1:
                return f"High Card, {VALUE_NAMES[top]}"
            case 2:
                return f"Pair of {_plural(top)}"
            case 3:
                return f"Two Pair, {_plural(top)} and {_plural(self.tiebreak[1])}"
            case 4:
                return f"Three {_plural(top)}"
            case 5 | 9:
                return f"{self.name}, {VALUE_NAMES[top]} high"
            case 6:
                return f"Flush, {VALUE_NAMES[top]} high"
            case 7:
                return f"Full House, {_plural(top)} over {_plural(self.tiebreak[1])}"
            case 8:
                return f"Four {_plural(top)}"
            case _:
                return "Royal Flush"


def _straight_high(values: Sequence[int]) -> int | None:
    unique = sorted(set(values), reverse=True)
    if len(unique) != 5:
        return None
    if unique[0] - unique[4] == 4:
        return unique[0]
    if unique == [14, 5, 4, 3, 2]:
        return 5
    return None


def evaluate5(cards: Sequence[Card]) -> HandRank:
    if len(cards) != 5:
        raise ValueError("evaluate5 needs exactly five cards")
    values = [card.value for card in cards]
    counts = Counter(values)
    # Group by (how many, value), biggest groups first: e.g. full house -> (trips value, pair value)
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    ordered = tuple(value for value, _ in groups)
    shape = [count for _, count in groups]
    flush = len({card.suit for card in cards}) == 1
    straight_high = _straight_high(values)
    hand = tuple(cards)

    if flush and straight_high:
        return HandRank(10 if straight_high == 14 else 9, (straight_high,), hand)
    if shape[0] == 4:
        return HandRank(8, ordered, hand)
    if shape == [3, 2]:
        return HandRank(7, ordered, hand)
    if flush:
        return HandRank(6, tuple(sorted(values, reverse=True)), hand)
    if straight_high:
        return HandRank(5, (straight_high,), hand)
    if shape[0] == 3:
        return HandRank(4, ordered, hand)
    if shape[:2] == [2, 2]:
        return HandRank(3, ordered, hand)
    if shape[0] == 2:
        return HandRank(2, ordered, hand)
    return HandRank(1, tuple(sorted(values, reverse=True)), hand)


def best_hand(cards: Sequence[Card]) -> HandRank:
    """Best five-card hand from five to seven cards."""
    if len(cards) < 5:
        raise ValueError("best_hand needs at least five cards")
    return max(evaluate5(combo) for combo in combinations(cards, 5))


def describe_cards(cards: Sequence[Card]) -> str:
    """Friendly description for any number of cards (used before the board is complete)."""
    if len(cards) >= 5:
        return best_hand(cards).description
    counts = Counter(card.value for card in cards)
    value, count = max(counts.items(), key=lambda item: (item[1], item[0]))
    if count >= 2:
        return {2: f"Pair of {_plural(value)}", 3: f"Three {_plural(value)}"}.get(count, f"Four {_plural(value)}")
    return f"High Card, {VALUE_NAMES[value]}"


def dealer_qualifies(rank: HandRank) -> bool:
    return rank.category >= 2


def pairs_bonus_key(hole_cards: Sequence[Card]) -> str | None:
    """Paytable key for the Pairs Bonus: the pair's rank for tens and up, '2-9' for lower pairs."""
    first, second = hole_cards
    if first.rank != second.rank:
        return None
    return first.rank if first.value >= 10 else "2-9"
