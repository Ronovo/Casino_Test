"""Thousands of random rounds per game, checking after every move that no credit appears or vanishes."""
import os
import random
import threading
import unittest

from casino.config import TABLES_DIR
from casino.engine.bets import BetError
from casino.engine.chips import Chips
from casino.games import load_games
from casino.rules import baccarat, roulette
from casino.engine.cards import Shoe
from casino.web.floor import Floor
from casino.web.server import CasinoApp
from Tests.helpers import DatabaseTestCase
from ronovo_portfolio_auth.security_questions import QUESTIONS

SECURITY = (QUESTIONS[0], "rex")
SECURITY_BODY = {"question": QUESTIONS[0], "answer": "rex"}

GAMES = {game.table.key: game for game in load_games(TABLES_DIR)}


def blackjack_bets(rng, game, credits):
    return {"bet": rng.randint(game.table.min_bet, max(game.table.min_bet, min(credits, 60)))}


def poker_bets(rng, game, credits):
    low = game.table.min_bet
    return {"ante": rng.randint(low, low + 20), "trips": rng.choice([0, 0, low, 7]), "pairs": rng.choice([0, 0, 3])}


def baccarat_bets(rng, game, credits):
    bets = {key: rng.choice([0, 0, 5, 25]) for key in ("player", "banker", "tie", "dragon7", "panda8")}
    bets[rng.choice(["player", "banker"])] = rng.randint(1, 50)
    return bets


def roulette_bets(rng, game, credits):
    low = game.table.min_bet
    choices = [("straight", rng.choice(game.wheel)), ("red_black", rng.choice(["Red", "Black"])),
               ("odd_even", rng.choice(["Odd", "Even"])), ("low_high", rng.choice(["Low", "High"])),
               ("dozen", rng.randint(1, 3)), ("column", rng.randint(1, 3))]
    picked = rng.sample(choices, rng.randint(1, len(choices)))
    return {"bets": [{"kind": kind, "selection": selection, "amount": rng.randint(low, low + 20)}
                     for kind, selection in picked]}


def gtn_bets(rng, game, credits):
    difficulty = rng.choice(game.difficulties)
    top = difficulty.max_number
    options = {"pick": rng.randint(1, top), "high_low": rng.choice(["High", "Low"]),
               "even_odd": rng.choice(["Even", "Odd"]), "range": rng.randint(1, top - difficulty.range_size + 1),
               "lucky": rng.sample(range(1, min(top, 1000) + 1), 2)}
    kinds = rng.sample(list(options), rng.randint(1, len(options)))
    return {"difficulty": difficulty.name,
            "bets": {kind: {"selection": options[kind], "amount": rng.randint(1, 20)} for kind in kinds}}


def racing_bets(rng, game, credits):
    picks = rng.sample([(horse.key, kind) for horse in game.horses for kind in ("win", "place", "show")],
                       rng.randint(1, 10))
    return {"bets": [{"horse": horse, "kind": kind, "amount": rng.randint(1, 25)} for horse, kind in picks]}


BET_MAKERS = {"racing": racing_bets, "blackjack": blackjack_bets, "poker": poker_bets, "baccarat": baccarat_bets,
              "roulette": roulette_bets, "gtn": gtn_bets}


