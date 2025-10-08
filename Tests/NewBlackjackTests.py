import sqlite3
import unittest
import os
import tempfile
import gc
import time
from unittest.mock import patch
from Games import blackjack
from DAL import character_maintenance as cm
from DAL import blackjack_maintenance as bjs
from DAL import money_maintenance as mm
from DAL import achievement_maintenance as am

def build_character_data(rawCharacterData):
    newCharacterData = {'name': rawCharacterData[1], 'credits': rawCharacterData[2], 'current_bet': 0,
                        'difficulty': rawCharacterData[4], 'blackjack_id': rawCharacterData[5]}
    return newCharacterData

@patch('Games.blackjack.input', create=True)
class MyTestCase(unittest.TestCase):

    def setUp(self):
        tmp_dir = tempfile.gettempdir()
        self.db_name = os.path.join(tmp_dir, "test_blackjack.sqlite")
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
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Blackjack (
        blackjack_id INTEGER PRIMARY KEY AUTOINCREMENT,
        current_bet INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT,
        description TEXT
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS CharacterAchievements (
        character_id INTEGER,
        achievement_id INTEGER,
        PRIMARY KEY (character_id, achievement_id)
        )''')
        self.conn.commit()

        # Point DAL modules to this temp database
        cm.DB_PATH = self.db_name
        bjs.DB_PATH = self.db_name
        mm.DB_PATH = self.db_name
        am.DB_PATH = self.db_name

        #Create Test Data
        self.cursor.execute("""
                INSERT INTO Characters (name, credits, difficulty)
                VALUES (?, ?, ?)
            """, ("Test User", 10, "Hard"))
        # Insert minimal achievements referenced by gameplay
        self.cursor.executemany("""
            INSERT INTO Achievements (name, display_name, description)
            VALUES (?, ?, ?)
        """, [
            ("Blackjack_21", "Blackjack: 21!", "Win with 21"),
            ("Blackjack_Win", "Blackjack Winner", "Win a hand"),
            ("Blackjack_Lose", "Blackjack Loss", "Lose a hand"),
            ("Blackjack_Draw", "Blackjack Draw", "Draw a hand")
        ])
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

    def test_PlayerWins_Blackjack(self, mocked_input):
        print("----------------------------------")
        print("Test #1 : Player Wins With 21")
        print("----------------------------------")
        # Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['1', '11','','', '2','','','']
        deck = ['KS', 'AS', '1S', '6D', '4H']
        #Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)
        result = blackjack.dealin(deck, self.characterData)
        self.assertEqual(result, "You Win with 21!")

    def test_DealerWins_Blackjack(self, mocked_input):
        print("----------------------------------")
        print("Test #2 : Dealer Wins With 21")
        print("----------------------------------")
        # 3 for Stand (no Ace input needed since no player Aces)
        mocked_input.side_effect = ['1', '','','2', '','','']
        deck = ['KS', 'QS', '1S', 'AD']
        #Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)
        result = blackjack.dealin(deck, self.characterData)
        self.assertEqual(result, "The House Wins!")

    def test_PlayerWins_DealerOver21(self, mocked_input):
        print("----------------------------------")
        print("Test #3 : Dealer Busts, Player Wins")
        print("----------------------------------")
        # 3 for Stand (no Ace input needed since no player Aces)
        mocked_input.side_effect = ['1','','', '2', '','','']
        deck = ['KS', 'QS', '1S', '6D', '6H']
        #Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)
        result = blackjack.dealin(deck, self.characterData)
        self.assertEqual(result, "You Win!")

    def test_Draw21(self, mocked_input):
        print("----------------------------------")
        print("Test #4 : Draw")
        print("----------------------------------")
        # Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['1', '11', '','','2', '','','']
        deck = ['KS', 'AS', '1S', 'AD']
        #Get that Test Data
        self.cursor.execute("SELECT * FROM Characters WHERE name = ?", ("Test User",))
        self.rawCharacterData = self.cursor.fetchone()
        self.characterData = build_character_data(self.rawCharacterData)
        result = blackjack.dealin(deck, self.characterData)
        self.assertEqual(result, "It's a draw! All bets returned")


    '''

    @patch('Characters.charactermaintenance.saveCharacter')
    @patch('Games.blackjack.input', create=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_Draw21(self, mock_file, mocked_input, mock_save):
        # Ace Value for Player, 3 for Stand
        mocked_input.side_effect = ['1', '11', '3']
        mock_file.return_value.read.return_value = json.dumps(self.mock_achievements)
        deck = ['KS', 'AS', '1S', 'AD']
        result = blackjack.dealin(deck, self.testCharacterData)
        self.assertEqual(result, "It's a draw!")
'''

