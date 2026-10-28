"""A character's chip rack. Every change is written to the database immediately."""
from __future__ import annotations

from casino.engine.chips import Chips, InsufficientChips
from casino.engine.db import Database


class Wallet:
    def __init__(self, db: Database, character_id: int, chips: Chips):
        self._db = db
        self._character_id = character_id
        self._chips = chips

    @classmethod
    def load(cls, db: Database, character_id: int) -> "Wallet":
        return cls(db, character_id, db.load_chips(character_id))

    @property
    def chips(self) -> Chips:
        return self._chips

    @property
    def total(self) -> int:
        return self._chips.total

    def can_afford(self, amount: int) -> bool:
        return 0 <= amount <= self.total

    def withdraw(self, stake: Chips | int) -> int:
        """Remove a stake. Exact chips are taken when present; otherwise chips are broken for change."""
        if isinstance(stake, Chips):
            amount = stake.total
            remaining = self._chips - stake if self._chips.contains(stake) else self._chips.split_off(amount)[1]
        else:
            amount = int(stake)
            if amount < 0:
                raise ValueError("Cannot withdraw a negative amount")
            if amount > self.total:
                raise InsufficientChips(f"Need {amount} credits but only {self.total} available")
            remaining = self._chips.split_off(amount)[1]
        self._set(remaining)
        return amount

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
