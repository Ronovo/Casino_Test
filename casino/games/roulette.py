"""Roulette on the American (double zero) wheel."""
from __future__ import annotations

from typing import Any, Mapping

from casino.engine.bets import Bet, BetError, Outcome, gather_slip, settle
from casino.engine.game import Game, Round, pay_rows, pay_section
from casino.engine.session import Session
from casino.rules import roulette as rules

# kind: (bet name, paytable line, the selections it takes; a straight bet takes any pocket on the wheel)
BET_KINDS: dict[str, tuple[str, str, tuple[Any, ...] | None]] = {
    "straight": ("Straight up", "Straight up: a single number", None),
    "red_black": ("Red/Black", "Red or Black", ("Red", "Black")),
    "odd_even": ("Odd/Even", "Odd or Even", ("Odd", "Even")),
    "low_high": ("Low/High", "Low (1-18) or High (19-36)", ("Low", "High")),
    "dozen": ("Dozen", "Dozen", (1, 2, 3)),
    "column": ("Column", "Column", (1, 2, 3)),
}


class RouletteRound(Round):
    def __init__(self, game: "RouletteGame", session: Session, placed: list[tuple[str, Bet]]):
        super().__init__(game, session, sum(bet.amount for _, bet in placed))
        self.placed = placed
        self.pocket = session.rng.choice(rules.WHEEL)
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

    def table_view(self) -> dict[str, Any]:
        return {"pocket": self.pocket, "color": rules.color_of(self.pocket)}


class RouletteGame(Game):
    game_key = "roulette"
    display_name = "Roulette"

    def rules_pages(self) -> list[list[str]]:
        return [
            [f"The wheel has {len(rules.WHEEL)} pockets: 1-36 in red and black, plus 0 and 00 in green.",
             "Place any number of bets, then spin. Every bet on the winning pocket pays.",
             "The green zero pockets only pay straight-up bets on that zero. Every other bet loses."],
        ]

    def paytable(self) -> list[dict[str, Any]]:
        pay = self.table.paytable
        return [pay_section(None, pay_rows((line, pay[kind]) for kind, (_, line, _) in BET_KINDS.items()))]

    def layout(self) -> dict[str, Any]:
        return {"wheel": list(rules.WHEEL), "red": sorted(rules.RED_NUMBERS)}

    def start(self, session: Session, data: Mapping[str, Any]) -> RouletteRound:
        def spot(item: Mapping[str, Any]) -> tuple[tuple[str, Any], str, Any]:
            kind, selection = item.get("kind"), item.get("selection")
            if not isinstance(kind, str) or kind not in BET_KINDS or type(selection) not in (str, int):
                raise BetError("That bet isn't on the board.")
            name, _, selections = BET_KINDS[kind]
            if selection not in (rules.WHEEL if selections is None else selections):
                raise BetError("That bet isn't on the board.")
            return (kind, selection), name, selection

        placed = gather_slip(data.get("bets"), spot, self.table.min_bet, self.table.max_bet)
        return RouletteRound(self, session, [(kind, bet) for (kind, _), bet in placed.items()])
