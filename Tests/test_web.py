"""Accounts, the floor service and the HTTP server, including a real socket round trip."""
import http.client
import io
import logging
import random
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

from flask import Response

import main
from casino.accounts import (MAX_CHARACTERS, REGISTRATION_WINDOW_SECONDS, AccountError, Accounts, hash_password,
                             verify_password)
from casino.cashier import break_chips, color_up
from casino.config import TABLES_DIR
from casino.engine.chips import Chips
from casino.engine.wallet import Wallet
from casino.games import load_games
from casino.web.floor import ApiError
from casino.web.server import (MAX_BODY_BYTES, CasinoApp, create_app, lan_address, make_server, open_casino,
                               parse_json_body, serve, set_cookie, static_file)
from Tests.helpers import (SECURITY, SECURITY_BODY, AppTestCase, Browser, DatabaseTestCase, login,
                           serve_in_background)


class CashierTests(unittest.TestCase):
    def test_break_chips_keeps_total(self):
        self.assertEqual(break_chips(Chips(Black=2), "Black", 1, "Green"), Chips(Black=1, Green=4))

    def test_break_with_remainder(self):
        self.assertEqual(break_chips(Chips(Green=1), "Green", 1, "Red"), Chips(Red=5))
        self.assertEqual(break_chips(Chips(Purple=1), "Purple", 1, "Black").total, 500)

    def test_color_up_keeps_total_and_larger_chips(self):
        rack = Chips(White=30, Red=10, Orange=1)
        result = color_up(rack, "Green", 3)
        self.assertEqual(result.total, rack.total)
        self.assertEqual(result["Green"], 3)
        self.assertEqual(result["Orange"], 1)


class AccountTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.accounts = Accounts(self.db)

    def test_password_hashes_are_salted_and_verifiable(self):
        first, second = hash_password("hunter22"), hash_password("hunter22")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("hunter22", first))
        self.assertFalse(verify_password("hunter23", first))
        self.assertFalse(verify_password("hunter22", "not a hash"))

    def test_register_login_and_logout(self):
        self.accounts.register("Ronovo", "hunter22", *SECURITY)
        token = login(self.accounts, "ronovo", "hunter22")
        user, character = self.accounts.resolve(token)
        self.assertEqual(user.username, "Ronovo")
        self.assertIsNone(character)
        self.accounts.logout(token)
        self.assertIsNone(self.accounts.resolve(token))
        self.assertIsNone(self.accounts.resolve("made-up-token"))
        self.assertIsNone(self.accounts.resolve(None))

    def test_registration_rules(self):
        self.accounts.register("Ronovo", "hunter22", *SECURITY)
        for username, password in (("RONOVO", "hunter22"), ("ab", "hunter22"), ("bad name", "hunter22"),
                                   ("<script>", "hunter22"), ("Fine_Name", "short"), ("Fine_Name", "x" * 129),
                                   (None, "hunter22"), ("Fine_Name", None), (["a"], {"b": 1})):
            with self.subTest(username=username), self.assertRaises(AccountError):
                self.accounts.register(username, password, *SECURITY)

    def test_wrong_passwords_lock_the_account_for_a_while(self):
        self.accounts.register("Ronovo", "hunter22", *SECURITY)
        for _ in range(5):
            with self.assertRaisesRegex(AccountError, "Wrong username or password"):
                login(self.accounts, "Ronovo", "nope")
        with self.assertRaisesRegex(AccountError, "Too many wrong passwords"):
            login(self.accounts, "Ronovo", "hunter22")

    def test_unknown_user_gets_the_same_error_as_a_wrong_password(self):
        with self.assertRaisesRegex(AccountError, "Wrong username or password"):
            login(self.accounts, "Nobody", "")
        with self.assertRaisesRegex(AccountError, "Wrong username or password"):
            self.accounts.authenticate(["Nobody"], "")

    def test_characters_belong_to_their_account(self):
        owner = self.accounts.register("Ronovo", "hunter22", *SECURITY)
        other = self.accounts.register("Rival", "hunter22", *SECURITY)
        token, other_token = login(self.accounts, "Ronovo", "hunter22"), login(self.accounts, "Rival", "hunter22")
        character = self.accounts.create_character(owner, "  High   Roller ", "Hard")
        self.assertEqual(character.name, "High Roller")
        self.assertEqual(self.db.load_chips(character.id).total, 100)
        with self.assertRaisesRegex(AccountError, "already taken"):
            self.accounts.create_character(other, "High Roller", "Easy")
        with self.assertRaisesRegex(AccountError, "isn't on your account"):
            self.accounts.select_character(other_token, other, character.id)
        self.accounts.select_character(token, owner, character.id)
        self.assertEqual(self.accounts.resolve(token)[1].id, character.id)
        self.assertEqual(self.db.list_characters(other.id), [])

    def test_character_creation_rules(self):
        user = self.accounts.register("Ronovo", "hunter22", *SECURITY)
        for name, difficulty in (("", "Easy"), ("   ", "Easy"), ("x" * 31, "Easy"), ("Fine", "Impossible"),
                                 (None, "Easy"), ("Fine", None), (5, ["Easy"])):
            with self.subTest(name=name, difficulty=difficulty), self.assertRaises(AccountError):
                self.accounts.create_character(user, name, difficulty)

    def test_registrations_are_limited(self):
        self.accounts.max_registrations = 1
        self.accounts.register("Ronovo", "hunter22", *SECURITY)
        with self.assertRaisesRegex(AccountError, "Too many new accounts"):
            self.accounts.register("Rival", "hunter22", *SECURITY)

    def test_the_registration_limit_is_a_rolling_window(self):
        self.accounts.max_registrations = 1
        with mock.patch("casino.accounts.time.monotonic", return_value=1000.0):
            self.accounts.register("Ronovo", "hunter22", *SECURITY)
        with mock.patch("casino.accounts.time.monotonic", return_value=1000.0 + REGISTRATION_WINDOW_SECONDS):
            self.accounts.register("Rival", "hunter22", *SECURITY)

    def test_a_taken_username_does_not_use_up_the_registration_limit(self):
        self.accounts.max_registrations = 2
        self.accounts.register("Ronovo", "hunter22", *SECURITY)
        with self.assertRaisesRegex(AccountError, "already taken"):
            self.accounts.register("ronovo", "hunter22", *SECURITY)
        self.accounts.register("Rival", "hunter22", *SECURITY)

    def test_an_account_holds_a_limited_number_of_characters(self):
        user = self.accounts.register("Ronovo", "hunter22", *SECURITY)
        for n in range(MAX_CHARACTERS):
            self.accounts.create_character(user, f"Character {n}", "Easy")
        with self.assertRaisesRegex(AccountError, f"can hold {MAX_CHARACTERS}"):
            self.accounts.create_character(user, "One Too Many", "Easy")

    def test_a_portfolio_account_links_to_only_one_casino_account(self):
        self.accounts.portfolio_user("1", "player1")
        other = self.accounts.register("Ronovo", "hunter22", *SECURITY)
        with self.assertRaisesRegex(AccountError, "already linked to another casino account"):
            self.accounts.link_portfolio(other, "1")

    def test_portfolio_names_stay_twenty_characters_with_a_number_added(self):
        for n in range(1, 11):
            self.db.create_user("player" + ("" if n == 1 else str(n)), "unused")
        self.assertEqual(self.accounts.portfolio_user("7", "player").username, "player11")
        long_name = "x" * 20
        self.db.create_user(long_name, "unused")
        for n in range(2, 11):
            self.db.create_user(f"{long_name[:20 - len(str(n))]}{n}", "unused")
        self.assertEqual(self.accounts.portfolio_user("8", long_name).username, f"{long_name[:18]}11")


