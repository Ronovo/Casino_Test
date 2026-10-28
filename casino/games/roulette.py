"""Roulette on a European (single zero) or American (double zero) wheel."""
from __future__ import annotations

from typing import Any, Mapping

from casino.engine.bets import Bet, BetError, Outcome, add_stake, settle
from casino.engine.game import Game, Round, pay_rows, pay_section
from casino.engine.session import Session
from casino.rules import roulette as rules

BET_LABELS = {"straight": "Straight up", "red_black": "Red/Black", "odd_even": "Odd/Even",
              "low_high": "Low/High", "dozen": "Dozen", "column": "Column"}
PAYTABLE_LABELS = (("straight", "Straight up: a single number"), ("red_black", "Red or Black"),
                   ("odd_even", "Odd or Even"), ("low_high", "Low (1-18) or High (19-36)"),
                   ("dozen", "Dozen"), ("column", "Column"))
SELECTIONS = {"red_black": ("Red", "Black"), "odd_even": ("Odd", "Even"), "low_high": ("Low", "High"),
              "dozen": (1, 2, 3), "column": (1, 2, 3)}


class RouletteRound(Round):
    def __init__(self, game: "RouletteGame", session: Session, placed: list[tuple[str, Bet]]):
        super().__init__(game, session)
        self.placed = placed
        self.pocket = session.rng.choice(game.wheel)
        settlements = []
        for kind, bet in placed:
            won = rules.wins(kind, bet.selection, self.pocket)
            settlements.append(settle(session.wallet, bet, Outcome.WIN if won else Outcome.LOSE,
                                      game.table.paytable[kind]))
            if won:
                session.unlock("Roulette_Win")
                if kind == "straight":
                    session.unlock("Roulette_Zero" if self.pocket in ("0", "00") else "Roulette_Straight")
        self.finish(settlements, [f"The ball lands on {self.pocket} {rules.color_of(self.pocket)}."])

    @property
    def staked(self) -> int:
        return sum(bet.amount for _, bet in self.placed)

    def table_view(self) -> dict[str, Any]:
        return {"pocket": self.pocket, "color": rules.color_of(self.pocket)}


class RouletteGame(Game):
    game_key = "roulette"
    display_name = "Roulette"

    @property
    def wheel(self) -> tuple[str, ...]:
        return rules.WHEELS[self.setting("wheel", "european")]

    def rules_pages(self) -> list[list[str]]:
        zeros = "0 and 00" if "00" in self.wheel else "a single 0"
        return [
            [f"The wheel has {len(self.wheel)} pockets: 1-36 in red and black, plus {zeros} in green.",
             "Place any number of bets, then spin. Every bet on the winning pocket pays.",
             "The green zero pockets only pay straight-up bets on that zero. Every other bet loses."],
        ]

    def paytable(self) -> list[dict[str, Any]]:
        pay = self.table.paytable
        return [pay_section(None, pay_rows((label, pay[kind]) for kind, label in PAYTABLE_LABELS))]

    def layout(self) -> dict[str, Any]:
        return {"wheel": list(self.wheel), "red": sorted(rules.RED_NUMBERS)}

    def start(self, session: Session, data: Mapping[str, Any]) -> RouletteRound:
        bets = data.get("bets")
        if not isinstance(bets, list) or not bets:
            raise BetError("Place at least one bet first.")
        placed: dict[tuple[str, Any], Bet] = {}
        for item in bets:
            if not isinstance(item, Mapping):
                raise BetError("That bet isn't on the board.")
            kind, selection = item.get("kind"), item.get("selection")
            if not isinstance(kind, str) or type(selection) not in (str, int):
                raise BetError("That bet isn't on the board.")
            valid = self.wheel if kind == "straight" else SELECTIONS.get(kind, ())
            if selection not in valid:
                raise BetError("That bet isn't on the board.")
            bet = placed.setdefault((kind, selection), Bet(BET_LABELS[kind], 0, selection))
            add_stake(bet, item.get("amount"), self.table.min_bet, self.table.max_bet)
        self.take_stakes(session, sum(bet.amount for bet in placed.values()))
        return RouletteRound(self, session, [(kind, bet) for (kind, _), bet in placed.items()])
