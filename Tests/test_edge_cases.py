"""Regression tests for edge cases found by the soak tests."""
import random

from casino.config import TABLES_DIR
from casino.engine.bets import BetError
from casino.games import load_games
from casino.games.blackjack import BlackjackGame
from casino.games.poker import UltimateHoldemGame
from casino.games.roulette import RouletteGame
from casino.web.floor import Floor
from Tests.helpers import DatabaseTestCase, FixedRng, play, table


class BlackjackEdgeCases(DatabaseTestCase):
    def game(self):
        return BlackjackGame(table("01_blackjack.json"))

    def test_two_card_21_after_a_split_is_not_called_blackjack(self):
        # Aces split and each catches a ten: two 21s that pay 1:1 as 21s, not 3:2 as naturals.
        session = self.make_session(cards=["AS", "9C", "AH", "7D", "KC", "QD", "10H"])
        current = play(self.game(), session, {"bet": 10}, "split")
        for hand in current.view()["hands"]:
            self.assertEqual(hand["label"], "21")
            self.assertEqual(hand["state"], "")
        self.assertEqual(session.wallet.total, 1000 + 20)

    def test_surrender_is_not_offered_when_half_the_bet_is_nothing(self):
        session = self.make_session(cards=["10S", "10C", "6H", "7D", "5C"])
        current = self.game().start(session, {"bet": 1})
        self.assertNotIn("surrender", [action["id"] for action in current.actions()])

    def test_surrender_on_an_odd_bet_rounds_in_the_houses_favor(self):
        session = self.make_session(cards=["10S", "10C", "6H", "7D"])
        play(self.game(), session, {"bet": 5}, "surrender")
        self.assertEqual(session.wallet.total, 1000 - 3)

    def test_split_then_double_on_both_hands_balances(self):
        # 8,8 split; each hand doubles. Hand 1: 8+3+10=21 wins 20. Hand 2: 8+2+5=15 loses 20 to 17.
        session = self.make_session(cards=["8S", "10C", "8H", "7D", "3C", "2D", "10H", "5S"])
        current = play(self.game(), session, {"bet": 10}, "split", "double", "double")
        self.assertEqual(current.staked, 40)
        self.assertEqual(session.wallet.total, 1000 + 20 - 20)

    def test_split_needs_the_chips_for_a_second_bet(self):
        session = self.make_session(credits=15, cards=["8S", "10C", "8H", "7D", "3C", "2D"])
        current = self.game().start(session, {"bet": 10})
        self.assertNotIn("split", [action["id"] for action in current.actions()])

    def test_ten_and_face_card_split_like_a_pair(self):
        session = self.make_session(cards=["10S", "10C", "KH", "7D"])
        current = self.game().start(session, {"bet": 10})
        self.assertIn("split", [action["id"] for action in current.actions()])

    def test_split_aces_get_one_card_each_and_are_not_split_again(self):
        # Each Ace catches another Ace; the hands are done at 12 apiece and the dealer's 16 draws to 21.
        session = self.make_session(cards=["AS", "7C", "AH", "9D", "AD", "AC", "5S"])
        current = play(self.game(), session, {"bet": 10}, "split")
        self.assertEqual([len(hand.cards) for hand in current.hands], [2, 2])
        self.assertEqual(session.wallet.total, 980)

    def test_dealer_hits_soft_17(self):
        current = play(self.game(), self.make_session(cards=["10S", "6D", "9H", "AC", "4C"]), {"bet": 100}, "stand")
        self.assertEqual(len(current.dealer), 3)
        self.assertIn("Dealer draws 4♣: 21.", current.notes)

    def test_insurance_is_only_offered_against_an_ace(self):
        session = self.make_session(cards=["9S", "KH", "8H", "7D"])
        current = self.game().start(session, {"bet": 10})
        self.assertEqual([action["id"] for action in current.actions()], ["hit", "stand", "double", "surrender"])
        with self.assertRaises(BetError):
            current.act("insurance")
        self.assertEqual(session.wallet.total, 990)

    def test_insurance_needs_a_bet_to_halve_and_the_chips_to_pay_for_it(self):
        for credits, bet in ((1000, 1), (10, 10)):
            with self.subTest(credits=credits, bet=bet):
                session = self.make_session(credits=credits, cards=["9S", "AH", "9H", "7D"], name=f"{bet}-{credits}")
                current = self.game().start(session, {"bet": bet})
                self.assertEqual([action["id"] for action in current.actions()], ["no_insurance"])
                with self.assertRaises(BetError):
                    current.act("insurance")

    def test_hole_card_stays_hidden_while_insurance_is_offered(self):
        session = self.make_session(cards=["9S", "AH", "9H", "KD"])
        current = self.game().start(session, {"bet": 10})
        view = current.view()
        self.assertEqual(view["dealer"]["cards"], [{"rank": "A", "suit": "H"}, None])
        self.assertEqual(view["dealer"]["label"], "Showing 11")
        self.assertNotIn(repr({"rank": "K", "suit": "D"}), repr(view))
        self.assertEqual([action["label"] for action in view["actions"]], ["Insurance (+5 cr)", "No insurance"])