class FloorTests(AppTestCase):
    def test_session_lists_the_account_and_its_characters(self):
        body = self.call("GET", "session")
        self.assertEqual(body["user"], "Ronovo")
        self.assertEqual([(c["name"], c["credits"]) for c in body["characters"]], [("Ronovo Ronove", 1000)])
        self.assertEqual(body["character"], body["characters"][0]["id"])
        self.assertIsNone(self.call("GET", "session", token=None)["user"])

    def test_everything_but_login_needs_an_account_and_a_character(self):
        self.call("GET", "lobby", token=None, status=401)
        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}}, token="forged", status=401)
        self.call("POST", "characters/select", {"id": None})
        self.call("GET", "lobby", status=409)

    def test_lobby_lists_every_table(self):
        body = self.call("GET", "lobby")
        self.assertEqual(len(body["tables"]), len(self.games))
        self.assertEqual(body["player"]["credits"], 1000)
        self.assertFalse(body["player"]["broke"])

    def test_a_round_that_fails_part_way_keeps_the_chips(self):
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        failing = mock.patch.object(type(self.db), "set_open_stake", side_effect=RuntimeError("disk full"))
        with failing, self.assertRaises(RuntimeError):
            self.app.dispatch("POST", "tables/blackjack/start", {"bets": {"bet": 10}}, self.token)
        self.assertEqual(self.seat().session.wallet.total, 1000)
        self.assertEqual(self.db.load_chips(self.seat().session.character.id).total, 1000)
        self.assertFalse(self.call("GET", "lobby")["tables"][0]["in_progress"])

    def test_a_move_that_fails_hands_the_stake_back_straight_away(self):
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 100}})
        failing = mock.patch.object(type(self.db), "set_open_stake", side_effect=RuntimeError("disk full"))
        with failing, self.assertRaises(RuntimeError):
            self.app.dispatch("POST", "tables/blackjack/act", {"action": "stand"}, self.token)
        body = self.call("GET", "lobby")
        self.assertEqual(body["player"]["credits"], 1000)
        self.assertIn("100 cr", body["notices"][0])
        self.assertFalse(body["tables"][0]["in_progress"])

        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}})
        self.assertEqual(self.call("POST", "tables/blackjack/act", {"action": "stand"})["player"]["credits"],
                         1010)
        restarted = CasinoApp(self.db, self.games).dispatch("GET", "lobby", {}, self.token).body
        self.assertEqual((restarted["player"]["credits"], restarted["notices"]), (1010, []))

    def test_an_interrupted_round_does_not_refund_a_lost_insurance_bet(self):
        self.stack(["10S", "AH", "9H", "7D"])
        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 100}})
        self.assertEqual(self.call("POST", "tables/blackjack/act", {"action": "insurance"})["player"]["credits"], 850)
        failing = mock.patch.object(type(self.db), "set_open_stake", side_effect=RuntimeError("disk full"))
        with failing, self.assertRaises(RuntimeError):
            self.app.dispatch("POST", "tables/blackjack/act", {"action": "stand"}, self.token)
        body = self.call("GET", "lobby")
        self.assertEqual(body["player"]["credits"], 950)
        self.assertIn("100 cr", body["notices"][0])

    def test_a_refund_that_fails_is_tried_again_and_paid_once(self):
        self.stack(["8S", "9C", "8H", "7D", "3C", "10D"])
        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}})
        self.call("POST", "tables/blackjack/act", {"action": "split"})

        deposit = Wallet.deposit

        def deposit_then_fail(wallet, amount):
            deposit(wallet, amount)
            raise RuntimeError("disk full")

        restarted = CasinoApp(self.db, self.games)
        with mock.patch.object(Wallet, "deposit", deposit_then_fail), self.assertRaises(RuntimeError):
            restarted.dispatch("GET", "lobby", {}, self.token)
        body = restarted.dispatch("GET", "lobby", {}, self.token).body
        self.assertEqual(body["player"]["credits"], 1000)
        self.assertIn("20 cr", body["notices"][0])
        again = CasinoApp(self.db, self.games).dispatch("GET", "lobby", {}, self.token).body
        self.assertEqual((again["player"]["credits"], again["notices"]), (1000, []))

    def test_blackjack_round_over_the_api(self):
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        body = self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}})
        self.assertFalse(body["round"]["finished"])
        self.assertEqual(body["player"]["credits"], 990)
        self.assertTrue(self.call("GET", "lobby")["tables"][0]["in_progress"])
        self.assertIsNotNone(self.call("GET", "tables/blackjack")["round"])

        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}}, status=409)
        self.call("POST", "tables/blackjack/act", {"action": "fly"}, status=400)
        body = self.call("POST", "tables/blackjack/act", {"action": "stand"})
        self.assertTrue(body["round"]["finished"])
        self.assertEqual(body["round"]["result"]["net"], 10)
        self.assertEqual(body["player"]["credits"], 1010)
        self.assertIn("Baby's First Win", [a["display_name"] for a in body["achievements"]])
        self.assertIsNone(self.call("GET", "tables/blackjack")["round"])
        self.call("POST", "tables/blackjack/act", {"action": "stand"}, status=409)

    def test_bad_requests_are_refused_without_touching_the_wallet(self):
        for path, data in (("tables/nowhere/start", {"bets": {"bet": 10}}),
                           ("tables/blackjack/start", {"bets": {"bet": 5000}}),
                           ("tables/blackjack/start", {"bets": {"bet": -10}}),
                           ("tables/blackjack/start", {"bets": {"bet": "10"}}),
                           ("tables/blackjack/start", {"bets": [10]}),
                           ("tables/blackjack/start", {}),
                           ("tables/roulette/start", {"bets": {"bets": [{"kind": ["x"], "selection": 1,
                                                                                    "amount": 5}]}}),
                           ("tables/roulette/start", {"bets": {"bets": [{"kind": "dozen", "selection": 4,
                                                                                    "amount": 5}]}}),
                           ("tables/guess_the_number/start", {"bets": {"difficulty": "Easy", "bets": {
                               "pick": {"selection": 11, "amount": 5}}}}),
                           ("tables/guess_the_number/start", {"bets": {"difficulty": "Easy", "bets": {
                               "lucky": {"selection": [3, 3], "amount": 5}}}}),
                           ("cashier", {"action": "break", "color": ["Black"], "into": "Red", "count": 1}),
                           ("cashier", {"action": "break", "color": "Black", "into": "Red", "count": 99}),
                           ("cashier", {"action": "color_up", "into": "Orange", "count": 5})):
            with self.subTest(path=path, data=data):
                reply = self.app.dispatch("POST", path, data, self.token)
                self.assertIn(reply.status, (400, 404), reply.body)
        self.assertEqual(self.seat().session.wallet.total, 1000)

    def test_cashier_exchanges_keep_the_total(self):
        body = self.call("POST", "cashier", {"action": "break", "color": "Purple", "count": 1, "into": "Black"})
        self.assertEqual((body["player"]["chips"]["Purple"], body["player"]["chips"]["Black"]), (0, 8))
        body = self.call("POST", "cashier", {"action": "color_up", "into": "Orange", "count": 1})
        self.assertEqual(body["player"]["chips"]["Orange"], 1)
        self.assertEqual(body["player"]["credits"], 1000)

    def test_profile_hides_locked_achievements(self):
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}})
        self.call("POST", "tables/blackjack/act", {"action": "stand"})
        body = self.call("GET", "profile")
        self.assertEqual(body["stats"][0]["game"], "Blackjack")
        self.assertEqual(body["stats"][0]["wins"], 1)
        blackjack = next(c for c in body["categories"] if c["category"] == "Blackjack")
        self.assertEqual(sum(item["unlocked"] for item in blackjack["items"]), 1)
        self.assertTrue(all("description" not in item for item in blackjack["items"] if not item["unlocked"]))

    def test_start_over_only_when_broke_with_nothing_in_play(self):
        self.call("POST", "start-over", status=400)
        seat = self.seat()
        seat.session.wallet.reset(Chips(White=10))
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        body = self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}})
        self.assertFalse(body["player"]["broke"])
        self.call("POST", "start-over", status=400)
        self.stack(["10S", "9C", "6H", "7D", "5C", "10H"])
        self.call("POST", "tables/blackjack/act", {"action": "hit"})
        body = self.call("POST", "start-over")
        self.assertEqual(body["player"]["credits"], 1000)

    def test_the_cashier_only_breaks_chips_into_a_smaller_color(self):
        self.call("POST", "cashier", {"action": "break", "color": "Red", "into": "Green", "count": 1}, status=400)

    def test_the_cashier_page_shows_the_rack(self):
        self.assertEqual(self.call("GET", "cashier")["player"]["chips"]["Purple"], 1)

    def test_an_exchange_must_be_an_object(self):
        with self.assertRaisesRegex(ApiError, "isn't possible"):
            self.app.floor.exchange(self.seat(), ["break"])

    def test_unknown_table_moves_are_not_found(self):
        self.call("POST", "tables/blackjack/fly", status=404)

    def test_idle_seats_are_let_go(self):
        seat = self.seat()
        with mock.patch("casino.web.floor.SEAT_IDLE_SECONDS", -1):
            self.assertIsNot(self.seat(), seat)

    def test_players_cannot_reach_each_others_seats(self):
        rival = self.signup("Rival", "Rival Player", "Easy")
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}})
        self.call("POST", "tables/blackjack/act", {"action": "stand"}, token=rival, status=409)
        mine = self.call("GET", "session")["characters"][0]["id"]
        self.call("POST", "characters/select", {"id": mine}, token=rival, status=400)
        self.assertEqual(self.call("GET", "lobby", token=rival)["player"]["credits"], 10_000)

    def test_stake_is_refunded_when_the_server_restarts_mid_round(self):
        self.stack(["8S", "9C", "8H", "7D", "3C", "10D"])
        self.call("POST", "tables/blackjack/start", {"bets": {"bet": 10}})
        self.call("POST", "tables/blackjack/act", {"action": "split"})
        self.assertEqual(self.seat().session.wallet.total, 980)

        restarted = CasinoApp(self.db, self.games)
        body = restarted.dispatch("GET", "lobby", {}, self.token).body
        self.assertEqual(body["player"]["credits"], 1000)
        self.assertIn("20 cr", body["notices"][0])
        self.assertEqual(CasinoApp(self.db, self.games).dispatch("GET", "lobby", {}, self.token).body["notices"], [])

    def test_walking_away_counts_only_before_betting(self):
        walked = "Best Bet Is To Not Play"
        self.call("GET", "tables/ultimate_holdem")
        self.call("POST", "tables/ultimate_holdem/start", {"bets": {"ante": 10}})
        for action in ("check", "check", "fold"):
            body = self.call("POST", "tables/ultimate_holdem/act", {"action": action})
        self.assertTrue(body["round"]["finished"])
        self.assertNotIn(walked, [a["display_name"] for a in self.call("POST", "tables/ultimate_holdem/leave")["achievements"]])

        self.call("GET", "tables/ultimate_holdem")
        self.assertIn(walked, [a["display_name"] for a in self.call("POST", "tables/ultimate_holdem/leave")["achievements"]])

    def test_registering_a_name_someone_failed_to_log_in_as_still_logs_in(self):
        for _ in range(6):
            self.call("POST", "login", {"username": "Newcomer", "password": "guess"}, token=None, status=400)
        reply = self.app.dispatch("POST", "register", {"username": "Newcomer", "password": "hunter22", **SECURITY_BODY}, None)
        self.assertEqual(reply.status, 200, reply.body)
        self.assertEqual(self.app.accounts.resolve(reply.token)[0].username, "Newcomer")

    def test_logging_in_again_ends_the_browsers_old_login(self):
        reply = self.app.dispatch("POST", "login", {"username": "Ronovo", "password": "hunter22"}, self.token)
        self.assertEqual(reply.status, 200, reply.body)
        self.assertIsNone(self.app.accounts.resolve(self.token))
        self.assertIsNotNone(self.app.accounts.resolve(reply.token))


