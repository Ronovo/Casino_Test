"""A character's chip rack. Every change is written to the database immediately."""
from __future__ import annotations

from casino.engine.chips import Chips
from casino.engine.db import Database


class Wallet:
    def __init__(self, db: Database, character_id: int, chips: Chips):
        self._db = db
        self._character_id = character_id
        self._chips = chips

    @classmethod
    def load(cls, db: Database, character_id: int) -> "Wallet":
        return cls(db, character_id, db.load_chips(character_id))

    def reload(self) -> None:
        """Re-reads the rack after a failed round rolled back chip changes this copy had already made."""
        self._chips = self._db.load_chips(self._character_id)

    @property
    def chips(self) -> Chips:
        return self._chips

    @property
    def total(self) -> int:
        return self._chips.total

    def can_afford(self, amount: int) -> bool:
        return 0 <= amount <= self.total

    def withdraw(self, amount: int) -> None:
        """Remove credits, breaking chips for change when needed. split_off refuses a negative amount or more than
        the rack holds."""
        self._set(self._chips.split_off(amount)[1])

    def deposit(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot deposit a negative amount")
        if amount:
            self._set(self._chips + Chips.make_change(amount))

    def exchange(self, new_chips: Chips) -> None:
        """Swap to a different mix of chips worth exactly the same amount."""
        if new_chips.total != self.total:
            raise ValueError("An exchange must keep the same total value")
        self._set(new_chips)

    def reset(self, chips: Chips) -> None:
        """Replace the rack outright (used when a broke character starts over)."""
        self._set(chips)

    def _set(self, chips: Chips) -> None:
        self._db.save_chips(self._character_id, chips)
        self._chips = chips