class PokerEdgeCases(DatabaseTestCase):
    CARDS = ["2H", "7C", "AS", "AD", "KD", "9S", "4C", "JH", "3S"]

    def game(self):
        return UltimateHoldemGame(table("03_ultimate_holdem.json"))

    def test_cannot_deal_in_without_chips_left_for_a_play_bet(self):
        # 100 cr on Ante + Blind 50/50 would leave nothing to bet with, so the only move would be to fold.
        session = self.make_session(credits=100, cards=self.CARDS)
        with self.assertRaisesRegex(BetError, "Play bet"):
            self.game().start(session, {"ante": 50})
        self.assertEqual(session.wallet.total, 100)
        current = self.game().start(session, {"ante": 33})
        current.act("check")
        current.act("check")
        self.assertIn("play1", [a["id"] for a in current.actions()])

    def test_buy_in_covers_ante_blind_and_play(self):
        self.assertEqual(self.game().min_buy_in, 3)

    def test_only_affordable_raises_are_offered(self):
        session = self.make_session(credits=65, cards=self.CARDS)
        current = self.game().start(session, {"ante": 10})
        self.assertEqual([a["id"] for a in current.actions()], ["check", "play4", "play3"])
        session = self.make_session(credits=55, cards=self.CARDS, name="Shorter")
        current = self.game().start(session, {"ante": 10})
        self.assertEqual([a["id"] for a in current.actions()], ["check", "play3"])

    def test_side_bets_pay_after_a_fold(self):
        # Pocket queens: Pairs Bonus 8:1 pays even though the hand is folded.
        cards = ["QH", "QD", "2C", "7S", "AS", "9D", "5C", "3H", "JC"]
        session = self.make_session(credits=1000, cards=cards)
        play(self.game(), session, {"ante": 10, "pairs": 5}, "check", "check", "fold")
        self.assertEqual(session.wallet.total, 1000 - 20 + 40)


class RouletteEdgeCases(DatabaseTestCase):
    def test_repeat_bets_on_one_selection_cannot_beat_the_table_maximum(self):
        game = RouletteGame(table("07_roulette.json"))
        session = self.make_session(credits=100_000, rng=FixedRng("17"))
        chunk = {"kind": "straight", "selection": "17", "amount": game.table.max_bet}
        with self.assertRaisesRegex(BetError, "maximum"):
            game.start(session, {"bets": [chunk, chunk, chunk]})
        self.assertEqual(session.wallet.total, 100_000)

    def test_zero_only_pays_straight_up(self):
        game = RouletteGame(table("07_roulette.json"))
        session = self.make_session(rng=FixedRng("0"))
        bets = [{"kind": kind, "selection": selection, "amount": 5}
                for kind, selection in (("red_black", "Red"), ("red_black", "Black"), ("odd_even", "Even"),
                                        ("low_high", "Low"), ("dozen", 1), ("column", 1), ("straight", "0"))]
        play(game, session, {"bets": bets})
        self.assertEqual(session.wallet.total, 1000 - 30 + 175)


class RandomnessEdgeCases(DatabaseTestCase):
    def test_live_tables_do_not_use_a_predictable_generator(self):
        games = load_games(TABLES_DIR)
        character = self.make_session().character
        seat = Floor(self.db, games).seat(character)
        self.assertIsInstance(seat.session.rng, random.SystemRandom)
