"""Accounts, the floor service and the HTTP server, including a real socket round trip."""
import http.client
import json
import random
import threading
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from unittest import mock

from casino.accounts import AccountError, Accounts, hash_password, verify_password
from casino.cashier import break_chips, color_up
from casino.config import TABLES_DIR
from casino.engine.cards import Shoe
from casino.engine.chips import Chips
from casino.engine.db import Character
from casino.games import load_games
from casino.web.floor import Floor
from casino.web.server import CasinoApp, make_server, static_file
from Tests.helpers import DatabaseTestCase, login, SECURITY, SECURITY_BODY



class CashierTests(DatabaseTestCase):
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

    def test_portfolio_names_stay_twenty_characters_with_a_number_added(self):
        for n in range(1, 11):
            self.db.create_user("player" + ("" if n == 1 else str(n)), "unused")
        self.assertEqual(self.accounts.portfolio_user("7", "player").username, "player11")
        long_name = "x" * 20
        self.db.create_user(long_name, "unused")
        for n in range(2, 11):
            self.db.create_user(f"{long_name[:20 - len(str(n))]}{n}", "unused")
        self.assertEqual(self.accounts.portfolio_user("8", long_name).username, f"{long_name[:18]}11")

class AppTestCase(DatabaseTestCase):
    """A CasinoApp with seeded randomness and one logged-in, seated player."""

    def setUp(self):
        super().setUp()
        self.games = load_games(TABLES_DIR)
        self.app = CasinoApp(self.db, self.games, Floor(self.db, self.games, rng_factory=lambda: random.Random(7)))
        self.token = self.signup("Ronovo", "Ronovo Ronove", "Medium")

    def signup(self, username, character, difficulty):
        token = self.app.dispatch("POST", "register", {"username": username, "password": "hunter22", **SECURITY_BODY}, None).token
        reply = self.app.dispatch("POST", "characters", {"name": character, "difficulty": difficulty}, token)
        self.assertEqual(reply.status, 200, reply.body)
        return token

    def call(self, method, path, data=None, token="default", status=200):
        reply = self.app.dispatch(method, path, data or {}, self.token if token == "default" else token)
        self.assertEqual(reply.status, status, reply.body)
        return reply.body

    def seat(self, name="Ronovo Ronove"):
        with self.db.connect() as conn:
            row = conn.execute("SELECT id, name, difficulty, user_id FROM Characters WHERE name = ?", (name,)).fetchone()
        return self.app.floor.seat(Character(*row))

    def stack(self, cards):
        self.seat().session.shoe_factory = lambda decks: Shoe.stacked(cards)


