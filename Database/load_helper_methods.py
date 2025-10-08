import sqlite3
import json

DB_PATH = "casino.db"


# --------------------------------------------------------
# ACHIEVEMENTS
# --------------------------------------------------------
def load_achievements_from_json(path):
    """Import static achievements from JSON into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(path, "r", encoding="utf-8") as f:
        achievements = json.load(f)

    for ach in achievements:
        cursor.execute("""
            INSERT OR IGNORE INTO Achievements (name, display_name, description)
            VALUES (?, ?, ?)
        """, (ach["name"], ach["displayName"], ach["description"]))

    conn.commit()
    conn.close()
# --------------------------------------------------------
# Poker
# --------------------------------------------------------
def load_poker_blinds(path):
    """Import static achievements from JSON into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(path, "r", encoding="utf-8") as f:
        blinds = json.load(f)

    for blind in blinds:
        cursor.execute("""
            INSERT OR IGNORE INTO PokerBlinds (name, score_value, odds, modifier)
            VALUES (?, ?, ?, ?)
        """, (blind["name"], blind["score_value"], blind["odds"], blind["modifier"],))

    conn.commit()
    conn.close()

def load_poker_trips(path):
    """Import static achievements from JSON into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(path, "r", encoding="utf-8") as f:
        trips = json.load(f)

    for trip in trips:
        cursor.execute("""
            INSERT OR IGNORE INTO PokerTrips (name, score_value, odds, modifier)
            VALUES (?, ?, ?, ?)
        """, (trip["name"], trip["score_value"], trip["odds"], trip["modifier"],))

    conn.commit()
    conn.close()

def load_poker_pairs(path):
    """Import static achievements from JSON into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    for pair in pairs:
        cursor.execute("""
            INSERT OR IGNORE INTO PokerPairs (name, score_value, odds, modifier)
            VALUES (?, ?, ?, ?)
        """, (pair["name"], pair["score_value"], pair["odds"], pair["modifier"],))

    conn.commit()
    conn.close()