@unittest.skipUnless(os.environ.get("CASINO_SOAK"), "set CASINO_SOAK=1 to run the soak tests")
class SoakTests(DatabaseTestCase):
    def soak(self, table_key, rounds, credits, seed=1, top_up=True):
        """Play random rounds with random legal moves. Returns (rounds played, total net)."""
        game = GAMES[table_key]
        session = self.make_session(credits=credits, rng=random.Random(seed), name=f"{table_key}-{seed}-{credits}")
        rng = random.Random(seed + 1000)
        make_bets = BET_MAKERS[game.game_key]
        played = total_net = refused = 0
        for _ in range(rounds):
            if top_up and session.wallet.total < game.min_buy_in:
                session.wallet.reset(Chips.make_change(credits))
            before = session.wallet.total
            try:
                current = game.start(session, make_bets(rng, game, before))
            except BetError:
                self.assertEqual(session.wallet.total, before, "a refused bet moved credits")
                refused += 1
                continue
            for _ in range(60):
                if current.finished:
                    break
                view = current.view()
                self.assertEqual(session.wallet.total, before - current.staked, "wallet and stake out of step")
                self.assertTrue(view["actions"], "an unfinished round offered no moves")
                self.assertNotIn("result", view)
                current.act(rng.choice(view["actions"])["id"])
            self.assertTrue(current.finished, "round never finished")

            result = current.view()["result"]
            self.assertEqual(session.wallet.total - before, result["net"], "payout does not match the result shown")
            self.assertEqual(sum(s["amount"] for s in result["settlements"]), current.staked)
            for settlement in result["settlements"]:
                self.assertGreaterEqual(settlement["returned"], 0)
                self.assertGreater(settlement["amount"], 0)
                self.assertEqual(settlement["net"], settlement["returned"] - settlement["amount"])
            self.assertEqual(session.wallet.total, self.db.load_chips(session.character.id).total)
            with self.assertRaises(BetError):
                current.act("hit")
            played += 1
            total_net += result["net"]

        stats = self.db.get_stats(session.character.id).get(game.game_key)
        if played:
            self.assertEqual(stats["wins"] + stats["losses"] + stats["pushes"], played)
            self.assertEqual(stats["net_credits"], total_net)
        return played, refused

    def test_every_table_with_a_deep_bankroll(self):
        for key in GAMES:
            with self.subTest(table=key):
                played, _ = self.soak(key, rounds=400, credits=5_000_000)
                self.assertGreater(played, 350)

    def test_every_table_on_a_shoestring(self):
        # Bankrolls close to the table minimum exercise unaffordable doubles, splits, raises and refused bets.
        for key, game in GAMES.items():
            for credits in (game.min_buy_in, game.min_buy_in * 2 + 1, game.min_buy_in * 5 + 3):
                with self.subTest(table=key, credits=credits):
                    self.soak(key, rounds=150, credits=credits, seed=credits)

    def test_views_never_leak_face_down_cards(self):
        for key in ("blackjack_classic", "ultimate_holdem"):
            game = GAMES[key]
            session = self.make_session(credits=1_000_000, rng=random.Random(5), name=key)
            rng = random.Random(6)
            for _ in range(200):
                current = game.start(session, BET_MAKERS[game.game_key](rng, game, 1_000_000))
                while not current.finished:
                    view = current.view()
                    if key == "blackjack_classic":
                        hidden = [current.dealer[1]]
                        shown = view["dealer"]["cards"]
                    else:
                        hidden = current.dealer + current.board[current.shown:]
                        shown = view["dealer"] + view["board"]
                    self.assertEqual(sum(card is None for card in shown), len(hidden))
                    text = repr(view)
                    for card in hidden:
                        self.assertNotIn(repr({"rank": card.rank, "suit": card.suit}), text)
                    current.act(rng.choice(view["actions"])["id"])


class OddsTests(DatabaseTestCase):
    """Long-run frequencies against published figures, as a check on the drawing rules."""

    def test_baccarat_outcome_frequencies(self):
        rng = random.Random(2024)
        counts = {"player": 0, "banker": 0, "tie": 0, "dragon7": 0, "panda8": 0}
        coups = 60_000
        for _ in range(coups):
            coup = baccarat.play_coup(Shoe.shuffled(8, rng).draw)
            counts[coup.winner] += 1
            counts["dragon7"] += coup.dragon7
            counts["panda8"] += coup.panda8
        expected = {"banker": 0.4586, "player": 0.4462, "tie": 0.0952, "dragon7": 0.0225, "panda8": 0.0345}
        for key, share in expected.items():
            with self.subTest(outcome=key):
                self.assertAlmostEqual(counts[key] / coups, share, delta=0.006)

    def test_roulette_bets_cover_the_right_number_of_pockets(self):
        for name, wheel in roulette.WHEELS.items():
            with self.subTest(wheel=name):
                self.assertEqual(len(set(wheel)), len(wheel))
                cover = lambda kind, selection: sum(roulette.wins(kind, selection, pocket) for pocket in wheel)
                for kind, selections, pockets in (("red_black", ("Red", "Black"), 18), ("odd_even", ("Odd", "Even"), 18),
                                                  ("low_high", ("Low", "High"), 18), ("dozen", (1, 2, 3), 12),
                                                  ("column", (1, 2, 3), 12), ("straight", wheel, 1)):
                    for selection in selections:
                        self.assertEqual(cover(kind, selection), pockets, (kind, selection))


class HostileInputTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.games = load_games(TABLES_DIR)
        self.app = CasinoApp(self.db, self.games, Floor(self.db, self.games, rng_factory=lambda: random.Random(3)))
        self.token = self.app.dispatch("POST", "register", {"username": "Fuzzer", "password": "hunter22", **SECURITY_BODY}, None).token
        self.app.dispatch("POST", "characters", {"name": "Fuzzer", "difficulty": "Medium"}, self.token)
        self.wallet = self.app.floor.seat(self.db.get_character("Fuzzer")).session.wallet

    def test_garbage_never_crashes_the_server_or_moves_credits(self):
        rng = random.Random(99)
        atoms = [None, True, False, 0, 1, -1, 5, 10**30, 2.5, float("nan"), float("inf"), "", "Red", "17", "00",
                 "player", "bet", "Easy", "Impossible", "hit", "<script>", "x" * 500, [], {}, [1, 2], ["a"],
                 {"amount": 5}, {"selection": 3, "amount": 5}, {"kind": "straight", "selection": "17", "amount": 5}]
        keys = ["bet", "bets", "ante", "trips", "pairs", "player", "banker", "tie", "dragon7", "panda8", "kind",
                "selection", "amount", "difficulty", "pick", "lucky", "range", "high_low", "even_odd", "action",
                "color", "into", "count", "id", "name", "horse"]

        def junk(depth=0):
            roll = rng.random()
            if depth < 3 and roll < 0.3:
                return {rng.choice(keys): junk(depth + 1) for _ in range(rng.randint(0, 4))}
            if depth < 3 and roll < 0.45:
                return [junk(depth + 1) for _ in range(rng.randint(0, 3))]
            return rng.choice(atoms)

        paths = [f"tables/{key}/{verb}" for key in [*(g.table.key for g in self.games), "nowhere"]
                 for verb in ("start", "act", "leave")] + ["cashier", "start-over", "characters/select", "nowhere"]
        statuses = set()
        for _ in range(4000):
            path = rng.choice(paths)
            body = {rng.choice(keys): junk() for _ in range(rng.randint(0, 4))}
            reply = self.app.dispatch("POST", path, body, self.token)
            statuses.add(reply.status)
            if reply.status == 200 and path == "characters/select":
                self.app.dispatch("POST", "characters/select",
                                  {"id": self.db.get_character("Fuzzer").id}, self.token)
        self.assertLessEqual(statuses, {200, 400, 404, 409})
        in_play = sum(current.staked for current in
                      self.app.floor.seat(self.db.get_character("Fuzzer")).rounds.values())
        stats = self.db.get_stats(self.db.get_character("Fuzzer").id)
        self.assertEqual(self.wallet.total + in_play, 1000 + sum(row["net_credits"] for row in stats.values()))

    def test_simultaneous_all_in_bets_cannot_overdraw(self):
        bets = {"bets": {"bets": [{"kind": "red_black", "selection": "Red", "amount": 1000}]}}
        replies = []
        barrier = threading.Barrier(12)

        def punt():
            barrier.wait()
            replies.append(self.app.dispatch("POST", "tables/roulette_european/start", bets, self.token))

        threads = [threading.Thread(target=punt) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        accepted = [reply for reply in replies if reply.status == 200]
        net = sum(reply.body["round"]["result"]["net"] for reply in accepted)
        self.assertEqual(self.wallet.total, 1000 + net)
        self.assertGreaterEqual(self.wallet.total, 0)
        self.assertTrue(all(reply.status in (200, 400) for reply in replies))
