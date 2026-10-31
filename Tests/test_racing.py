"""Horse racing: the odds maths, bet settlement, the 40-race season and steward handicapping."""
import json
import random
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from casino.engine.bets import BetError
from casino.games.racing import HorseRacingGame, new_season
from casino.rules import racing as rules
from casino.rules.racing import Conditions, HandicapRules, Horse, Model
from Tests.helpers import DatabaseTestCase, play, table

STRENGTHS = [88.0, 85.0, 84.0, 82.0, 80.0, 79.0, 77.0, 74.0]


class RiggedRandom(random.Random):
    """Hands out scripted values from random() so a chosen horse gets the luck; everything else stays seeded."""

    def __init__(self, seed=0):
        super().__init__(seed)
        self.script = []

    def favor(self, runners, winner, second=None, third=None):
        luck = [0.05] * runners
        luck[winner] = 1 - 1e-9
        if second is not None:
            luck[second] = 1 - 1e-7
        if third is not None:
            luck[third] = 1 - 1e-5
        self.script += luck

    def random(self):
        return self.script.pop(0) if self.script else super().random()

    def getrandbits(self, k):
        # Defined so choice() and randint() draw bits directly instead of eating the scripted random() values.
        return super().getrandbits(k)


class OddsMathTests(unittest.TestCase):
    def test_probabilities_are_consistent(self):
        chances = rules.finish_probabilities(STRENGTHS, 5.0)
        for kind, total in (("win", 1), ("place", 2), ("show", 3)):
            self.assertAlmostEqual(sum(chance[kind] for chance in chances), total, places=9)
        for chance in chances:
            self.assertLess(chance["win"], chance["place"])
            self.assertLess(chance["place"], chance["show"])
        wins = [chance["win"] for chance in chances]
        self.assertEqual(wins, sorted(wins, reverse=True))

    def test_simulated_races_match_the_exact_probabilities(self):
        rng = random.Random(7)
        races = 40_000
        seen = [{"win": 0, "place": 0, "show": 0} for _ in STRENGTHS]
        for _ in range(races):
            order = rules.finishing_order(rules.run_race(STRENGTHS, 5.0, rng))
            for place, runner in enumerate(order[:3], 1):
                for kind, places in rules.BET_PLACES.items():
                    seen[runner][kind] += place <= places
        for runner, chance in enumerate(rules.finish_probabilities(STRENGTHS, 5.0)):
            for kind in rules.BET_PLACES:
                with self.subTest(runner=runner, kind=kind):
                    self.assertAlmostEqual(seen[runner][kind] / races, chance[kind], delta=0.008)

    def test_equal_horses_have_equal_chances(self):
        for chance in rules.finish_probabilities([80.0] * 8, 5.0):
            self.assertAlmostEqual(chance["win"], 1 / 8)
            self.assertAlmostEqual(chance["place"], 2 / 8)
            self.assertAlmostEqual(chance["show"], 3 / 8)

    def test_no_price_ever_favors_the_player(self):
        for margin in (0.0, 0.15, 0.3):
            for step in range(1, 1000):
                probability = step / 1000
                price = rules.offered_odds(probability, margin)
                if price is None:
                    continue
                with self.subTest(probability=probability, margin=margin):
                    self.assertIn(price, rules.ODDS_LADDER)
                    self.assertLessEqual(probability * (1 + price), 1 - margin + 1e-9)

    def test_near_certainties_are_not_priced_and_longshots_are_capped(self):
        self.assertIsNone(rules.offered_odds(0.9, 0.15))
        self.assertEqual(rules.offered_odds(0.0001, 0.15), 99)
        self.assertEqual(rules.offered_odds(0.5, 0.15), 0.6)

    def test_a_race_needs_three_runners(self):
        with self.assertRaises(ValueError):
            rules.finish_probabilities([80.0, 81.0], 5.0)


