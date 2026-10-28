"""Punto Banco drawing rules and coup resolution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from casino.engine.cards import Card


def card_value(card: Card) -> int:
    if card.rank == "A":
        return 1
    if card.value >= 10:
        return 0
    return card.value


def hand_total(cards: Sequence[Card]) -> int:
    return sum(card_value(card) for card in cards) % 10


def is_natural(cards: Sequence[Card]) -> bool:
    return len(cards) == 2 and hand_total(cards) >= 8


def player_draws(total: int) -> bool:
    return total <= 5


def banker_draws(banker_total: int, player_third: int | None) -> bool:
    """Standard banker tableau. `player_third` is the value of the player's third card, or None if they stood."""
    if player_third is None:
        return banker_total <= 5
    if banker_total <= 2:
        return True
    if banker_total == 3:
        return player_third != 8
    if banker_total == 4:
        return 2 <= player_third <= 7
    if banker_total == 5:
        return 4 <= player_third <= 7
    if banker_total == 6:
        return player_third in (6, 7)
    return False


@dataclass
class Coup:
    player: list[Card]
    banker: list[Card]
    log: list[str] = field(default_factory=list)

    @property
    def player_total(self) -> int:
        return hand_total(self.player)

    @property
    def banker_total(self) -> int:
        return hand_total(self.banker)

    @property
    def winner(self) -> str:
        if self.player_total > self.banker_total:
            return "player"
        if self.banker_total > self.player_total:
            return "banker"
        return "tie"

    @property
    def dragon7(self) -> bool:
        """Banker wins with a three-card 7."""
        return self.winner == "banker" and len(self.banker) == 3 and self.banker_total == 7

    @property
    def panda8(self) -> bool:
        """Player wins with a three-card 8."""
        return self.winner == "player" and len(self.player) == 3 and self.player_total == 8


def play_coup(draw: Callable[[], Card]) -> Coup:
    first_player, first_banker, second_player, second_banker = draw(), draw(), draw(), draw()
    coup = Coup([first_player, second_player], [first_banker, second_banker])
    if is_natural(coup.player) or is_natural(coup.banker):
        coup.log.append(f"Natural! Player {coup.player_total}, Banker {coup.banker_total}. No more cards.")
        return coup

    player_third = None
    if player_draws(coup.player_total):
        card = draw()
        coup.player.append(card)
        player_third = card_value(card)
        coup.log.append(f"Player draws {card} (now {coup.player_total}).")
    else:
        coup.log.append(f"Player stands on {coup.player_total}.")

    if banker_draws(coup.banker_total, player_third):
        card = draw()
        coup.banker.append(card)
        coup.log.append(f"Banker draws {card} (now {coup.banker_total}).")
    else:
        coup.log.append(f"Banker stands on {coup.banker_total}.")
    return coup
