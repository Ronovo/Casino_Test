"""Playing cards and shoes (one or more shuffled decks)."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Sequence

RANKS: tuple[str, ...] = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
SUITS: tuple[str, ...] = ("S", "H", "D", "C")
SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
SUIT_NAMES = {"S": "Spades", "H": "Hearts", "D": "Diamonds", "C": "Clubs"}
RANK_NAMES = {"J": "Jack", "Q": "Queen", "K": "King", "A": "Ace"}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS or self.suit not in SUITS:
            raise ValueError(f"Invalid card: {self.rank}{self.suit}")

    @classmethod
    def parse(cls, text: str) -> "Card":
        """Parse 'AS', '10H', 'TH' or the legacy '1H' (ten of hearts)."""
        text = text.strip().upper()
        rank, suit = text[:-1], text[-1]
        if rank in ("1", "T"):
            rank = "10"
        return cls(rank, suit)

    @property
    def value(self) -> int:
        """Poker ranking value: 2..14 with Ace high."""
        return RANKS.index(self.rank) + 2

    @property
    def is_red(self) -> bool:
        return self.suit in ("H", "D")

    @property
    def name(self) -> str:
        return f"{RANK_NAMES.get(self.rank, self.rank)} of {SUIT_NAMES[self.suit]}"

    def __str__(self) -> str:
        return f"{self.rank}{SUIT_SYMBOLS[self.suit]}"


def parse_cards(texts: Iterable[str | Card]) -> list[Card]:
    return [text if isinstance(text, Card) else Card.parse(text) for text in texts]


def cards_view(cards: Sequence[Card], face_down: Iterable[int] = ()) -> list[dict[str, str] | None]:
    """Cards as sent to a client. Face-down cards go out as None so their identity never leaves the server."""
    face_down = set(face_down)
    return [None if i in face_down else {"rank": card.rank, "suit": card.suit} for i, card in enumerate(cards)]


class ShoeEmpty(RuntimeError):
    """Raised when drawing from an empty shoe."""


class Shoe:
    """Cards are drawn from the front, so a stacked shoe deals in the order given."""

    def __init__(self, cards: Iterable[Card]):
        self._cards = list(cards)

    @classmethod
    def shuffled(cls, decks: int = 1, rng: random.Random | None = None) -> "Shoe":
        cards = [Card(rank, suit) for _ in range(decks) for suit in SUITS for rank in RANKS]
        (rng or random).shuffle(cards)
        return cls(cards)

    @classmethod
    def stacked(cls, cards: Iterable[str | Card]) -> "Shoe":
        return cls(parse_cards(cards))

    def draw(self) -> Card:
        if not self._cards:
            raise ShoeEmpty("The shoe is empty")
        return self._cards.pop(0)

    def __len__(self) -> int:
        return len(self._cards)
