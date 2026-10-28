"""Blackjack: you against the dealer, with doubling, one split and surrender."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from casino.engine.bets import Bet, Outcome, Settlement, read_stake, settle
from casino.engine.cards import Card, cards_view
from casino.engine.chips import fmt_credits
from casino.engine.game import Game, Round, pay_rows, pay_section
from casino.engine.session import Session
from casino.rules import blackjack as rules


@dataclass
class PlayerHand:
    cards: list[Card]
    bet: Bet
    from_split: bool = False
    doubled: bool = False
    surrendered: bool = False
    finished: bool = False


def total_view(cards: list[Card], from_split: bool = False) -> dict[str, Any]:
    """A hand's total for display. A two-card 21 made after a split is a plain 21, not a natural."""
    value, soft = rules.hand_value(cards)
    if rules.is_natural(cards) and not from_split:
        return {"label": "Blackjack!", "state": "blackjack"}
    if value > 21:
        return {"label": f"{value} BUST", "state": "bust"}
    return {"label": f"{value} (soft)" if soft and value < 21 else str(value), "state": ""}


class BlackjackRound(Round):
    def __init__(self, game: "BlackjackGame", session: Session, amount: int):
        super().__init__(game, session)
        self.shoe = session.new_shoe(game.decks)
        player = [self.shoe.draw()]
        self.dealer = [self.shoe.draw()]
        player.append(self.shoe.draw())
        self.dealer.append(self.shoe.draw())
        self.hands = [PlayerHand(player, Bet("Hand", amount))]
        self.active = 0

        if rules.is_natural(player) or rules.is_natural(self.dealer):
            self._finish([self._settle_naturals()], [self._natural_note()])
        else:
            self._advance()

    @property
    def staked(self) -> int:
        return sum(hand.bet.amount for hand in self.hands)

    # ------------------------------------------------------------------ player
    def actions(self) -> list[dict[str, str]]:
        game, wallet, hand = self.game, self.session.wallet, self.hands[self.active]
        stake = fmt_credits(hand.bet.amount)
        actions = [{"id": "hit", "label": "Hit"}, {"id": "stand", "label": "Stand"}]
        two_cards = len(hand.cards) == 2
        if (two_cards and game.setting("allow_double", True) and wallet.can_afford(hand.bet.amount)
                and (not hand.from_split or game.setting("double_after_split", True))):
            actions.append({"id": "double", "label": f"Double (+{stake})"})
        if (len(self.hands) == 1 and rules.can_split(hand.cards) and game.setting("allow_split", True)
                and wallet.can_afford(hand.bet.amount)):
            actions.append({"id": "split", "label": f"Split (+{stake})"})
        # Surrender returns half the bet rounded down, so a 1 credit bet would get nothing back.
        if (len(self.hands) == 1 and two_cards and game.setting("allow_surrender", True)
                and hand.bet.amount >= 2):
            actions.append({"id": "surrender", "label": "Surrender"})
        return actions

    def perform(self, action: str) -> None:
        wallet, hand = self.session.wallet, self.hands[self.active]
        if action == "hit":
            hand.cards.append(self.shoe.draw())
        elif action == "stand":
            hand.finished = True
        elif action == "double":
            wallet.withdraw(hand.bet.amount)
            hand.bet.amount *= 2
            hand.doubled = True
            hand.cards.append(self.shoe.draw())
            hand.finished = True
        elif action == "split":
            wallet.withdraw(hand.bet.amount)
            split_card = hand.cards.pop()
            hand.cards.append(self.shoe.draw())
            second = PlayerHand([split_card, self.shoe.draw()], Bet("Hand 2", hand.bet.amount), from_split=True)
            hand.bet.name, hand.from_split = "Hand 1", True
            self.hands.append(second)
            if split_card.rank == "A":
                hand.finished = second.finished = True
        else:
            hand.surrendered = hand.finished = True
        self._advance()

    def _advance(self) -> None:
        """Move to the next hand that still needs a decision, or play out the dealer when none is left."""
        for index, hand in enumerate(self.hands):
            if rules.total(hand.cards) >= 21:
                hand.finished = True
            if not hand.finished:
                self.active = index
                return
        notes = []
        if any(not hand.surrendered and not rules.is_bust(hand.cards) for hand in self.hands):
            notes = self._dealer_turn()
        self._finish([self._settle_hand(hand) for hand in self.hands], notes)

    def _dealer_turn(self) -> list[str]:
        game, dealer = self.game, self.dealer
        notes = [f"Dealer reveals {dealer[1]}: {total_view(dealer)['label']}."]
        while rules.dealer_should_hit(dealer, game.stands_on, game.hit_soft_17):
            card = self.shoe.draw()
            dealer.append(card)
            notes.append(f"Dealer draws {card}: {total_view(dealer)['label']}.")
        notes.append("Dealer busts!" if rules.is_bust(dealer) else f"Dealer stands on {rules.total(dealer)}.")
        return notes

    # ------------------------------------------------------------------ settlement
    def _natural_ratio(self, cards: list[Card]) -> float:
        pay = self.game.table.paytable
        if pay.get("black_jack_bonus") and rules.has_black_jack(cards):
            return pay["black_jack_bonus"]
        return pay.get("natural", 1.5)

    def _settle_naturals(self) -> Settlement:
        hand, wallet = self.hands[0], self.session.wallet
        if rules.is_natural(hand.cards) and rules.is_natural(self.dealer):
            return settle(wallet, hand.bet, Outcome.PUSH)
        if rules.is_natural(hand.cards):
            self.session.unlock("Blackjack_21")
            return settle(wallet, hand.bet, Outcome.WIN, self._natural_ratio(hand.cards))
        return settle(wallet, hand.bet, Outcome.LOSE)

    def _natural_note(self) -> str:
        player, dealer = rules.is_natural(self.hands[0].cards), rules.is_natural(self.dealer)
        if player and dealer:
            return "You and the dealer both have blackjack."
        return "Blackjack!" if player else "The dealer has blackjack."

    def _settle_hand(self, hand: PlayerHand) -> Settlement:
        wallet = self.session.wallet
        if hand.surrendered:
            return settle(wallet, hand.bet, Outcome.LOSE, returned=hand.bet.amount // 2)
        outcome = rules.compare(hand.cards, self.dealer)
        pay = self.game.table.paytable
        ratio = pay.get("win", 1)
        if outcome is Outcome.WIN and rules.total(hand.cards) == 21 and pay.get("twenty_one"):
            ratio = pay["twenty_one"]
        return settle(wallet, hand.bet, outcome, ratio)

    def _finish(self, settlements: list[Settlement], notes: list[str]) -> None:
        session = self.session
        outcomes = {s.outcome for s in settlements}
        if Outcome.WIN in outcomes:
            session.unlock("Blackjack_Win")
        if Outcome.LOSE in outcomes:
            session.unlock("Blackjack_Lose")
        if Outcome.PUSH in outcomes:
            session.unlock("Blackjack_Draw")
        if any(hand.doubled and s.outcome is Outcome.WIN for hand, s in zip(self.hands, settlements)):
            session.unlock("Blackjack_Double_Win")
        if len(self.hands) > 1:
            session.unlock("Blackjack_Split")
        self.finish(settlements, notes)

    # ------------------------------------------------------------------ view
    def table_view(self) -> dict[str, Any]:
        if self.finished:
            dealer = {"cards": cards_view(self.dealer), **total_view(self.dealer)}
        else:
            dealer = {"cards": cards_view(self.dealer, face_down=(1,)),
                      "label": f"Showing {rules.total(self.dealer[:1])}", "state": ""}
        hands = []
        for index, hand in enumerate(self.hands):
            status = "Surrendered" if hand.surrendered else "Doubled" if hand.doubled else ""
            hands.append({"name": hand.bet.name, "cards": cards_view(hand.cards), "bet": hand.bet.amount,
                          "status": status, "active": not self.finished and index == self.active,
                          **total_view(hand.cards, hand.from_split)})
        return {"dealer": dealer, "hands": hands}


class BlackjackGame(Game):
    game_key = "blackjack"
    display_name = "Blackjack"

    @property
    def decks(self) -> int:
        return int(self.setting("decks", 1))

    @property
    def stands_on(self) -> int:
        return int(self.setting("dealer_stands_on", 17))

    @property
    def hit_soft_17(self) -> bool:
        return bool(self.setting("dealer_hits_soft_17", False))

    def rules_pages(self) -> list[list[str]]:
        soft = "hits" if self.hit_soft_17 else "stands on"
        return [
            ["The classic duel against the house: get closer to 21 than the dealer without going over.",
             "Number cards count their number, J/Q/K count 10, and an Ace counts 1 or 11, whichever helps.",
             f"The dealer draws to {self.stands_on} and {soft} a soft 17.",
             f"The shoe holds {self.decks} deck(s) and is reshuffled every round, so card counting won't help."],
            ["After you bet, you and the dealer get two cards each. One dealer card stays face down.",
             "Hit: take another card.",
             "Stand: keep your total.",
             "Double: double your bet and take exactly one more card.",
             "Split: turn a pair into two hands with a bet each (once per round; split Aces get one card).",
             "Surrender: give up on your first two cards and get half your bet back.",
             "A two-card 21 is a natural. If you or the dealer has one, the round ends immediately."],
        ]

    def paytable(self) -> list[dict[str, Any]]:
        pay = self.table.paytable
        rows = pay_rows([("Win", pay.get("win", 1)), ("Natural (two-card 21)", pay.get("natural", 1.5))])
        if pay.get("twenty_one"):
            rows += pay_rows([("Any other winning 21", pay["twenty_one"])])
        if pay.get("black_jack_bonus"):
            rows += pay_rows([("Natural with J♠ or J♣", pay["black_jack_bonus"])])
        rows += [["Push", "bet returned"], ["Surrender", "half your bet returned"]]
        return [pay_section(None, rows)]

    def start(self, session: Session, data: Mapping[str, Any]) -> BlackjackRound:
        amount = read_stake(data.get("bet"), "Bet", self.table.min_bet, self.table.max_bet)
        self.take_stakes(session, amount)
        return BlackjackRound(self, session, amount)
