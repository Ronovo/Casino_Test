"""Full rounds played through each game's start/act interface with stacked shoes and fixed numbers."""
import unittest

from casino.config import TABLES_DIR
from casino.engine.bets import BetError
from casino.games import load_games
from casino.games.baccarat import BaccaratGame
from casino.games.blackjack import BlackjackGame
from casino.games.gtn import GuessTheNumberGame
from casino.games.poker import UltimateHoldemGame
from casino.games.roulette import RouletteGame
from Tests.helpers import DatabaseTestCase, FixedRng, play, table


class RegistryTests(unittest.TestCase):
    def test_every_table_loads_with_a_unique_key(self):
        games = load_games(TABLES_DIR)
        self.assertEqual(len({g.table.key for g in games}), len(games))
        for game in games:
            info = game.info()
            self.assertTrue(info["rules"])
            self.assertTrue(info["paytable"])


class BlackjackGameTests(DatabaseTestCase):
    def play(self, bet, cards, *actions, credits=1000, table_file="01_blackjack_classic.json"):
        session = self.make_session(credits=credits, cards=cards)
        current = play(BlackjackGame(table(table_file)), session, {"bet": bet}, *actions)
        return session, current

    def test_natural_pays_classic_2_to_1(self):
        session, _ = self.play(10, ["AS", "9H", "KH", "7D"])
        self.assertEqual(session.wallet.total, 1020)
        self.assertTrue({"Blackjack_21", "Blackjack_Win"} <= self.unlocked(session))

    def test_natural_with_black_jack_pays_3_to_1(self):
        self.assertEqual(self.play(10, ["AS", "9H", "JS", "7D"])[0].wallet.total, 1030)

    def test_high_roller_natural_pays_3_to_2(self):
        session, _ = self.play(100, ["AS", "9H", "JS", "7D"], table_file="02_blackjack_high_roller.json")
        self.assertEqual(session.wallet.total, 1150)

    def test_both_naturals_push(self):
        self.assertEqual(self.play(10, ["AS", "AH", "KH", "KD"])[0].wallet.total, 1000)

    def test_dealer_natural_beats_player(self):
        self.assertEqual(self.play(10, ["9S", "AH", "9H", "KD"])[0].wallet.total, 990)

    def test_stand_and_dealer_busts(self):
        session, _ = self.play(10, ["10S", "9C", "6H", "7D", "10C"], "stand")
        self.assertEqual(session.wallet.total, 1010)
        self.assertEqual(self.db.get_stats(session.character.id)["blackjack"]["wins"], 1)

    def test_double_down_pays_on_doubled_stake_only(self):
        # 11 doubles into 21 against 17: 20 staked, classic 21 pays 2:1 -> +40
        session, _ = self.play(10, ["5S", "10C", "6H", "7D", "10H"], "double")
        self.assertEqual(session.wallet.total, 1040)
        self.assertIn("Blackjack_Double_Win", self.unlocked(session))

    def test_player_bust_skips_dealer(self):
        session, current = self.play(10, ["10S", "10C", "6H", "7D", "10H"], "hit")
        self.assertEqual(session.wallet.total, 990)
        self.assertEqual(len(current.dealer), 2)

    def test_split_plays_two_hands(self):
        # 8+3=11 stands and loses to 17; 8+10=18 stands and wins -> net 0
        session, _ = self.play(10, ["8S", "10C", "8H", "7D", "3C", "10D"], "split", "stand", "stand")
        self.assertEqual(session.wallet.total, 1000)
        self.assertIn("Blackjack_Split", self.unlocked(session))

    def test_surrender_returns_half(self):
        self.assertEqual(self.play(10, ["10S", "10C", "6H", "7D"], "surrender")[0].wallet.total, 995)

    def test_double_not_offered_when_unaffordable(self):
        session = self.make_session(credits=10, cards=["10S", "10C", "6H", "7D"])
        current = BlackjackGame(table("01_blackjack_classic.json")).start(session, {"bet": 10})
        self.assertNotIn("double", [action["id"] for action in current.actions()])
        with self.assertRaises(BetError):
            current.act("double")

    def test_hole_card_is_hidden_until_the_round_ends(self):
        session = self.make_session(cards=["10S", "9C", "6H", "7D", "10C"])
        current = BlackjackGame(table("01_blackjack_classic.json")).start(session, {"bet": 10})
        self.assertEqual(current.view()["dealer"]["cards"], [{"rank": "9", "suit": "C"}, None])
        current.act("stand")
        self.assertNotIn(None, current.view()["dealer"]["cards"])


