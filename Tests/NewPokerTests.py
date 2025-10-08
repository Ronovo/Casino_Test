import sqlite3
import unittest
import os
import tempfile
import gc
import time
from unittest.mock import patch
import formatter

from Games import poker
from DAL import character_maintenance as cm, poker_maintenance as ps, money_maintenance as mm
from Database import load_helper_methods as lhm

def build_character_data(rawCharacterData):
    newCharacterData = {'name': rawCharacterData[1], 'credits': rawCharacterData[2], 'current_bet': 0,
                        'difficulty': rawCharacterData[4], 'poker_id': rawCharacterData[5]}
    return newCharacterData

@patch('Games.poker.input', create=True)
class MyTestCase(unittest.TestCase):

    def setUp(self):
        tmp_dir = tempfile.gettempdir()
        self.db_name = os.path.join(tmp_dir, "test_poker.sqlite")
        # Ensure a clean file
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        #Create Character Temp Table
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        credits INTEGER DEFAULT 0,
        difficulty TEXT,
        blackjack_id INTEGER DEFAULT 0,
        poker_id INTEGER DEFAULT 0,
        FOREIGN KEY (blackjack_id) REFERENCES Blackjack (blackjack_id),
        FOREIGN KEY (poker_id) REFERENCES GuessTheNumber (poker_id)
        )''')
        # Minimal additional tables used by game logic
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Poker (
        poker_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ante DEFAULT 0,
        trips DEFAULT 0,
        pairs DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS PokerBlinds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        score_value INT NOT NULL,
        odds TEXT NOT NULL,
        modifier DOUBLE NOT NULL
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS PokerTrips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                score_value INT NOT NULL,
                odds TEXT NOT NULL,
                modifier DOUBLE NOT NULL
                )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS PokerPairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                score_value TEXT NOT NULL,
                odds TEXT NOT NULL,
                modifier DOUBLE NOT NULL
                )''')
        self.conn.commit()

        # Point DAL modules to this temp database
        cm.DB_PATH = self.db_name
        ps.DB_PATH = self.db_name
        mm.DB_PATH = self.db_name
        lhm.DB_PATH = self.db_name

        #Create Test Data
        self.cursor.execute("""
                INSERT INTO Characters (name, credits, difficulty)
                VALUES (?, ?, ?)
            """, ("Test User", 100, "Hard"))
        
        # Manually load paytables to avoid database locking issues
        import json
        
        # Load blinds
        blindsPath = os.path.join(os.path.dirname(__file__), "Paytables_Test", "blind_modifier.json")
        with open(blindsPath, "r", encoding="utf-8") as f:
            blinds = json.load(f)
        for blind in blinds:
            self.cursor.execute("""
                INSERT OR IGNORE INTO PokerBlinds (name, score_value, odds, modifier)
                VALUES (?, ?, ?, ?)
            """, (blind["name"], blind["score_value"], blind["odds"], blind["modifier"]))
        
        # Load trips
        tripsPath = os.path.join(os.path.dirname(__file__), "Paytables_Test", "trips_modifier.json")
        with open(tripsPath, "r", encoding="utf-8") as f:
            trips = json.load(f)
        for trip in trips:
            self.cursor.execute("""
                INSERT OR IGNORE INTO PokerTrips (name, score_value, odds, modifier)
                VALUES (?, ?, ?, ?)
            """, (trip["name"], trip["score_value"], trip["odds"], trip["modifier"]))
        
        # Load pairs
        pairsPath = os.path.join(os.path.dirname(__file__), "Paytables_Test", "pairs_modifier.json")
        with open(pairsPath, "r", encoding="utf-8") as f:
            pairs = json.load(f)
        for pair in pairs:
            self.cursor.execute("""
                INSERT OR IGNORE INTO PokerPairs (name, score_value, odds, modifier)
                VALUES (?, ?, ?, ?)
            """, (pair["name"], pair["score_value"], pair["odds"], pair["modifier"]))
        
        self.conn.commit()

    def tearDown(self):
        # Close cursor first, then connection
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()
        # Force garbage collection to ensure connections are released
        gc.collect()
        # Small delay to ensure file handles are released
        time.sleep(0.1)
        if self.db_name != ":memory:" and os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except PermissionError:
                # If still locked, try again after a longer delay
                time.sleep(0.5)
                try:
                    os.remove(self.db_name)
                except PermissionError:
                    # If still failing, just leave the file - it will be overwritten next time
                    pass
        # Clear references to help with garbage collection
        if hasattr(self, 'cursor'):
            del self.cursor
        if hasattr(self, 'conn'):
            del self.conn

    def test_poker_royal_flush(self, mocked_input):
        formatter.drawMenuTopper("Test #1 : Royal Flush")

        mocked_input.side_effect = [
            # Initial betting sequence - Set ante and blind
            "1",
            "10",
            # Set trips bet
            "2",
            "10",
            # Set pairs bet
            "3",
            "10",
            # Lock in initial bet
            "4",
            # Pre-flop betting
            "3",  # Pre-flop: 4x ante
            "",   # Enter after Pre-flor bet
            # Post-flop betting
            "2",  # Post-flop: 2x ante
            "",   # Enter after post-flop bet
            "",   # Enter after card reveal
            # Pick Hand
            "1","1","1","1","1",
            # Final betting
            "1",  # Final: Check (no additional bet)
            "",   # Enter after final bet
        ]

        #Deck = (0-1 : Player Hand)(2-3 Dealer)(4-8 Community)
        # Stacked deck: Player gets royal flush, dealer gets flush
        self.deck = ["1S","JS","2S","3S","QS","KS","AS","2D","3D"]
        
        # Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)
        
        result = poker.dealin(self.deck, self.characterData)
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['player_score'], 10)  # Royal Flush
        self.assertEqual(result['dealer_score'], 6)  # Flush
        self.assertTrue(result['final_winnings'] > 0)  # Should win

    def test_poker_straight_flush(self, mocked_input):
        formatter.drawMenuTopper("Test #2 : Straight Flush")

        mocked_input.side_effect = [
            # Initial betting sequence - Set ante and blind
            "1", "10",
            # Set trips bet
            "2", "10",
            # Set pairs bet
            "3", "10",
            # Lock in initial bet
            "4",
            # Pre-flop betting
            "3", "",  # Enter after Pre-flor bet
            # Post-flop betting
            "2", "", "",
            # Pick Hand
            "1", "1", "1", "1", "1",
            # Final betting
            "1", "",
        ]

        # Deck = (0-1 : Player Hand)(2-3 Dealer)(4-8 Community)
        # Stacked deck: Player gets royal flush, dealer gets flush
        self.deck = ["1S", "JS", "2D", "3C", "QS", "KS", "9S", "2D", "3D"]

        # Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)

        result = poker.dealin(self.deck, self.characterData)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['player_score'], 9)  # Straight Flush
        self.assertTrue(result['final_winnings'] > 0)  # Should win

    def test_poker_4_kind(self, mocked_input):
        formatter.drawMenuTopper("Test #3 : 4 of a Kind")

        mocked_input.side_effect = [
            # Initial betting sequence - Set ante and blind
            "1",
            "10",
            # Set trips bet
            "2",
            "10",
            # Set pairs bet
            "3",
            "10",
            # Lock in initial bet
            "4",
            # Pre-flop betting
            "3",  # Pre-flop: 4x ante
            "",  # Enter after Pre-flor bet
            # Post-flop betting
            "2",  # Post-flop: 2x ante
            "",  # Enter after post-flop bet
            "",  # Enter after card reveal
            # Pick Hand
            "1", "1", "1", "1", "1",
            # Final betting
            "1",  # Final: Check (no additional bet)
            "",  # Enter after final bet
        ]

        # Deck = (0-1 : Player Hand)(2-3 Dealer)(4-8 Community)
        # Stacked deck: Player gets royal flush, dealer gets flush
        self.deck = ["AS", "AC", "2D", "3C", "AD", "AH", "9S", "2D", "3D"]

        # Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)

        result = poker.dealin(self.deck, self.characterData)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['player_score'], 8)  # 4 of a kind
        self.assertTrue(result['final_winnings'] > 0)  # Should win

    def test_poker_full_house(self, mocked_input):
        formatter.drawMenuTopper("Test #4 : Full House")

        mocked_input.side_effect = [
            # Initial betting sequence - Set ante and blind
            "1", "10",
            # Set trips bet
            "2", "10",
            # Set pairs bet
            "3", "10",
            # Lock in initial bet
            "4",
            # Pre-flop betting
            "3", "",  # Enter after Pre-flor bet
            # Post-flop betting
            "2", "", "",
            # Pick Hand
            "1", "1", "1", "1", "1",
            # Final betting
            "1", "",
        ]

        # Deck = (0-1 : Player Hand)(2-3 Dealer)(4-8 Community)
        # Stacked deck: Player gets royal flush, dealer gets flush
        self.deck = ["AS", "AC", "2D", "3C", "QS", "QC", "QH", "2D", "3D"]

        # Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)

        result = poker.dealin(self.deck, self.characterData)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['player_score'], 7)  # Full House
        self.assertTrue(result['final_winnings'] > 0)  # Should win

    def test_poker_flush(self, mocked_input):
        formatter.drawMenuTopper("Test #5 : Flush")

        mocked_input.side_effect = [
            # Initial betting sequence - Set ante and blind
            "1","10",
            # Set trips bet
            "2","10",
            # Set pairs bet
            "3","10",
            # Lock in initial bet
            "4",
            # Pre-flop betting
            "3","",  # Enter after Pre-flor bet
            # Post-flop betting
            "2","","",
            # Pick Hand
            "1", "1", "1", "1", "1",
            # Final betting
            "1","",
        ]

        # Deck = (0-1 : Player Hand)(2-3 Dealer)(4-8 Community)
        # Stacked deck: Player gets royal flush, dealer gets flush
        self.deck = ["1S", "JS", "2D", "3C", "6S", "8S", "9S", "2D", "3D"]

        # Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)

        result = poker.dealin(self.deck, self.characterData)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['player_score'], 6)  # Flush
        self.assertTrue(result['final_winnings'] > 0)  # Should win

    def test_poker_straight(self, mocked_input):
        formatter.drawMenuTopper("Test #6 : Straight")

        mocked_input.side_effect = [
            # Initial betting sequence - Set ante and blind
            "1","10",
            # Set trips bet
            "2","10",
            # Set pairs bet
            "3","10",
            # Lock in initial bet
            "4",
            # Pre-flop betting
            "3","",  # Enter after Pre-flor bet
            # Post-flop betting
            "2","","",
            # Pick Hand
            "1", "1", "1", "1", "1",
            # Final betting
            "1","",
        ]

        # Deck = (0-1 : Player Hand)(2-3 Dealer)(4-8 Community)
        # Stacked deck: Player gets royal flush, dealer gets flush
        self.deck = ["1S", "JS", "2D", "3C", "7S", "8S", "9C", "2D", "3D"]

        # Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)

        result = poker.dealin(self.deck, self.characterData)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['player_score'], 5)  # Straight
        self.assertTrue(result['final_winnings'] > 0)  # Should win

    def test_poker_3_kind(self, mocked_input):
        formatter.drawMenuTopper("Test #7 : 3 of a Kind")

        mocked_input.side_effect = [
            # Initial betting sequence - Set ante and blind
            "1","10",
            # Set trips bet
            "2","10",
            # Set pairs bet
            "3","10",
            # Lock in initial bet
            "4",
            # Pre-flop betting
            "3","",  # Enter after Pre-flor bet
            # Post-flop betting
            "2","","",
            # Pick Hand
            "1", "1", "1", "1", "1",
            # Final betting
            "1","",
        ]

        # Deck = (0-1 : Player Hand)(2-3 Dealer)(4-8 Community)
        # Stacked deck: Player gets royal flush, dealer gets flush
        self.deck = ["AS", "AC", "2D", "3C", "AH", "8S", "9C", "2D", "3D"]

        # Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)

        result = poker.dealin(self.deck, self.characterData)

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['player_score'], 4)  # 3 of a kind
        self.assertTrue(result['final_winnings'] > 0)  # Should win

if __name__ == '__main__':
    unittest.main()
