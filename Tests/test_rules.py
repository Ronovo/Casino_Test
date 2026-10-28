import unittest

from casino.engine.bets import Outcome, format_ratio, payout
from casino.engine.cards import Card, parse_cards
from casino.rules import baccarat, blackjack, gtn, poker, roulette


def cards(*texts):
    return parse_cards(texts)


class BetMathTests(unittest.TestCase):
    def test_payouts(self):
        self.assertEqual(payout(10, Outcome.WIN, 1), 20)
        self.assertEqual(payout(10, Outcome.WIN, 1.5), 25)
        self.assertEqual(payout(3, Outcome.WIN, 1.5), 7)  # 4.5 winnings rounds down
        self.assertEqual(payout(10, Outcome.PUSH), 10)
        self.assertEqual(payout(10, Outcome.LOSE, 35), 0)

    def test_format_ratio(self):
        self.assertEqual(format_ratio(1.5), "3:2")
        self.assertEqual(format_ratio(35), "35:1")
        self.assertEqual(format_ratio(50_000_000), "50,000,000:1")


class CardTests(unittest.TestCase):
    def test_parse_legacy_ten(self):
        self.assertEqual(Card.parse("1H"), Card("10", "H"))
        self.assertEqual(Card.parse("th"), Card("10", "H"))
        self.assertEqual(str(Card.parse("AS")), "A♠")
        self.assertEqual(Card.parse("QD").name, "Queen of Diamonds")


class BlackjackRuleTests(unittest.TestCase):
    def test_ace_is_one_or_eleven(self):
        self.assertEqual(blackjack.hand_value(cards("AS", "6H")), (17, True))
        self.assertEqual(blackjack.hand_value(cards("AS", "AH", "9D")), (21, True))
        self.assertEqual(blackjack.hand_value(cards("AS", "5H", "KD")), (16, False))
        self.assertEqual(blackjack.hand_value(cards("6S", "5H", "AD")), (12, False))

    def test_natural_and_bust(self):
        self.assertTrue(blackjack.is_natural(cards("AS", "KD")))
        self.assertFalse(blackjack.is_natural(cards("7S", "7D", "7H")))
        self.assertTrue(blackjack.is_bust(cards("KS", "QD", "2H")))

    def test_dealer_draws_to_17(self):
        self.assertTrue(blackjack.dealer_should_hit(cards("10S", "6H")))
        self.assertFalse(blackjack.dealer_should_hit(cards("10S", "7H")))
        self.assertFalse(blackjack.dealer_should_hit(cards("AS", "6H")))
        self.assertTrue(blackjack.dealer_should_hit(cards("AS", "6H"), hit_soft_17=True))
        self.assertFalse(blackjack.dealer_should_hit(cards("10S", "7H"), hit_soft_17=True))

    def test_compare_and_split(self):
        self.assertIs(blackjack.compare(cards("10S", "9H"), cards("10D", "8C")), Outcome.WIN)
        self.assertIs(blackjack.compare(cards("10S", "9H", "5D"), cards("10D", "8C", "9S")), Outcome.LOSE)
        self.assertIs(blackjack.compare(cards("10S", "8H"), cards("10D", "8C", "9S")), Outcome.WIN)
        self.assertIs(blackjack.compare(cards("10S", "8H"), cards("9D", "9C")), Outcome.PUSH)
        self.assertTrue(blackjack.can_split(cards("8S", "8H")))
        self.assertFalse(blackjack.can_split(cards("KS", "QH")))
        self.assertTrue(blackjack.has_black_jack(cards("JC", "AH")))
        self.assertFalse(blackjack.has_black_jack(cards("JH", "AH")))