class FloorTests(AppTestCase):
    def test_session_lists_the_account_and_its_characters(self):
        body = self.call("GET", "session")
        self.assertEqual(body["user"], "Ronovo")
        self.assertEqual([(c["name"], c["credits"]) for c in body["characters"]], [("Ronovo Ronove", 1000)])
        self.assertEqual(body["character"], body["characters"][0]["id"])
        self.assertIsNone(self.call("GET", "session", token=None)["user"])

    def test_everything_but_login_needs_an_account_and_a_character(self):
        self.call("GET", "lobby", token=None, status=401)
        self.call("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}}, token="forged", status=401)
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
            self.app.dispatch("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}}, self.token)
        self.assertEqual(self.seat().session.wallet.total, 1000)
        self.assertEqual(self.db.load_chips(self.seat().session.character.id).total, 1000)
        self.assertFalse(self.call("GET", "lobby")["tables"][0]["in_progress"])

    def test_blackjack_round_over_the_api(self):
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        body = self.call("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}})
        self.assertFalse(body["round"]["finished"])
        self.assertEqual(body["player"]["credits"], 990)
        self.assertTrue(self.call("GET", "lobby")["tables"][0]["in_progress"])
        self.assertIsNotNone(self.call("GET", "tables/blackjack_classic")["round"])

        self.call("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}}, status=409)
        self.call("POST", "tables/blackjack_classic/act", {"action": "fly"}, status=400)
        body = self.call("POST", "tables/blackjack_classic/act", {"action": "stand"})
        self.assertTrue(body["round"]["finished"])
        self.assertEqual(body["round"]["result"]["net"], 10)
        self.assertEqual(body["player"]["credits"], 1010)
        self.assertIn("Baby's First Win", [a["display_name"] for a in body["achievements"]])
        self.assertIsNone(self.call("GET", "tables/blackjack_classic")["round"])
        self.call("POST", "tables/blackjack_classic/act", {"action": "stand"}, status=409)

    def test_bad_requests_are_refused_without_touching_the_wallet(self):
        for path, data in (("tables/nowhere/start", {"bets": {"bet": 10}}),
                           ("tables/blackjack_classic/start", {"bets": {"bet": 5000}}),
                           ("tables/blackjack_classic/start", {"bets": {"bet": -10}}),
                           ("tables/blackjack_classic/start", {"bets": {"bet": "10"}}),
                           ("tables/blackjack_classic/start", {"bets": [10]}),
                           ("tables/blackjack_classic/start", {}),
                           ("tables/roulette_european/start", {"bets": {"bets": [{"kind": ["x"], "selection": 1,
                                                                                    "amount": 5}]}}),
                           ("tables/roulette_european/start", {"bets": {"bets": [{"kind": "dozen", "selection": 4,
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
        self.call("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}})
        self.call("POST", "tables/blackjack_classic/act", {"action": "stand"})
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
        body = self.call("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}})
        self.assertFalse(body["player"]["broke"])
        self.call("POST", "start-over", status=400)
        self.stack(["10S", "9C", "6H", "7D", "5C", "10H"])
        self.call("POST", "tables/blackjack_classic/act", {"action": "hit"})
        body = self.call("POST", "start-over")
        self.assertEqual(body["player"]["credits"], 1000)

    def test_the_cashier_only_breaks_chips_into_a_smaller_color(self):
        self.call("POST", "cashier", {"action": "break", "color": "Red", "into": "Green", "count": 1}, status=400)

    def test_players_cannot_reach_each_others_seats(self):
        rival = self.signup("Rival", "Rival Player", "Easy")
        self.stack(["10S", "9C", "6H", "7D", "10C"])
        self.call("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}})
        self.call("POST", "tables/blackjack_classic/act", {"action": "stand"}, token=rival, status=409)
        mine = self.call("GET", "session")["characters"][0]["id"]
        self.call("POST", "characters/select", {"id": mine}, token=rival, status=400)
        self.assertEqual(self.call("GET", "lobby", token=rival)["player"]["credits"], 10_000)

    def test_stake_is_refunded_when_the_server_restarts_mid_round(self):
        self.stack(["8S", "9C", "8H", "7D", "3C", "10D"])
        self.call("POST", "tables/blackjack_classic/start", {"bets": {"bet": 10}})
        self.call("POST", "tables/blackjack_classic/act", {"action": "split"})
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


class HttpTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.server = make_server(self.app, "127.0.0.1", 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def request(self, path, data=None, headers=None, raw=None):
        body = raw if raw is not None else (None if data is None else json.dumps(data).encode())
        request = urllib.request.Request(self.base + path, data=body,
                                         headers=headers or {"Content-Type": "application/json"})
        try:
            with self.browser.open(request, timeout=10) as response:
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read(), error.headers

    def api(self, path, data=None):
        status, body, _ = self.request("/api/" + path, data)
        return status, json.loads(body)

    def test_login_cookie_and_a_full_round(self):
        self.assertEqual(self.api("lobby")[0], 401)
        status, body = self.api("login", {"username": "Ronovo", "password": "hunter22"})
        self.assertEqual((status, body["user"]), (200, "Ronovo"))
        self.api("characters/select", {"id": body["characters"][0]["id"]})

        self.stack(["AS", "9H", "KH", "7D"])
        status, body = self.api("tables/blackjack_classic/start", {"bets": {"bet": 10}})
        self.assertEqual((status, body["round"]["result"]["net"]), (200, 20))
        self.assertEqual(self.api("logout", {})[0], 200)
        self.assertEqual(self.api("lobby")[0], 401)

    def test_login_cookie_is_http_only_and_same_site(self):
        _, _, headers = self.request("/api/login", {"username": "Ronovo", "password": "hunter22"})
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)

    def test_wrong_password_is_rejected(self):
        status, body = self.api("login", {"username": "Ronovo", "password": "wrong"})
        self.assertEqual(status, 400)
        self.assertNotIn("user", body)

    def test_static_files_and_path_traversal(self):
        status, body, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", body)
        self.assertIn("Content-Security-Policy", headers)
        self.assertEqual(self.request("/js/app.js")[0], 200)
        for path in ("/nothing.js", "/js"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_files_outside_the_static_folder_are_never_served(self):
        root = Path(self._tmp.name)
        (root / "static" / "js").mkdir(parents=True)
        (root / "outside_static_test.js").write_text("secret", encoding="utf-8")
        with mock.patch("casino.web.server.STATIC_DIR", root / "static"):
            for path in ("/../outside_static_test.js", "/js/../../outside_static_test.js"):
                with self.subTest(path=path):
                    self.assertIsNone(static_file(path))

    def test_a_malformed_cookie_reads_as_no_cookie(self):
        status, body, _ = self.request("/api/session", headers={"Cookie": 'casino_login="unterminated; x'})
        self.assertEqual(status, 200)
        self.assertIsNone(json.loads(body)["user"])

    def test_a_post_without_a_length_is_refused(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/api/login")
        connection.endheaders()
        self.assertEqual(connection.getresponse().status, 411)

    def test_malformed_requests(self):
        self.assertEqual(self.request("/api/login", raw=b"{not json")[0], 400)
        self.assertEqual(self.request("/api/login", raw=b"[1, 2]")[0], 400)
        self.assertEqual(self.request("/api/login", raw=b"a=1", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("/api/login", raw=b"x" * 70_000)[0], 413)
        self.assertEqual(self.request("/api/nowhere", {})[0], 401)
        self.assertEqual(self.request("/login", {})[0], 404)
