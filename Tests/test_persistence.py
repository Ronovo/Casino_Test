import json
import tempfile
import unittest
from pathlib import Path

from casino.config import ACHIEVEMENTS_PATH, load_starting_chips
from casino.engine.chips import Chips, InsufficientChips
from casino.engine.db import Database, DuplicateCharacter
from casino.engine.session import Session
from casino.engine.wallet import Wallet
from Tests.helpers import DatabaseTestCase


class StartingChipsTests(unittest.TestCase):
    def test_every_difficulty_matches_its_credits(self):
        expected = {"Easy": 10_000, "Medium": 1_000, "Hard": 100, "Very Hard": 10}
        for difficulty, credits in expected.items():
            self.assertEqual(load_starting_chips(difficulty).total, credits)

    def test_chips_json_must_match_the_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chips.json"
            path.write_text(json.dumps([{"color": "White", "credit_value": 2, "medium_amount": 1}]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "White"):
                load_starting_chips("Medium", path)


class DatabaseTests(DatabaseTestCase):
    def test_initialize_is_idempotent(self):
        count = "SELECT COUNT(*) FROM Achievements"
        with self.db.connect() as conn:
            before = conn.execute(count).fetchone()[0]
        self.db.initialize(ACHIEVEMENTS_PATH)
        with self.db.connect() as conn:
            self.assertEqual(conn.execute(count).fetchone()[0], before)

    def test_a_database_without_achievement_definitions(self):
        db = Database(self.db_path.parent / "bare.db")
        db.initialize()
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Achievements").fetchone()[0], 0)

    def test_nested_transactions_commit_or_roll_back_as_one(self):
        with self.assertRaises(RuntimeError), self.db.transaction():
            with self.db.transaction():
                self.db.create_character("Ronovo", "Hard", Chips(White=10), self.owner.id)
            raise RuntimeError("abandon")
        self.assertEqual(self.db.list_characters(self.owner.id), [])

    def test_duplicate_character_names_are_rejected(self):
        self.db.create_character("Ronovo", "Hard", Chips(White=10), self.owner.id)
        with self.assertRaises(DuplicateCharacter):
            self.db.create_character("Ronovo", "Easy", Chips(), self.owner.id)

    def test_chips_round_trip(self):
        character = self.db.create_character("Ronovo", "Hard", Chips(White=10, Red=8), self.owner.id)
        self.db.save_chips(character.id, Chips(Green=3))
        self.assertEqual(self.db.load_chips(character.id), Chips(Green=3))

    def test_record_round_aggregates(self):
        character = self.db.create_character("Ronovo", "Hard", Chips(), self.owner.id)
        for net in (10, -5, 0, 40):
            self.db.record_round(character.id, "blackjack", net)
        stats = self.db.get_stats(character.id)["blackjack"]
        self.assertEqual(stats, {"wins": 2, "losses": 1, "pushes": 1, "net_credits": 45, "biggest_win": 40})

    def test_achievements_unlock_once(self):
        character = self.db.create_character("Ronovo", "Hard", Chips(), self.owner.id)
        self.assertIsNotNone(self.db.unlock_achievement(character.id, "Blackjack_Win"))
        self.assertIsNone(self.db.unlock_achievement(character.id, "Blackjack_Win"))
        with self.assertRaises(KeyError):
            self.db.unlock_achievement(character.id, "Not_A_Real_Achievement")

    def test_editing_achievement_json_updates_existing_database(self):
        path = self.db_path.parent / "achievements.json"
        path.write_text(json.dumps({"Blackjack": [
            {"name": "Blackjack_Win", "displayName": "Renamed", "description": "Edited"}]}), encoding="utf-8")
        self.db.sync_achievements(path)
        character = self.db.create_character("Ronovo", "Hard", Chips(), self.owner.id)
        achievement = self.db.unlock_achievement(character.id, "Blackjack_Win")
        self.assertEqual(achievement.display_name, "Renamed")


class WalletTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.character = self.db.create_character("Ronovo", "Hard", Chips(White=10, Red=8, Green=2), self.owner.id)
        self.wallet = Wallet.load(self.db, self.character.id)

    def test_withdraw_and_deposit_persist(self):
        self.wallet.withdraw(26)
        self.wallet.deposit(52)
        self.assertEqual(self.wallet.total, 126)
        self.assertEqual(self.db.load_chips(self.character.id).total, 126)

    def test_cannot_overdraw(self):
        with self.assertRaises(InsufficientChips):
            self.wallet.withdraw(101)
        self.assertEqual(self.wallet.total, 100)

    def test_cannot_deposit_a_negative_amount(self):
        with self.assertRaises(ValueError):
            self.wallet.deposit(-1)
        self.assertEqual(self.wallet.total, 100)

    def test_exchange_must_keep_total(self):
        with self.assertRaises(ValueError):
            self.wallet.exchange(Chips(Black=2))
        self.wallet.exchange(Chips(Black=1))
        self.assertEqual(self.wallet.chips, Chips(Black=1))


class SessionAchievementTests(DatabaseTestCase):
    def test_money_achievements_respect_difficulty(self):
        hard = self.make_session(credits=1000, difficulty="Hard", name="Hard Player")
        hard.check_money_achievements()
        self.assertEqual(self.unlocked(hard), {"Money_1000"})

        easy = self.make_session(credits=None, difficulty="Easy", name="Easy Player")
        easy.check_money_achievements()
        self.assertEqual(self.unlocked(easy), set())

    def test_an_achievement_unlocked_in_another_sitting_is_not_announced_again(self):
        first = self.make_session()
        second = Session(self.db, first.character, Wallet.load(self.db, first.character.id))
        second.unlock("Blackjack_Win")
        first.unlock("Roulette_Win")
        second.unlock("Roulette_Win")
        self.assertEqual([a["display_name"] for a in second.pop_achievements()], ["Baby's First Win"])

    def test_every_reached_threshold_unlocks(self):
        session = self.make_session(credits=100_000, difficulty="Very Hard")
        session.check_money_achievements()
        self.assertEqual(self.unlocked(session), {"Money_100", "Money_1000", "Money_10000", "Money_100000"})


if __name__ == "__main__":
    unittest.main()