class PokerRuleTests(unittest.TestCase):
    def rank(self, *texts):
        return poker.best_hand(cards(*texts))

    def test_categories(self):
        expectations = {
            ("AS", "KS", "QS", "JS", "10S"): 10,
            ("9H", "8H", "7H", "6H", "5H"): 9,
            ("AS", "AC", "AD", "AH", "3C"): 8,
            ("QS", "QC", "QH", "AS", "AC"): 7,
            ("2S", "6S", "8S", "JS", "KS"): 6,
            ("10S", "9C", "8D", "7H", "6S"): 5,
            ("AS", "2C", "3D", "4H", "5S"): 5,
            ("AS", "AC", "AD", "9H", "3C"): 4,
            ("AS", "AC", "3D", "3H", "9C"): 3,
            ("AS", "AC", "4D", "7H", "9C"): 2,
            ("AS", "JC", "4D", "7H", "9C"): 1,
        }
        for hand, category in expectations.items():
            with self.subTest(hand=hand):
                self.assertEqual(self.rank(*hand).category, category)

    def test_tiebreakers_use_kickers(self):
        self.assertGreater(self.rank("AS", "AH", "7D", "8C", "9S"), self.rank("2S", "2H", "KD", "QC", "JS"))
        self.assertGreater(self.rank("KS", "KH", "AD", "3C", "2S"), self.rank("KD", "KC", "QD", "3H", "2H"))
        self.assertGreater(self.rank("10S", "JC", "QD", "KH", "AS"), self.rank("9S", "10C", "JD", "QH", "KS"))
        self.assertGreater(self.rank("6S", "2C", "3D", "4H", "5S"), self.rank("AS", "2C", "3D", "4H", "5S"))
        self.assertEqual(self.rank("2S", "3D", "AS", "AH", "AD", "AC", "KS"),
                         self.rank("2H", "3H", "AS", "AH", "AD", "AC", "KS"))

    def test_seven_card_flush_with_six_suited(self):
        best = self.rank("2S", "4S", "6S", "8S", "JS", "KS", "3D")
        self.assertEqual(best.category, 6)
        self.assertEqual(best.tiebreak, (13, 11, 8, 6, 4))

    def test_descriptions(self):
        self.assertEqual(self.rank("KS", "KH", "AD", "3C", "2S").description, "Pair of Kings")
        self.assertEqual(self.rank("QS", "QC", "QH", "5S", "5C").description, "Full House, Queens over 5s")
        self.assertEqual(poker.describe_cards(cards("7S", "7D")), "Pair of 7s")

    def test_dealer_qualifies_and_pairs_bonus(self):
        self.assertFalse(poker.dealer_qualifies(self.rank("AS", "JC", "4D", "7H", "9C")))
        self.assertTrue(poker.dealer_qualifies(self.rank("2S", "2C", "4D", "7H", "9C")))
        self.assertEqual(poker.pairs_bonus_key(cards("10H", "10D")), "10")
        self.assertEqual(poker.pairs_bonus_key(cards("AH", "AD")), "A")
        self.assertEqual(poker.pairs_bonus_key(cards("7H", "7D")), "2-9")
        self.assertIsNone(poker.pairs_bonus_key(cards("7H", "8D")))


class BaccaratRuleTests(unittest.TestCase):
    def test_card_values(self):
        self.assertEqual(baccarat.hand_total(cards("AS", "KD")), 1)
        self.assertEqual(baccarat.hand_total(cards("7S", "6D")), 3)
        self.assertEqual(baccarat.hand_total(cards("9S", "9D", "9H")), 7)

    def test_banker_tableau(self):
        self.assertTrue(baccarat.banker_draws(5, None))
        self.assertFalse(baccarat.banker_draws(6, None))
        self.assertTrue(baccarat.banker_draws(2, 8))
        self.assertFalse(baccarat.banker_draws(3, 8))
        self.assertTrue(baccarat.banker_draws(3, 9))
        self.assertTrue(baccarat.banker_draws(4, 2))
        self.assertFalse(baccarat.banker_draws(4, 1))
        self.assertTrue(baccarat.banker_draws(5, 4))
        self.assertFalse(baccarat.banker_draws(5, 3))
        self.assertTrue(baccarat.banker_draws(6, 7))
        self.assertFalse(baccarat.banker_draws(6, 5))
        self.assertFalse(baccarat.banker_draws(7, 0))

    def test_banker_natural_stops_player_drawing(self):
        deck = iter(cards("2S", "9D", "3H", "KC", "5S"))
        coup = baccarat.play_coup(lambda: next(deck))
        self.assertEqual(len(coup.player), 2)
        self.assertEqual(coup.winner, "banker")

    def test_dragon7_and_panda8(self):
        deck = iter(cards("2S", "2D", "3H", "2H", "5C", "3S"))
        coup = baccarat.play_coup(lambda: next(deck))
        self.assertTrue(coup.dragon7)
        deck = iter(cards("2S", "KD", "3H", "7C", "3C"))
        coup = baccarat.play_coup(lambda: next(deck))
        self.assertTrue(coup.panda8)