class HostileInputTests(AppTestCase):
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
                self.call("POST", "characters/select", {"id": self.character().id})
        self.assertLessEqual(statuses, {200, 400, 404, 409})
        seat = self.seat()
        in_play = sum(current.staked for current in seat.rounds.values())
        stats = self.db.get_stats(self.character().id)
        self.assertEqual(seat.session.wallet.total + in_play, 1000 + sum(row["net_credits"] for row in stats.values()))

    def test_simultaneous_all_in_bets_cannot_overdraw(self):
        bets = {"bets": {"bets": [{"kind": "red_black", "selection": "Red", "amount": 1000}]}}
        wallet = self.seat().session.wallet
        replies = []
        barrier = threading.Barrier(12)

        def punt():
            barrier.wait()
            replies.append(self.app.dispatch("POST", "tables/roulette/start", bets, self.token))

        threads = [threading.Thread(target=punt) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        accepted = [reply for reply in replies if reply.status == 200]
        net = sum(reply.body["round"]["result"]["net"] for reply in accepted)
        self.assertEqual(wallet.total, 1000 + net)
        self.assertGreaterEqual(wallet.total, 0)
        self.assertTrue(all(reply.status in (200, 400) for reply in replies))


class StaticFileTests(unittest.TestCase):
    def test_files_outside_the_static_folder_are_never_served(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "static" / "js").mkdir(parents=True)
            (root / "outside_static_test.js").write_text("secret", encoding="utf-8")
            with mock.patch("casino.web.server.STATIC_DIR", root / "static"):
                for path in ("/../outside_static_test.js", "/js/../../outside_static_test.js"):
                    with self.subTest(path=path):
                        self.assertIsNone(static_file(path))


class ServerTests(DatabaseTestCase):
    def test_the_casino_opens_in_the_configured_database(self):
        with mock.patch("casino.web.server.DB_PATH", self.db_path.parent / "live.db"):
            casino = open_casino()
        self.assertEqual(len(casino.floor.games), len(load_games(TABLES_DIR)))
        with mock.patch("casino.web.server.open_casino", return_value=casino) as opened:
            create_app()
        opened.assert_called_once()

    def test_unexpected_errors_become_a_500(self):
        app = CasinoApp(self.db, [])
        with (mock.patch.object(app, "dispatch", side_effect=RuntimeError("boom")),
              mock.patch("casino.web.server.traceback.print_exc") as printed):
            reply = app.answer("GET", "session", {}, None)
        self.assertEqual(reply.status, 500)
        printed.assert_called_once()

    def test_an_oversized_body_that_ends_early_is_still_refused(self):
        client = create_app(CasinoApp(self.db, [])).test_client()
        reply = client.post("/api/login", data=b"x" * 10, content_type="application/json",
                            environ_overrides={"CONTENT_LENGTH": str(MAX_BODY_BYTES + 1), "wsgi.input_terminated": True})
        self.assertEqual(reply.status_code, 413)

    def test_deeply_nested_json_is_refused(self):
        with self.assertRaisesRegex(ApiError, "Malformed"):
            parse_json_body("application/json", b"[" * 30_000 + b"]" * 30_000)

    def test_cookies_are_marked_secure_when_configured(self):
        response = Response()
        with mock.patch("casino.web.server.SECURE_COOKIES", True):
            set_cookie(response, "casino_login", "token", 60)
        self.assertIn("Secure", response.headers["Set-Cookie"])

    def test_the_lan_address(self):
        probe = mock.MagicMock()
        probe.__enter__.return_value.getsockname.return_value = ("192.168.1.5", 50000)
        with mock.patch("casino.web.server.socket.socket", return_value=probe):
            self.assertEqual(lan_address(), "192.168.1.5")
        with mock.patch("casino.web.server.socket.socket", side_effect=OSError):
            self.assertIsNone(lan_address())

    def test_serve_says_where_to_connect_and_closes_on_ctrl_c(self):
        server = mock.Mock()
        server.serve_forever.side_effect = KeyboardInterrupt
        app = CasinoApp(self.db, [])
        for host, address, shared in (("0.0.0.0", "192.168.1.5", True), ("::", None, False),
                                      ("127.0.0.1", "192.168.1.5", False)):
            with (self.subTest(host=host), mock.patch("casino.web.server.make_server", return_value=server),
                  mock.patch("casino.web.server.lan_address", return_value=address),
                  mock.patch("sys.stdout", new_callable=io.StringIO) as out):
                serve(app, host, 8000)
                self.assertIn("http://localhost:8000", out.getvalue())
                self.assertEqual("For other players" in out.getvalue(), shared)
        self.assertEqual(server.server_close.call_count, 3)

    def test_verbose_servers_keep_their_request_log(self):
        log = logging.getLogger("werkzeug")
        self.addCleanup(log.setLevel, log.level)
        log.setLevel(logging.NOTSET)
        with mock.patch("casino.web.server.make_wsgi_server") as made:
            make_server(CasinoApp(self.db, []), "127.0.0.1", 0, verbose=True)
        made.assert_called_once()
        self.assertEqual(log.level, logging.NOTSET)

    def test_main_serves_with_the_command_line_options(self):
        with (mock.patch("sys.argv", ["main.py", "--host", "127.0.0.1", "--port", "8080", "--verbose"]),
              mock.patch("main.open_casino", return_value="casino"), mock.patch("main.serve") as served):
            main.main()
        served.assert_called_once_with("casino", "127.0.0.1", 8080, True)

    def test_the_coverage_reports_are_served_from_their_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp) / "coverage"
            (reports / "python").mkdir(parents=True)
            (reports / "index.html").write_text("landing page", encoding="utf-8")
            (reports / "reports.json").write_text("{}", encoding="utf-8")
            (reports / "python" / "index.html").write_text("python report", encoding="utf-8")
            (Path(tmp) / "secret.db").write_text("secret", encoding="utf-8")
            client = create_app(CasinoApp(self.db, [])).test_client()
            with mock.patch("casino.web.server.COVERAGE_DIR", reports):
                self.assertEqual(client.get("/coverage", buffered=True).status_code, 308)
                index = client.get("/coverage/", buffered=True)
                self.assertEqual(index.get_data(as_text=True), "landing page")
                self.assertNotIn("Content-Security-Policy", index.headers)
                self.assertEqual(client.get("/coverage/python/", buffered=True).get_data(as_text=True), "python report")
                self.assertEqual(client.get("/coverage/reports.json", buffered=True).mimetype, "application/json")
                for path in ("/coverage/js/", "/coverage/../secret.db", "/coverage/%2e%2e/secret.db"):
                    with self.subTest(path=path):
                        self.assertEqual(client.get(path, buffered=True).status_code, 404)


class HttpTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.base = serve_in_background(self, self.app)
        self.browser = Browser(self.base)

    def api(self, path, data=None):
        status, _, body = self.browser.request("/api/" + path, json_body=data)
        return status, body

    def test_login_cookie_and_a_full_round(self):
        self.assertEqual(self.api("lobby")[0], 401)
        status, body = self.api("login", {"username": "Ronovo", "password": "hunter22"})
        self.assertEqual((status, body["user"]), (200, "Ronovo"))
        self.api("characters/select", {"id": body["characters"][0]["id"]})

        self.stack(["AS", "9H", "KH", "7D"])
        status, body = self.api("tables/blackjack/start", {"bets": {"bet": 10}})
        self.assertEqual((status, body["round"]["result"]["net"]), (200, 15))
        self.assertEqual(self.api("logout", {})[0], 200)
        self.assertEqual(self.api("lobby")[0], 401)

    def test_login_cookie_is_http_only_and_same_site(self):
        _, headers, _ = self.browser.request("/api/login", json_body={"username": "Ronovo", "password": "hunter22"})
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)

    def test_wrong_password_is_rejected(self):
        status, body = self.api("login", {"username": "Ronovo", "password": "wrong"})
        self.assertEqual(status, 400)
        self.assertNotIn("user", body)

    def test_static_files(self):
        status, headers, body = self.browser.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", body)
        self.assertIn("Content-Security-Policy", headers)
        self.assertEqual(self.browser.request("/js/app.js")[0], 200)
        for path in ("/nothing.js", "/js"):
            with self.subTest(path=path):
                self.assertEqual(self.browser.request(path)[0], 404)

    def test_a_malformed_cookie_reads_as_no_cookie(self):
        status, _, body = self.browser.request("/api/session", headers={"Cookie": 'casino_login="unterminated; x'})
        self.assertEqual(status, 200)
        self.assertIsNone(body["user"])

    def test_a_post_without_a_length_is_refused(self):
        connection = http.client.HTTPConnection("127.0.0.1", urlsplit(self.base).port, timeout=10)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/api/login")
        connection.endheaders()
        self.assertEqual(connection.getresponse().status, 411)

    def test_malformed_requests(self):
        self.assertEqual(self.browser.request("/api/login", raw=b"{not json")[0], 400)
        self.assertEqual(self.browser.request("/api/login", raw=b"[1, 2]")[0], 400)
        self.assertEqual(self.browser.request("/api/login", raw=b"a=1", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.browser.request("/api/login", raw=b"x" * 70_000)[0], 413)
        self.assertEqual(self.browser.request("/api/nowhere", json_body={})[0], 401)
        self.assertEqual(self.browser.request("/login", json_body={})[0], 404)
