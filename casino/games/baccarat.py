"""EZ Baccarat: commission-free Punto Banco with Dragon 7 and Panda 8 bonus bets."""
from __future__ import annotations

from typing import Any, Mapping

from casino.engine.bets import Bet, BetError, Outcome, Settlement, read_stake, settle
from casino.engine.cards import cards_view
from casino.engine.chips import fmt_credits
from casino.engine.game import Game, Round, pay_rows, pay_section
from casino.engine.session import Session
from casino.rules import baccarat as rules

BET_TYPES = (("player", "Player"), ("banker", "Banker"), ("tie", "Tie"),
             ("dragon7", "Dragon 7 bonus"), ("panda8", "Panda 8 bonus"))
MAIN_BETS = ("player", "banker", "tie")
WIN_ACHIEVEMENTS = {"player": "Baccarat_Win", "banker": "Baccarat_Win", "tie": "Baccarat_Tie",
                    "dragon7": "Baccarat_Dragon7", "panda8": "Baccarat_Panda8"}
WINNER_NOTES = {"player": "Player wins!", "banker": "Banker wins!", "tie": "It's a tie!"}


class BaccaratRound(Round):
    def __init__(self, game: "BaccaratGame", session: Session, stakes: dict[str, int]):
        super().__init__(game, session)
        self.stakes = stakes
        shoe = session.new_shoe(int(game.setting("decks", 8)))
        self.coup = rules.play_coup(shoe.draw)
        settlements = [self._settle(key, label) for key, label in BET_TYPES if stakes[key]]
        self.finish(settlements, [*self.coup.log, WINNER_NOTES[self.coup.winner]])

    @property
    def staked(self) -> int:
        return sum(self.stakes.values())

    def _settle(self, key: str, label: str) -> Settlement:
        coup, session = self.coup, self.session
        if key in ("player", "banker"):
            if coup.winner == "tie":
                outcome = Outcome.PUSH
            elif coup.winner != key:
                outcome = Outcome.LOSE
            elif key == "banker" and coup.dragon7 and self.game.ez_rules:
                outcome = Outcome.PUSH
            else:
                outcome = Outcome.WIN
        elif key == "tie":
            outcome = Outcome.WIN if coup.winner == "tie" else Outcome.LOSE
        else:
            outcome = Outcome.WIN if getattr(coup, key) else Outcome.LOSE

        if outcome is Outcome.WIN:
            session.unlock(WIN_ACHIEVEMENTS[key])
        return settle(session.wallet, Bet(label, self.stakes[key]), outcome, self.game.table.paytable[key])

    def table_view(self) -> dict[str, Any]:
        coup = self.coup
        return {"player": {"cards": cards_view(coup.player), "total": coup.player_total},
                "banker": {"cards": cards_view(coup.banker), "total": coup.banker_total},
                "winner": coup.winner, "stakes": self.stakes}


class BaccaratGame(Game):
    game_key = "baccarat"
    display_name = "Baccarat"

    @property
    def ez_rules(self) -> bool:
        return bool(self.setting("banker_push_on_dragon7", True))

    def rules_pages(self) -> list[list[str]]:
        pages = [
            ["Baccarat is James Bond's favorite game, and one of the easiest to play.",
             "Two hands are dealt, Player and Banker. You bet on which hand will be closer to 9, or on a tie.",
             "Aces count 1, cards 2-9 count their number, and 10s and face cards count 0.",
             "Only the last digit of a total counts: 7 + 6 = 13, which is worth 3.",
             f"The shoe holds {self.setting('decks', 8)} decks and is reshuffled every round."],
            ["You don't make any decisions after betting. The dealer follows fixed drawing rules:",
             "A two-card 8 or 9 is a natural. If either hand has one, nobody draws.",
             "Player draws a third card on 0-5 and stands on 6-7.",
             "Banker draws based on its total and the Player's third card (standard tableau).",
             "Player and Banker bets push on a tie."],
            ["Bonus bets need a Player or Banker bet on the same coup.",
             "Dragon 7: the Banker wins with a three-card 7.",
             "Panda 8: the Player wins with a three-card 8."],
        ]
        if self.ez_rules:
            pages[2].append("EZ rule: when the Banker wins with a three-card 7, Banker bets push instead of paying.")
        return pages

    def paytable(self) -> list[dict[str, Any]]:
        pay = self.table.paytable
        return [pay_section(None, pay_rows((label, pay[key]) for key, label in BET_TYPES))]

    def layout(self) -> dict[str, Any]:
        return {"bets": [{"key": key, "label": label} for key, label in BET_TYPES]}

    def start(self, session: Session, data: Mapping[str, Any]) -> BaccaratRound:
        table = self.table
        stakes = {key: read_stake(data.get(key), label, table.min_bet if key in MAIN_BETS else 1, table.max_bet,
                                  optional=True)
                  for key, label in BET_TYPES}
        if not any(stakes.values()):
            raise BetError("Place at least one bet first.")
        if (stakes["dragon7"] or stakes["panda8"]) and not (stakes["player"] or stakes["banker"]):
            raise BetError("Bonus bets need a Player or Banker bet too.")
        self.take_stakes(session, sum(stakes.values()))
        return BaccaratRound(self, session, stakes)
