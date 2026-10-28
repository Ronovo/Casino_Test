"""Everything a game needs for one sitting: database, character, wallet and randomness."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

from casino.engine.cards import Shoe
from casino.engine.db import Achievement, Character, Database
from casino.engine.wallet import Wallet

# (credits reached, achievement, difficulties that can earn it; None = everyone)
MONEY_ACHIEVEMENTS = (
    (100, "Money_100", {"Very Hard"}),
    (1_000, "Money_1000", {"Hard", "Very Hard"}),
    (10_000, "Money_10000", {"Medium", "Hard", "Very Hard"}),
    (100_000, "Money_100000", None),
    (1_000_000, "Money_1000000", None),
)


@dataclass
class Session:
    db: Database
    character: Character
    wallet: Wallet
    rng: random.Random = field(default_factory=random.Random)
    shoe_factory: Callable[[int], Shoe] | None = None
    _pending: list[Achievement] = field(default_factory=list)
    # Names already unlocked, loaded on first use so repeat unlocks don't cost a database write each round.
    _unlocked: set[str] | None = None

    def new_shoe(self, decks: int = 1) -> Shoe:
        if self.shoe_factory:
            return self.shoe_factory(decks)
        return Shoe.shuffled(decks, self.rng)

    # ------------------------------------------------------------------ achievements
    def unlock(self, name: str) -> None:
        if self._unlocked is None:
            self._unlocked = {a.name for a in self.db.achievements(self.character.id) if a.unlocked}
        if name in self._unlocked:
            return
        achievement = self.db.unlock_achievement(self.character.id, name)
        self._unlocked.add(name)
        if achievement:
            self._pending.append(achievement)

    def check_money_achievements(self) -> None:
        for threshold, name, difficulties in MONEY_ACHIEVEMENTS:
            if self.wallet.total >= threshold and (difficulties is None or self.character.difficulty in difficulties):
                self.unlock(name)

    def pop_achievements(self) -> list[dict[str, str]]:
        """Unlocks the player hasn't been shown yet."""
        unlocked = [{"display_name": a.display_name, "description": a.description} for a in self._pending]
        self._pending.clear()
        return unlocked

    # ------------------------------------------------------------------ rounds
    def finish_round(self, game_key: str, net: int) -> None:
        self.db.record_round(self.character.id, game_key, net)
        self.check_money_achievements()