class StrengthTests(unittest.TestCase):
    def test_trip_ground_and_weight_move_the_rating(self):
        model = Model()
        stayer = Horse("s", "Stayer", 80, 1.0, 0.0, "closer", "#000")
        mudder = Horse("m", "Mudder", 80, 0.0, 1.0, "closer", "#000")
        self.assertEqual(rules.strength(stayer, Conditions(8, "Good"), 0, model), 80)
        self.assertGreater(rules.strength(stayer, Conditions(12, "Good"), 0, model),
                           rules.strength(stayer, Conditions(5, "Good"), 0, model))
        self.assertGreater(rules.strength(mudder, Conditions(8, "Heavy"), 0, model),
                           rules.strength(mudder, Conditions(8, "Firm"), 0, model))
        self.assertEqual(rules.strength(stayer, Conditions(8, "Good"), 10, model),
                         rules.strength(stayer, Conditions(8, "Good"), 0, model) - 10 * model.weight_cost)

    def test_times_follow_the_finishing_order(self):
        scores = rules.run_race(STRENGTHS, 5.0, random.Random(3))
        times = rules.race_times(scores, Conditions(8, "Good"))
        order = rules.finishing_order(scores)
        self.assertEqual([times[runner] for runner in order], sorted(times))
        self.assertEqual(rules.lengths_behind(scores)[order[0]], 0)
        self.assertGreater(rules.race_times(scores, Conditions(8, "Heavy"))[0], times[0])


class HandicapRuleTests(unittest.TestCase):
    RULES = HandicapRules()

    def test_a_first_win_is_free(self):
        self.assertEqual(rules.review_weight(0, [1], self.RULES), 0)
        self.assertEqual(rules.review_weight(0, [4, 2, 5, 3, 6, 7, 2, 1], self.RULES), 0)

    def test_winning_again_inside_the_window_is_too_much(self):
        self.assertEqual(rules.review_weight(0, [1, 1], self.RULES), 6)
        self.assertEqual(rules.review_weight(6, [1, 4, 5, 2, 3, 6, 7, 1], self.RULES), 12)

    def test_only_the_review_window_counts(self):
        self.assertEqual(rules.review_weight(6, [1, 4, 5, 2, 3, 6, 7, 8, 1], self.RULES), 6)

    def test_weight_goes_on_for_winning_not_for_having_won(self):
        # Two recent wins, but today's second place is not a reason to add more.
        self.assertEqual(rules.review_weight(6, [1, 1, 2], self.RULES), 6)

    def test_weight_comes_off_one_unplaced_run_at_a_time_but_never_below_zero(self):
        self.assertEqual(rules.review_weight(6, [1, 1, 4], self.RULES), 5)
        self.assertEqual(rules.review_weight(6, [1, 1, 3], self.RULES), 6)
        self.assertEqual(rules.review_weight(0, [5, 6, 7], self.RULES), 0)

    def test_weight_is_capped(self):
        self.assertEqual(rules.review_weight(28, [1, 1, 1, 1], self.RULES), 30)
        self.assertEqual(rules.review_weight(30, [1, 1, 1, 1], self.RULES), 30)

    def test_no_runs_no_change(self):
        self.assertEqual(rules.review_weight(4, [], self.RULES), 4)


class RacingGameTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.game = HorseRacingGame(table("09_horse_racing.json"))
        self.keys = [horse.key for horse in self.game.horses]

    def session(self, credits=10_000, name="Punter"):
        return self.make_session(credits=credits, rng=RiggedRandom(1), name=name)

    def bet(self, horse, kind, amount):
        return {"horse": self.keys[horse], "kind": kind, "amount": amount}

    def price(self, session, horse, kind):
        return self.game.odds(self.game.season(session))[horse][kind]

    def test_race_card_lists_every_horse_with_prices(self):
        card = self.game.betting_view(self.session())
        self.assertEqual((card["season"], card["race"]), (1, 1))
        self.assertEqual(len(card["runners"]), 8)
        self.assertIn(card["conditions"]["distance"], rules.DISTANCES)
        self.assertIn(card["conditions"]["going"], rules.GOING)
        for runner in card["runners"]:
            self.assertRegex(runner["odds"]["win"], r"^\d+:\d+$")
            self.assertEqual(runner["weight"], 0)

    def test_many_bets_on_many_horses_settle_independently(self):
        session = self.session()
        prices = {(horse, kind): self.price(session, horse, kind) for horse in range(8) for kind in rules.BET_PLACES}
        bets = [self.bet(horse, kind, 10) for (horse, kind), price in prices.items() if price is not None]
        self.assertGreaterEqual(len(bets), 20)
        session.rng.favor(8, winner=5, second=2, third=7)
        current = play(self.game, session, {"bets": bets})

        self.assertEqual([r["position"] for r in current.runners if r["key"] in
                          (self.keys[5], self.keys[2], self.keys[7])], [2, 1, 3])
        expected = 10_000
        for (horse, kind), price in prices.items():
            if price is None:
                continue
            expected -= 10
            finished = {5: 1, 2: 2, 7: 3}.get(horse, 9)
            if finished <= rules.BET_PLACES[kind]:
                expected += 10 + int(10 * price)
        self.assertEqual(session.wallet.total, expected)
        self.assertEqual(len(current.settlements), len(bets))
        self.assertTrue({"Racing_Win", "Racing_Across"} <= self.unlocked(session))

    def test_place_and_show_pay_for_second_and_third(self):
        session = self.session()
        place, show = self.price(session, 3, "place"), self.price(session, 6, "show")
        session.rng.favor(8, winner=0, second=3, third=6)
        play(self.game, session, {"bets": [self.bet(3, "win", 20), self.bet(3, "place", 20), self.bet(6, "show", 20),
                                           self.bet(6, "place", 20)]})
        self.assertEqual(session.wallet.total, 10_000 - 80 + (20 + int(20 * place)) + (20 + int(20 * show)))

    def test_longshot_win_pays_the_price_on_the_board(self):
        session = self.session()
        price = self.price(session, 7, "win")
        self.assertGreaterEqual(price, 15)
        session.rng.favor(8, winner=7)
        play(self.game, session, {"bets": [self.bet(7, "win", 100)]})
        self.assertEqual(session.wallet.total, 10_000 + 100 * price)
        self.assertIn("Racing_Longshot", self.unlocked(session))

    def test_repeat_bets_merge_and_respect_the_table_maximum(self):
        session = self.session(credits=100_000)
        session.rng.favor(8, winner=1)
        current = play(self.game, session, {"bets": [self.bet(0, "win", 30), self.bet(0, "win", 20)]})
        self.assertEqual([(s.bet.amount, s.bet.label) for s in current.settlements],
                         [(50, f"Win ({self.game.horses[0].name})")])
        with self.assertRaisesRegex(BetError, "maximum"):
            self.game.start(session, {"bets": [self.bet(0, "win", 5000), self.bet(0, "win", 1)]})

    def test_bad_bets_are_refused_and_cost_nothing(self):
        session = self.session(credits=100)
        unpriced = next(((horse, kind) for horse in range(8) for kind in rules.BET_PLACES
                         if self.price(session, horse, kind) is None), None)
        bad = [{}, {"bets": []}, {"bets": "all of them"}, {"bets": [5]},
               {"bets": [{"horse": "pegasus", "kind": "win", "amount": 5}]},
               {"bets": [{"horse": self.keys[0], "kind": "exacta", "amount": 5}]},
               {"bets": [{"horse": ["x"], "kind": {}, "amount": 5}]},
               {"bets": [self.bet(0, "win", 0)]}, {"bets": [self.bet(0, "win", -5)]},
               {"bets": [self.bet(0, "win", 2.5)]}, {"bets": [self.bet(0, "win", 5001)]},
               {"bets": [self.bet(0, "win", 60), self.bet(1, "win", 60)]}]
        if unpriced:
            bad.append({"bets": [self.bet(*unpriced, 5)]})
        for bets in bad:
            with self.subTest(bets=bets), self.assertRaises(BetError):
                self.game.start(session, bets)
        self.assertEqual(session.wallet.total, 100)
        self.assertEqual(self.game.season(session)["race"], 0)

    def test_a_bet_the_board_does_not_price_is_refused(self):
        lopsided = replace(self.game.table, settings={**self.game.table.settings,
                                                      "model": {"spread": 1.0, "aptitude": 0.0, "weight_cost": 0.5}})
        game = HorseRacingGame(lopsided)
        session = self.session()
        self.assertIsNone(game.odds(game.season(session))[0]["show"])
        self.assertIsNone(game.betting_view(session)["runners"][0]["odds"]["show"])
        with self.assertRaisesRegex(BetError, "no Show price"):
            game.start(session, {"bets": [{"horse": self.keys[0], "kind": "show", "amount": 5}]})

    def test_results_update_the_standings(self):
        session = self.session()
        session.rng.favor(8, winner=4, second=1, third=0)
        current = play(self.game, session, {"bets": [self.bet(4, "win", 5)]})
        standings = current.view()["standings"]
        self.assertEqual([row["key"] for row in standings[:3]], [self.keys[4], self.keys[1], self.keys[0]])
        self.assertEqual([row["points"] for row in standings[:4]], [10, 5, 3, 1])
        self.assertEqual(sum(row["starts"] for row in standings), 8)
        self.assertEqual(standings[0]["recent"], [1])
        self.assertEqual(self.game.betting_view(session)["race"], 2)

    def test_season_survives_a_new_session(self):
        session = self.session()
        session.rng.favor(8, winner=4)
        play(self.game, session, {"bets": [self.bet(4, "win", 5)]})
        again = type(session)(self.db, session.character, session.wallet, rng=RiggedRandom(9))
        card = HorseRacingGame(table("09_horse_racing.json")).betting_view(again)
        self.assertEqual(card["race"], 2)
        self.assertEqual(card["standings"][0]["key"], self.keys[4])

    def test_a_changed_stable_starts_a_fresh_season(self):
        session = self.session()
        session.rng.favor(8, winner=4)
        play(self.game, session, {"bets": [self.bet(4, "win", 5)]})
        season = self.game.season(session)
        season["horses"]["retired"] = season["horses"].pop(self.keys[0])
        self.db.save_table_state(session.character.id, self.game.table.key, season)
        fresh = self.game.season(session)
        self.assertEqual((fresh["season"], fresh["race"]), (1, 0))
        self.assertEqual(set(fresh["horses"]), set(self.keys))

    def test_the_stable_needs_four_horses_with_unique_keys(self):
        horse = {"key": "a", "name": "A", "rating": 80, "stamina": 0, "mud": 0, "style": "front", "silks": "#000"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "horses.json"
            for stable in ([horse] * 3, [horse] * 4):
                path.write_text(json.dumps(stable), encoding="utf-8")
                with self.subTest(horses=len(stable)), self.assertRaises(ValueError):
                    HorseRacingGame(table("09_horse_racing.json"), path)

    def test_a_horse_that_keeps_winning_is_weighted_down_and_its_odds_lengthen(self):
        session = self.session()
        favorite = 0
        for race in range(1, 7):
            session.rng.favor(8, winner=favorite)
            current = play(self.game, session, {"bets": [self.bet(favorite, "win", 1)]})
            weight = self.game.season(session)["horses"][self.keys[favorite]]["weight"]
            # The first win is free; every win after it adds weight.
            self.assertEqual(weight, (race - 1) * 6)
        self.assertIn("Stewards: Midnight Ledger goes from +24 lb to +30 lb.", current.notes)

        season = self.game.season(session)
        weighted = self.game.odds(season)[favorite]["win"]
        season["horses"][self.keys[favorite]]["weight"] = 0
        unweighted = self.game.odds(season)[favorite]["win"]
        self.assertGreater(weighted, unweighted)

    def test_forty_races_crown_a_champion_and_start_a_new_season(self):
        session = self.session()
        results = []
        for race in range(1, 41):
            card = self.game.betting_view(session)
            self.assertEqual((card["season"], card["race"]), (1, race))
            current = play(self.game, session, {"bets": [self.bet(race % 8, "win", 1)]})
            results.append(current)
            self.assertEqual(current.season_over is not None, race == 40)

        final = results[-1].view()
        champion = final["standings"][0]
        self.assertEqual(final["season_over"], {"season": 1, "champion": champion["name"]})
        self.assertTrue(all(row["starts"] == 40 for row in final["standings"]))
        self.assertEqual(sum(row["points"] for row in final["standings"]), 40 * (10 + 5 + 3 + 1))
        self.assertEqual(sum(row["firsts"] for row in final["standings"]), 40)
        self.assertEqual(max(row["points"] for row in final["standings"]), champion["points"])
        self.assertIn("Racing_Season", self.unlocked(session))

        card = self.game.betting_view(session)
        self.assertEqual((card["season"], card["race"], card["champion"]), (2, 1, champion["name"]))
        self.assertTrue(all(row["starts"] == 0 and row["weight"] == 0 and row["points"] == 0
                            for row in card["standings"]))
        self.assertEqual(self.db.get_stats(session.character.id)["racing"]["wins"]
                         + self.db.get_stats(session.character.id)["racing"]["losses"], 40)


class SeasonBalanceTests(unittest.TestCase):
    """Seasons simulated straight from the rules, with no database, to judge the handicapping as a whole."""

    def seasons(self, handicap, count=200):
        game = HorseRacingGame(table("09_horse_racing.json"))
        game.handicap = handicap
        rng = random.Random(11)
        wins = {horse.key: 0 for horse in game.horses}
        titles = dict(wins)
        most_in_a_season = []
        for _ in range(count):
            season = new_season(1, game.horses, Conditions(8, "Good"), None)
            for _ in range(game.season_length):
                conditions = Conditions(rng.choice(list(rules.DISTANCES)), rng.choice(list(rules.GOING)))
                strengths = [rules.strength(horse, conditions, season["horses"][horse.key]["weight"], game.model)
                             for horse in game.horses]
                order = rules.finishing_order(rules.run_race(strengths, game.model.spread, rng))
                game.record_result(season, {game.horses[runner].key: place for place, runner in enumerate(order, 1)})
            for key, record in season["horses"].items():
                wins[key] += record["firsts"]
            titles[game.standings(season)[0]["key"]] += 1
            most_in_a_season.append(max(record["firsts"] for record in season["horses"].values()))
        return wins, titles, most_in_a_season, count

    def test_handicapping_reins_in_the_best_horse_without_making_ability_irrelevant(self):
        free_wins, free_titles, free_most, count = self.seasons(HandicapRules(penalty_lb=0, relief_lb=0))
        wins, titles, most, _ = self.seasons(HandicapRules())
        best, worst = "midnight_ledger", "slow_clap"
        races = count * 40

        self.assertGreater(free_wins[best] / races, 0.30)
        self.assertLess(wins[best] / races, 0.23)
        self.assertGreater(free_titles[best] / count, 0.90)
        self.assertLess(titles[best] / count, 0.80)
        self.assertLess(sum(most) / count, sum(free_most) / count - 3)
        self.assertGreater(wins[best], wins[worst] * 2)
        self.assertGreater(wins[worst], free_wins[worst])
        self.assertGreater(sum(1 for key in titles if titles[key]), sum(1 for key in free_titles if free_titles[key]))

    def test_the_house_keeps_an_edge_on_every_kind_of_bet(self):
        game = HorseRacingGame(table("09_horse_racing.json"))
        rng = random.Random(5)
        staked = {kind: 0 for kind in rules.BET_PLACES}
        returned = dict(staked)
        for _ in range(4000):
            conditions = Conditions(rng.choice(list(rules.DISTANCES)), rng.choice(list(rules.GOING)))
            weights = [rng.choice([0, 0, 4, 8, 12]) for _ in game.horses]
            strengths = [rules.strength(horse, conditions, weight, game.model)
                         for horse, weight in zip(game.horses, weights)]
            chances = rules.finish_probabilities(strengths, game.model.spread)
            order = rules.finishing_order(rules.run_race(strengths, game.model.spread, rng))
            for place, runner in enumerate(order, 1):
                for kind, places in rules.BET_PLACES.items():
                    price = rules.offered_odds(chances[runner][kind], game.margin)
                    if price is None:
                        continue
                    staked[kind] += 100
                    if place <= places:
                        returned[kind] += 100 + int(100 * price)
        for kind in rules.BET_PLACES:
            with self.subTest(kind=kind):
                edge = 1 - returned[kind] / staked[kind]
                self.assertGreater(edge, 0.10)
                self.assertLess(edge, 0.35)


if __name__ == "__main__":
    unittest.main()
