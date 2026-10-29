import json
import unittest

from casino.config import ACHIEVEMENTS_PATH, CHARACTER_EXPORT_DIR, load_starting_chips
from casino.engine.chips import Chips, InsufficientChips
from casino.engine.db import DuplicateCharacter
from casino.engine.wallet import Wallet
from casino.transfer import export_character, import_character, read_import
from Tests.helpers import DatabaseTestCase


class StartingChipsTests(unittest.TestCase):
    def test_every_difficulty_matches_its_credits(self):
        expected = {"Easy": 10_000, "Medium": 1_000, "Hard": 100, "Very Hard": 10}
        for difficulty, credits in expected.items():
            self.assertEqual(load_starting_chips(difficulty).total, credits)


class DatabaseTests(DatabaseTestCase):
    def test_initialize_is_idempotent(self):
        self.db.initialize(ACHIEVEMENTS_PATH)
        count = "SELECT COUNT(*) FROM Achievements"
        with self.db.connect() as conn:
            before = conn.execute(count).fetchone()[0]
        self.db.initialize(ACHIEVEMENTS_PATH)
        with self.db.connect() as conn:
            self.assertEqual(conn.execute(count).fetchone()[0], before)

    def test_duplicate_character_names_are_rejected(self):
        self.db.create_character("Ronovo", "Hard", Chips(White=10))
        with self.assertRaises(DuplicateCharacter):
            self.db.create_character("Ronovo", "Easy", Chips())

    def test_chips_round_trip(self):
        character = self.db.create_character("Ronovo", "Hard", Chips(White=10, Red=8))
        self.db.save_chips(character.id, Chips(Green=3))
        self.assertEqual(self.db.load_chips(character.id), Chips(Green=3))

    def test_record_round_aggregates(self):
        character = self.db.create_character("Ronovo", "Hard", Chips())
        for net in (10, -5, 0, 40):
            self.db.record_round(character.id, "blackjack", net)
        stats = self.db.get_stats(character.id)["blackjack"]
        self.assertEqual(stats, {"wins": 2, "losses": 1, "pushes": 1, "net_credits": 45, "biggest_win": 40})

    def test_achievements_unlock_once(self):
        character = self.db.create_character("Ronovo", "Hard", Chips())
        self.assertIsNotNone(self.db.unlock_achievement(character.id, "Blackjack_Win"))
        self.assertIsNone(self.db.unlock_achievement(character.id, "Blackjack_Win"))
        with self.assertRaises(KeyError):
            self.db.unlock_achievement(character.id, "Not_A_Real_Achievement")

    def test_editing_achievement_json_updates_existing_database(self):
        path = self.db_path.parent / "achievements.json"
        path.write_text(json.dumps([{"Blackjack": [
            {"name": "Blackjack_Win", "displayName": "Renamed", "description": "Edited"}]}]), encoding="utf-8")
        self.db.sync_achievements(path)
        character = self.db.create_character("Ronovo", "Hard", Chips())
        achievement = self.db.unlock_achievement(character.id, "Blackjack_Win")
        self.assertEqual(achievement.display_name, "Renamed")


class WalletTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.character = self.db.create_character("Ronovo", "Hard", Chips(White=10, Red=8, Green=2))
        self.wallet = Wallet.load(self.db, self.character.id)

    def test_withdraw_and_deposit_persist(self):
        self.wallet.withdraw(26)
        self.wallet.deposit(52)
        self.assertEqual(self.wallet.total, 126)
        self.assertEqual(self.db.load_chips(self.character.id).total, 126)

    def test_withdraw_exact_chips(self):
        self.wallet.withdraw(Chips(Green=2))
        self.assertEqual(self.wallet.chips, Chips(White=10, Red=8))

    def test_cannot_overdraw(self):
        with self.assertRaises(InsufficientChips):
            self.wallet.withdraw(101)
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

    def test_every_reached_threshold_unlocks(self):
        session = self.make_session(credits=100_000, difficulty="Very Hard")
        session.check_money_achievements()
        self.assertEqual(self.unlocked(session), {"Money_100", "Money_1000", "Money_10000", "Money_100000"})


class TransferTests(DatabaseTestCase):
    def test_import_export_file(self):
        character = read_import(self.db, CHARACTER_EXPORT_DIR / "Ronovo Ronove.json")
        self.assertEqual(character.difficulty, "Very Hard")
        self.assertEqual(self.db.load_chips(character.id), Chips(White=11, Green=4))
        self.assertEqual(self.db.get_stats(character.id)["blackjack"]["wins"], 139)
        unlocked = {a.name for a in self.db.achievements(character.id) if a.unlocked}
        self.assertEqual(unlocked, {"Blackjack_Lose", "Blackjack_Win", "Blackjack_21", "Blackjack_Draw", "Money_100"})

    def test_export_import_round_trip_under_new_name(self):
        character = self.db.create_character("Ronovo", "Hard", Chips(Black=3))
        self.db.record_round(character.id, "roulette", 350)
        self.db.unlock_achievement(character.id, "Roulette_Straight")
        data = export_character(self.db, "Ronovo")

        copy = import_character(self.db, json.loads(json.dumps(data)), name="Ronovo Copy")
        self.assertEqual(self.db.load_chips(copy.id).total, 300)
        self.assertEqual(self.db.get_stats(copy.id)["roulette"]["biggest_win"], 350)
        self.assertIn("Roulette_Straight", {a.name for a in self.db.achievements(copy.id) if a.unlocked})

    def test_export_unknown_character(self):
        with self.assertRaises(ValueError):
            export_character(self.db, "Nobody")


if __name__ == "__main__":
    unittest.main()