class PokerGameTests(DatabaseTestCase):
    def play(self, bets, cards, *actions, credits=10_000):
        session = self.make_session(credits=credits, cards=cards)
        play(UltimateHoldemGame(table("03_ultimate_holdem.json")), session, bets, *actions)
        return session

    def test_royal_flush_pays_blind_and_trips(self):
        # Dealer doesn't qualify: Ante pushes, Play +40, Blind 500:1 +5000, Trips 50:1 +250
        cards = ["AS", "KS", "2D", "3C", "QS", "JS", "10S", "7H", "4D"]
        session = self.play({"ante": 10, "trips": 5}, cards, "play4")
        self.assertEqual(session.wallet.total, 10_000 + 5_290)
        self.assertTrue({"Poker_Win", "Poker_Trips", "Poker_Royal", "Poker_Push_Dealer"} <= self.unlocked(session))

    def test_raise_is_actually_charged_when_losing(self):
        # Dealer's aces qualify and beat the player: Ante, Blind and the 4x Play all lose
        cards = ["2H", "7C", "AS", "AD", "KD", "9S", "4C", "JH", "3S"]
        self.assertEqual(self.play({"ante": 10}, cards, "play4").wallet.total, 10_000 - 60)

    def test_fold_loses_ante_and_blind(self):
        cards = ["2H", "7C", "AS", "AD", "KD", "9S", "4C", "JH", "3S"]
        session = self.play({"ante": 10}, cards, "check", "check", "fold")
        self.assertEqual(session.wallet.total, 10_000 - 20)
        self.assertIn("Poker_Lose_Walk2", self.unlocked(session))

    def test_non_qualifying_dealer_still_beats_play_and_blind(self):
        cards = ["2H", "3C", "AS", "KD", "9S", "8D", "6C", "JH", "4S"]
        self.assertEqual(self.play({"ante": 10}, cards, "check", "check", "play1").wallet.total, 10_000 - 20)

    def test_pocket_pair_pays_pairs_bonus(self):
        # Queens beat ace-high: Ante push, Play +40, Blind push, Pairs 8:1 +40
        cards = ["QH", "QD", "2C", "7S", "AS", "9D", "5C", "3H", "JC"]
        self.assertEqual(self.play({"ante": 10, "pairs": 5}, cards, "play4").wallet.total, 10_000 + 80)

    def test_pocket_tens_pay_pairs_bonus(self):
        cards = ["10H", "10D", "2C", "7S", "AS", "9D", "5C", "3H", "JC"]
        self.assertEqual(self.play({"ante": 10, "pairs": 5}, cards, "play4").wallet.total, 10_000 + 40 + 25)

    def test_tie_pushes_everything(self):
        cards = ["2H", "3D", "2S", "3H", "AS", "AH", "AD", "AC", "KS"]
        session = self.play({"ante": 10}, cards, "play4")
        self.assertEqual(session.wallet.total, 10_000)
        self.assertIn("Poker_Push_Tie", self.unlocked(session))

    def test_side_bets_do_not_carry_over_to_the_next_hand(self):
        cards = ["2H", "7C", "AS", "AD", "KD", "9S", "4C", "JH", "3S"]
        session = self.make_session(credits=10_000, cards=cards)
        game = UltimateHoldemGame(table("03_ultimate_holdem.json"))
        play(game, session, {"ante": 10, "trips": 5}, "play4")
        play(game, session, {"ante": 10}, "play4")
        self.assertEqual(session.wallet.total, 10_000 - 65 - 60)

    def test_leaving_before_dealing_costs_nothing(self):
        session = self.make_session(credits=10_000)
        UltimateHoldemGame(table("03_ultimate_holdem.json")).leave(session)
        self.assertEqual(session.wallet.total, 10_000)
        self.assertIn("Poker_Lose_Walk1", self.unlocked(session))

    def test_dealer_and_unseen_board_cards_stay_hidden(self):
        cards = ["2H", "7C", "AS", "AD", "KD", "9S", "4C", "JH", "3S"]
        session = self.make_session(credits=10_000, cards=cards)
        current = UltimateHoldemGame(table("03_ultimate_holdem.json")).start(session, {"ante": 10})
        view = current.view()
        self.assertEqual(view["dealer"], [None, None])
        self.assertEqual(view["board"], [None] * 5)
        current.act("check")
        self.assertEqual(current.view()["board"][3:], [None, None])
        self.assertIsNotNone(current.view()["board"][2])


