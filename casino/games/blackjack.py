"""Blackjack: you against the dealer, with doubling, splitting up to four hands, surrender and insurance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from casino.engine.bets import Bet, Outcome, Settlement, format_ratio, read_stake, settle
from casino.engine.cards import Card, cards_view
from casino.engine.chips import fmt_credits
from casino.engine.game import Game, Round, pay_rows, pay_section
from casino.engine.session import Session
from casino.rules import blackjack as rules

MAX_HANDS = 4


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
        super().__init__(game, session, amount)
        self.shoe = session.new_shoe(game.decks)
        player = [self.shoe.draw()]
        self.dealer = [self.shoe.draw()]
        player.append(self.shoe.draw())
        self.dealer.append(self.shoe.draw())
        self.hands = [PlayerHand(player, Bet("Hand", amount))]
        self.active = 0
        self.insurance: Bet | None = None
        # With an Ace up, the dealer only checks the hole card once the player has decided on insurance.
        self.insuring = self.dealer[0].rank == "A"
        if not self.insuring:
            self._peek()

    # ------------------------------------------------------------------ player
    def actions(self) -> list[dict[str, str]]:
        if self.insuring:
            return self._insurance_actions()
        game, wallet, hand = self.game, self.session.wallet, self.hands[self.active]
        stake = fmt_credits(hand.bet.amount)
        actions = [{"id": "hit", "label": "Hit"}, {"id": "stand", "label": "Stand"}]
        two_cards = len(hand.cards) == 2
        affordable = wallet.can_afford(hand.bet.amount)
        if (two_cards and game.setting("allow_double", True) and affordable
                and (not hand.from_split or game.setting("double_after_split", True))):
            actions.append({"id": "double", "label": f"Double (+{stake})"})
        if (rules.can_split(hand.cards) and game.setting("allow_split", True) and affordable
                and len(self.hands) < MAX_HANDS):
            actions.append({"id": "split", "label": f"Split (+{stake})"})
        # Surrender returns half the bet rounded down, so a 1 credit bet would get nothing back.
        if (len(self.hands) == 1 and two_cards and game.setting("allow_surrender", True)
                and hand.bet.amount >= 2):
            actions.append({"id": "surrender", "label": "Surrender"})
        return actions

    @property
    def premium(self) -> int:
        return self.hands[0].bet.amount // 2

    def _insurance_actions(self) -> list[dict[str, str]]:
        if rules.is_natural(self.hands[0].cards):
            return [{"id": "even_money", "label": "Even money"}, {"id": "no_insurance", "label": "No thanks"}]
        actions = []
        if self.premium >= 1 and self.session.wallet.can_afford(self.premium):
            actions.append({"id": "insurance", "label": f"Insurance (+{fmt_credits(self.premium)})"})
        actions.append({"id": "no_insurance", "label": "No insurance"})
        return actions

    def perform(self, action: str) -> None:
        if action == "even_money":
            self._even_money()
            return
        if action in ("insurance", "no_insurance"):
            if action == "insurance":
                self.take(self.premium)
                self.insurance = Bet("Insurance", self.premium)
            self._peek()
            return
        hand = self.hands[self.active]
        if action == "hit":
            hand.cards.append(self.shoe.draw())
        elif action == "stand":
            hand.finished = True
        elif action == "double":
            self.take(hand.bet.amount)
            hand.bet.amount *= 2
            hand.doubled = True
            hand.cards.append(self.shoe.draw())
            hand.finished = True
        elif action == "split":
            self._split(hand)
        else:
            hand.surrendered = hand.finished = True
        self._advance()

    def _split(self, hand: PlayerHand) -> None:
        self.take(hand.bet.amount)
        split_card = hand.cards.pop()
        hand.cards.append(self.shoe.draw())
        second = PlayerHand([split_card, self.shoe.draw()], Bet("Hand", hand.bet.amount), from_split=True)
        hand.from_split = True
        self.hands.insert(self.active + 1, second)
        for number, each in enumerate(self.hands, 1):
            each.bet.name = f"Hand {number}"
        if split_card.rank == "A":
            hand.finished = second.finished = True

    def _even_money(self) -> None:
        """A natural paid 1:1 before the dealer checks the hole card."""
        self.insuring = False
        self.session.unlock("Blackjack_21")
        settlement = settle(self.session.wallet, self.hands[0].bet, Outcome.WIN, self.game.win_pays)
        self._finish([settlement], ["Blackjack! You take even money."])

    def _peek(self) -> None:
        """Check the hole card: a natural on either side ends the round at once, otherwise play goes on."""
        self.insuring = False
        dealer_natural = rules.is_natural(self.dealer)
        if self.insurance:
            outcome = Outcome.WIN if dealer_natural else Outcome.LOSE
            self.settlements.append(settle(self.session.wallet, self.insurance, outcome, 2))
        if self.dealer[0].rank == "A" and not dealer_natural:
            self.notes.append("Dealer doesn't have blackjack.")
        if dealer_natural or rules.is_natural(self.hands[0].cards):
            self._finish([self._settle_naturals()], [self._natural_note()])
        else:
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
    def _settle_naturals(self) -> Settlement:
        hand, wallet = self.hands[0], self.session.wallet
        if rules.is_natural(hand.cards) and rules.is_natural(self.dealer):
            return settle(wallet, hand.bet, Outcome.PUSH)
        if rules.is_natural(hand.cards):
            self.session.unlock("Blackjack_21")
            return settle(wallet, hand.bet, Outcome.WIN, self.game.natural_pays)
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
        return settle(wallet, hand.bet, rules.compare(hand.cards, self.dealer), self.game.win_pays)

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
        self.finish(self.settlements + settlements, self.notes + notes)

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
        return {"dealer": dealer, "hands": hands, "insurance": self.insurance.amount if self.insurance else 0}


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

    @property
    def win_pays(self) -> float:
        return self.table.paytable.get("win", 1)

    @property
    def natural_pays(self) -> float:
        return self.table.paytable.get("natural", 1.5)

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
             f"Split: turn a pair, or any two ten-value cards, into two hands with a bet each. Split again up to "
             f"{MAX_HANDS} hands; split Aces get one card each.",
             "Surrender: give up on your first two cards and get half your bet back.",
             "Insurance (dealer shows an Ace): a side bet of half your bet that pays 2:1 if the dealer has blackjack. "
             "With a natural of your own it is offered as even money.",
             "A two-card 21 is a natural. If you or the dealer has one, the round ends immediately."],
        ]

    def paytable(self) -> list[dict[str, Any]]:
        rows = pay_rows([("Win", self.win_pays), ("Natural (two-card 21, rounded down)", self.natural_pays),
                         ("Insurance", 2)])
        rows += [["Push", "bet returned"], ["Surrender", "half your bet returned"]]
        return [pay_section(None, rows)]

    def layout(self) -> dict[str, Any]:
        return {"natural": format_ratio(self.natural_pays)}

    def start(self, session: Session, data: Mapping[str, Any]) -> BlackjackRound:
        amount = read_stake(data.get("bet"), "Bet", self.table.min_bet, self.table.max_bet)
        return BlackjackRound(self, session, amount)
