"""Ultimate Texas Hold'em: you against the dealer, with Blind, Trips and Pairs Bonus bets."""
from __future__ import annotations

from typing import Any, Mapping

from casino.engine.bets import Bet, BetError, Outcome, Settlement, read_stake, settle
from casino.engine.cards import cards_view
from casino.engine.chips import fmt_credits
from casino.engine.game import Game, Round, pay_rows, pay_section
from casino.engine.session import Session
from casino.rules import poker as rules

# (board cards showing, street name, Play bet multipliers on offer)
STREETS = ((0, "Pre-Flop", (4, 3)), (3, "The Flop", (2,)), (5, "Turn & River", (1,)))


class HoldemRound(Round):
    def __init__(self, game: "UltimateHoldemGame", session: Session, ante: int, trips: int, pairs: int):
        super().__init__(game, session, ante * 2 + trips + pairs)
        self.bets = {"ante": Bet("Ante", ante), "blind": Bet("Blind", ante)}
        if trips:
            self.bets["trips"] = Bet("Trips", trips)
        if pairs:
            self.bets["pairs"] = Bet("Pairs Bonus", pairs)
        shoe = session.new_shoe(1)
        self.player = [shoe.draw(), shoe.draw()]
        self.dealer = [shoe.draw(), shoe.draw()]
        self.board = [shoe.draw() for _ in range(5)]
        self.street = 0
        self.folded = False

    @property
    def shown(self) -> int:
        return 5 if self.finished else STREETS[self.street][0]

    def actions(self) -> list[dict[str, str]]:
        shown, _, multipliers = STREETS[self.street]
        ante = self.bets["ante"].amount
        actions = []
        if shown < 5:
            actions.append({"id": "check", "label": "Check"})
        for multiplier in multipliers:
            if self.session.wallet.can_afford(ante * multiplier):
                verb = "Raise" if shown == 0 else "Bet"
                actions.append({"id": f"play{multiplier}",
                                "label": f"{verb} {multiplier}x ({fmt_credits(ante * multiplier)})"})
        if shown == 5:
            actions.append({"id": "fold", "label": "Fold"})
        return actions

    def perform(self, action: str) -> None:
        if action == "check":
            self.street += 1
            return
        if action == "fold":
            self.folded = True
        else:
            self.bets["play"] = Bet("Play", self.bets["ante"].amount * int(action.removeprefix("play")))
            self.take(self.bets["play"].amount)
        self._showdown()

    def _showdown(self) -> None:
        session, bets = self.session, self.bets
        wallet, pay = session.wallet, self.game.table.paytable
        player_rank = rules.best_hand(self.player + self.board)
        dealer_rank = rules.best_hand(self.dealer + self.board)
        qualifies = rules.dealer_qualifies(dealer_rank)
        notes = [f"You: {player_rank.description}",
                 f"Dealer: {dealer_rank.description}" + ("" if qualifies else " (doesn't qualify, Ante pushes)")]
        settlements: list[Settlement] = []
        if self.folded:
            notes.insert(0, "You folded.")
            settlements += [settle(wallet, bets["ante"], Outcome.LOSE), settle(wallet, bets["blind"], Outcome.LOSE)]
            session.unlock("Poker_Lose_Walk2")
        elif player_rank > dealer_rank:
            blind_ratio = pay["blind"].get(player_rank.name)
            settlements += [
                settle(wallet, bets["ante"], Outcome.WIN if qualifies else Outcome.PUSH),
                settle(wallet, bets["play"], Outcome.WIN),
                settle(wallet, bets["blind"], Outcome.WIN if blind_ratio else Outcome.PUSH, blind_ratio or 1),
            ]
            session.unlock("Poker_Win")
        elif player_rank < dealer_rank:
            settlements += [
                settle(wallet, bets["ante"], Outcome.LOSE if qualifies else Outcome.PUSH),
                settle(wallet, bets["play"], Outcome.LOSE),
                settle(wallet, bets["blind"], Outcome.LOSE),
            ]
            session.unlock("Poker_Lose")
        else:
            settlements += [settle(wallet, bets[key], Outcome.PUSH) for key in ("ante", "play", "blind")]
            session.unlock("Poker_Push_Tie")
        if not self.folded and not qualifies:
            session.unlock("Poker_Push_Dealer")

        if "trips" in bets:
            ratio = pay["trips"].get(player_rank.name)
            settlements.append(settle(wallet, bets["trips"], Outcome.WIN if ratio else Outcome.LOSE, ratio or 1))
            if ratio:
                session.unlock("Poker_Trips")
        if "pairs" in bets:
            key = rules.pairs_bonus_key(self.player)
            ratio = pay["pairs"].get(key) if key else None
            settlements.append(settle(wallet, bets["pairs"], Outcome.WIN if ratio else Outcome.LOSE, ratio or 1))
            if ratio:
                session.unlock("Poker_Pairs")
        if player_rank.category == 10:
            session.unlock("Poker_Royal")
        self.finish(settlements, notes)

    def table_view(self) -> dict[str, Any]:
        shown = self.shown
        view = {"street": "Showdown" if self.finished else STREETS[self.street][1],
                "player": cards_view(self.player),
                "player_hand": rules.describe_cards(self.player + self.board[:shown]),
                "board": cards_view(self.board, face_down=range(shown, 5)),
                "dealer": cards_view(self.dealer, face_down=() if self.finished else (0, 1)),
                "dealer_hand": None,
                "bets": {key: bet.amount for key, bet in self.bets.items()}}
        if self.finished:
            view["dealer_hand"] = rules.best_hand(self.dealer + self.board).description
        return view