class BaccaratGameTests(DatabaseTestCase):
    def play(self, bets, cards):
        session = self.make_session(cards=cards)
        play(BaccaratGame(table("05_baccarat.json")), session, bets)
        return session

    def test_player_natural_wins(self):
        self.assertEqual(self.play({"player": 10}, ["9S", "2H", "KH", "3D"]).wallet.total, 1010)

    def test_tie_pays_tie_bet_and_pushes_player_bet(self):
        session = self.play({"player": 10, "tie": 10}, ["9S", "9H", "KH", "KD"])
        self.assertEqual(session.wallet.total, 1080)
        self.assertIn("Baccarat_Tie", self.unlocked(session))

    def test_dragon7_needs_main_bet_and_pushes_banker(self):
        cards = ["2S", "2D", "3H", "2H", "5C", "3S"]
        session = self.make_session(cards=cards)
        game = BaccaratGame(table("05_baccarat.json"))
        with self.assertRaisesRegex(BetError, "Bonus bets need a Player or Banker bet too."):
            game.start(session, {"dragon7": 10})
        self.assertEqual(session.wallet.total, 1000)
        play(game, session, {"dragon7": 10, "banker": 10})
        self.assertEqual(session.wallet.total, 1400)
        self.assertIn("Baccarat_Dragon7", self.unlocked(session))

    def test_panda8(self):
        self.assertEqual(self.play({"player": 10, "panda8": 10}, ["2S", "KD", "3H", "7C", "3C"]).wallet.total, 1260)


class GuessTheNumberGameTests(DatabaseTestCase):
    def play(self, difficulty, bets, number, credits=1000):
        session = self.make_session(credits=credits, rng=FixedRng(number))
        play(GuessTheNumberGame(table("06_guess_the_number.json")), session,
             {"difficulty": difficulty, "bets": bets})
        return session

    def test_every_bet_type_on_easy(self):
        bets = {"pick": {"selection": 7, "amount": 10},          # exact 5:1        +50
                "high_low": {"selection": "High", "amount": 10},  # high 1:1         +10
                "even_odd": {"selection": "Even", "amount": 10},  # even loses       -10
                "range": {"selection": 6, "amount": 10},          # range 6-7 2:1    +20
                "lucky": {"selection": [3, 7], "amount": 10}}     # lucky #2 1:1     +10
        session = self.play("Easy", bets, 7)
        self.assertEqual(session.wallet.total, 1080)
        self.assertTrue({"GTN_Win", "GTN_Exact"} <= self.unlocked(session))

    def test_impossible_pays_its_real_odds(self):
        session = self.play("Impossible", {"pick": {"selection": 12_345_678, "amount": 1}}, 12_345_678)
        self.assertEqual(session.wallet.total, 1000 + 50_000_000)
        self.assertTrue({"GTN_Impossible", "Money_1000000"} <= self.unlocked(session))


class RouletteGameTests(DatabaseTestCase):
    def play(self, bets, pocket, table_file="07_roulette_european.json"):
        session = self.make_session(rng=FixedRng(pocket))
        play(RouletteGame(table(table_file)), session, {"bets": bets})
        return session

    def test_straight_red_and_column(self):
        bets = [{"kind": "straight", "selection": "17", "amount": 10},
                {"kind": "red_black", "selection": "Red", "amount": 10},
                {"kind": "column", "selection": 2, "amount": 10}]
        session = self.play(bets, "17")
        self.assertEqual(session.wallet.total, 1000 + 350 - 10 + 20)
        self.assertIn("Roulette_Straight", self.unlocked(session))

    def test_repeat_bets_on_same_selection_merge(self):
        bets = [{"kind": "red_black", "selection": "Black", "amount": 10},
                {"kind": "red_black", "selection": "Black", "amount": 5}]
        self.assertEqual(self.play(bets, "17").wallet.total, 1015)

    def test_double_zero(self):
        bets = [{"kind": "straight", "selection": "00", "amount": 5},
                {"kind": "red_black", "selection": "Red", "amount": 5}]
        session = self.play(bets, "00", "08_roulette_american.json")
        self.assertEqual(session.wallet.total, 1000 + 175 - 5)
        self.assertIn("Roulette_Zero", self.unlocked(session))


if __name__ == "__main__":
    unittest.main()
