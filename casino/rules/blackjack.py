"""Blackjack hand values and dealer behaviour."""
from __future__ import annotations

from typing import Sequence

from casino.engine.bets import Outcome
from casino.engine.cards import Card


def card_points(card: Card) -> int:
    """Ace counts 1 here; hand_value decides when it becomes 11."""
    if card.rank == "A":
        return 1
    return min(card.value, 10)


def hand_value(cards: Sequence[Card]) -> tuple[int, bool]:
    """Best total and whether it is soft (an Ace is counting as 11)."""
    total = sum(card_points(card) for card in cards)
    if any(card.rank == "A" for card in cards) and total + 10 <= 21:
        return total + 10, True
    return total, False


def total(cards: Sequence[Card]) -> int:
    return hand_value(cards)[0]


def is_natural(cards: Sequence[Card]) -> bool:
    return len(cards) == 2 and total(cards) == 21


def is_bust(cards: Sequence[Card]) -> bool:
    return total(cards) > 21


def can_split(cards: Sequence[Card]) -> bool:
    """Two cards of the same value: a pair, or any two ten-value cards."""
    return len(cards) == 2 and card_points(cards[0]) == card_points(cards[1])


def dealer_should_hit(cards: Sequence[Card], stands_on: int = 17, hit_soft_17: bool = False) -> bool:
    value, soft = hand_value(cards)
    if value < stands_on:
        return True
    return value == 17 and soft and hit_soft_17


def compare(player: Sequence[Card], dealer: Sequence[Card]) -> Outcome:
    """Outcome of a finished (non-natural) player hand against the dealer's finished hand."""
    if is_bust(player):
        return Outcome.LOSE
    if is_bust(dealer):
        return Outcome.WIN
    player_total, dealer_total = total(player), total(dealer)
    if player_total > dealer_total:
        return Outcome.WIN
    if player_total < dealer_total:
        return Outcome.LOSE
    return Outcome.PUSH