class UltimateHoldemGame(Game):
    game_key = "poker"
    display_name = "Ultimate Texas Hold'em"

    @property
    def min_buy_in(self) -> int:
        """Ante, Blind and the smallest Play bet."""
        return self.table.min_bet * 3

    def rules_pages(self) -> list[list[str]]:
        return [
            ["Ultimate Texas Hold'em squares you off against the dealer. Best five-card poker hand wins.",
             "You and the dealer each get two private cards and share five community cards.",
             "Your hand is the best five cards out of your two plus the five on the board.",
             f"To play, place an Ante (minimum {fmt_credits(self.table.min_bet)}). An equal Blind bet is placed "
             "automatically, and you must keep at least one more Ante's worth of chips back for a Play bet."],
            ["You get one chance to make a Play bet, and the earlier you make it, the bigger it can be:",
             "Pre-Flop: check, or raise 3x or 4x your Ante.",
             "The Flop: if you checked, check again or bet 2x your Ante.",
             "Turn & River: if you checked twice, bet 1x your Ante or fold (losing Ante and Blind).",
             "The dealer needs at least a Pair to qualify. If the dealer doesn't qualify, your Ante is returned."],
            ["Showdown:",
             "You win: Play and Ante pay 1:1. Blind pays the Blind table for a Straight or better, otherwise "
             "it pushes.",
             "You lose: Ante, Blind and Play lose (the Ante pushes if the dealer didn't qualify).",
             "Tie: everything pushes.",
             "Side bets are optional and pay on your cards alone, even if you fold or lose the hand:",
             "Trips: your final hand is Three of a Kind or better.",
             "Pairs Bonus: your two starting cards are a pair."],
        ]

    def paytable(self) -> list[dict[str, Any]]:
        pay = self.table.paytable
        return [
            pay_section("Ante and Play", [["You win", "1:1"]]),
            pay_section("Blind (when you win)", [*pay_rows(pay["blind"].items()), ["Anything less", "push"]]),
            pay_section("Trips", pay_rows(pay["trips"].items())),
            pay_section("Pairs Bonus (starting hand)",
                        pay_rows((f"Pair of {key}s", ratio) for key, ratio in pay["pairs"].items())),
        ]

    def start(self, session: Session, data: Mapping[str, Any]) -> HoldemRound:
        table = self.table
        ante = read_stake(data.get("ante"), "Ante", table.min_bet, table.max_bet)
        trips = read_stake(data.get("trips"), "Trips", maximum=table.max_bet, optional=True)
        pairs = read_stake(data.get("pairs"), "Pairs Bonus", maximum=table.max_bet, optional=True)
        needed = ante * 3 + trips + pairs
        if not session.wallet.can_afford(needed):
            raise BetError(f"Keep chips back for a Play bet: these bets need {fmt_credits(needed)} in your rack.")
        return HoldemRound(self, session, ante, trips, pairs)

    def leave(self, session: Session) -> None:
        session.unlock("Poker_Lose_Walk1")