class GuessTheNumberRuleTests(unittest.TestCase):
    PAY = {"exact": 5, "close": 2, "high_low": 1, "even_odd": 1, "range": 2, "lucky_1": 3, "lucky_2": 1}
    EASY = gtn.Difficulty("Easy", 10)
    MEDIUM = gtn.Difficulty("Medium", 100)
    IMPOSSIBLE = gtn.Difficulty("Impossible", 100_000_000)

    def test_pick_exact_and_close(self):
        self.assertEqual(gtn.resolve("pick", 4, 4, self.EASY, self.PAY).ratio, 5)
        self.assertEqual(gtn.resolve("pick", 5, 4, self.EASY, self.PAY).ratio, 2)
        self.assertIs(gtn.resolve("pick", 6, 4, self.EASY, self.PAY).outcome, Outcome.LOSE)
        self.assertEqual(gtn.resolve("pick", 58, 50, self.MEDIUM, self.PAY).ratio, 2)
        self.assertEqual(gtn.resolve("pick", 7, 7, self.IMPOSSIBLE, self.PAY).ratio, 50_000_000)

    def test_high_low_even_odd(self):
        self.assertIs(gtn.resolve("high_low", "Low", 5, self.EASY, self.PAY).outcome, Outcome.WIN)
        self.assertIs(gtn.resolve("high_low", "High", 5, self.EASY, self.PAY).outcome, Outcome.LOSE)
        self.assertIs(gtn.resolve("even_odd", "Odd", 7, self.EASY, self.PAY).outcome, Outcome.WIN)

    def test_range_covers_exactly_range_size_numbers(self):
        hits = [n for n in range(1, 101) if gtn.resolve("range", 10, n, self.MEDIUM, self.PAY).outcome is Outcome.WIN]
        self.assertEqual(hits, list(range(10, 30)))
        self.assertEqual(gtn.resolve("range", 10, 12, self.MEDIUM, self.PAY).ratio, 2)

    def test_lucky(self):
        self.assertEqual(gtn.resolve("lucky", (3, 8), 3, self.MEDIUM, self.PAY).ratio, 30)
        self.assertEqual(gtn.resolve("lucky", (3, 8), 8, self.MEDIUM, self.PAY).ratio, 10)


class RouletteRuleTests(unittest.TestCase):
    def test_wheels(self):
        self.assertEqual(len(roulette.EUROPEAN_WHEEL), 37)
        self.assertEqual(len(set(roulette.AMERICAN_WHEEL)), 38)
        self.assertEqual(set(roulette.EUROPEAN_WHEEL), {str(n) for n in range(37)})

    def test_bets(self):
        self.assertTrue(roulette.wins("straight", "17", "17"))
        self.assertTrue(roulette.wins("red_black", "Black", "17"))
        self.assertTrue(roulette.wins("odd_even", "Odd", "17"))
        self.assertTrue(roulette.wins("low_high", "Low", "17"))
        self.assertTrue(roulette.wins("dozen", 2, "17"))
        self.assertTrue(roulette.wins("column", 2, "17"))
        self.assertTrue(roulette.wins("column", 3, "36"))
        self.assertFalse(roulette.wins("red_black", "Red", "0"))
        self.assertTrue(roulette.wins("straight", "00", "00"))
        self.assertEqual(roulette.color_of("00"), "green")


if __name__ == "__main__":
    unittest.main()
