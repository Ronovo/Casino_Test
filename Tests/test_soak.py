"""Thousands of random rounds per game, checking after every move that no credit appears or vanishes."""
import os
import random
import unittest

from casino.config import TABLES_DIR
from casino.engine.bets import BetError
from casino.engine.chips import Chips
from casino.games import load_games
from casino.rules import roulette
from Tests.helpers import DatabaseTestCase


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
    choices = [("straight", rng.choice(roulette.WHEEL)), ("red_black", rng.choice(["Red", "Black"])),
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
        """Play random rounds with random legal moves. Returns (rounds played, bets refused)."""
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
                settled = sum(s.returned for s in current.settlements)
                self.assertEqual(session.wallet.total, before - current.staked + settled,
                                 "wallet and stake out of step")
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
        for key in ("blackjack", "ultimate_holdem"):
            game = GAMES[key]
            session = self.make_session(credits=1_000_000, rng=random.Random(5), name=key)
            rng = random.Random(6)
            for _ in range(200):
                current = game.start(session, BET_MAKERS[game.game_key](rng, game, 1_000_000))
                while not current.finished:
                    view = current.view()
                    if key == "blackjack":
                        hidden = [current.dealer[1]]
                        shown = view["dealer"]["cards"]
                        face_up = current.dealer[:1] + [card for hand in current.hands for card in hand.cards]
                    else:
                        hidden = current.dealer + current.board[current.shown:]
                        shown = view["dealer"] + view["board"]
                        face_up = current.player + current.board[:current.shown]
                    self.assertEqual(sum(card is None for card in shown), len(hidden))
                    text = repr(view)
                    # A six-deck shoe can deal a hidden card's twin face up, so count rather than forbid.
                    for card in hidden:
                        sent = repr({"rank": card.rank, "suit": card.suit})
                        self.assertEqual(text.count(sent), face_up.count(card))
                    current.act(rng.choice(view["actions"])["id"])
