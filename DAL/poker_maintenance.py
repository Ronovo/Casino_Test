import sqlite3
from DAL import character_maintenance as cm

DB_PATH = "casino.db"

# --------------------------------------------------------
# Poker CREATE LINK
# --------------------------------------------------------
def create_new_poker_entry():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Poker entry
    cursor.execute("""
               INSERT INTO Poker (wins, losses, draws) VALUES (0, 0, 0);
            """)
    poker_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return poker_id

def update_character_with_poker(poker_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE Characters
            SET poker_id = ?
            WHERE name = ?
        """, (
        poker_id,
        name
    ))

    conn.commit()
    conn.close()

def create_poker_connection(characterData):
    """
    Create a connection to a new poker_id to the CharacterData
    Expects a dict (like load_character_by_name returns).
    """

    poker_id = create_new_poker_entry()
    update_character_with_poker(poker_id, characterData["name"])

    return cm.load_character_by_name(characterData["name"])

# --------------------------------------------------------
# POKER GET METHODS
# --------------------------------------------------------
def get_poker_id(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT poker_id FROM Characters WHERE name = ?",
                   (name,))
    id = cursor.fetchone()
    return id[0]

def get_poker_ante(name):
    poker_id = get_poker_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT ante FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    ante = cursor.fetchone()
    return ante[0]

def get_poker_trips(name):
    poker_id = get_poker_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT trips FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    trips = cursor.fetchone()
    return trips[0]

def get_poker_pairs(name):
    poker_id = get_poker_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pairs FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    pairs = cursor.fetchone()
    return pairs[0]

def get_poker_wins(poker_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT wins FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    wins = cursor.fetchone()
    return wins[0]

def get_poker_losses(poker_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT losses FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    losses = cursor.fetchone()
    return losses[0]

def get_poker_draws(poker_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT draws FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    draws = cursor.fetchone()
    return draws[0]

def get_blind_modifier(scoreValue):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT modifier FROM PokerBlinds WHERE score_value = ?",
                   (scoreValue,))
    modifier = cursor.fetchone()
    return modifier[0]

def get_trips_modifier(scoreValue):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT modifier FROM PokerTrips WHERE score_value = ?",
                   (scoreValue,))
    modifier = cursor.fetchone()
    return modifier[0]

def get_pairs_modifier(scoreValue):
    if scoreValue.isnumeric():
        if 2 <= int(scoreValue) <= 9:
            scoreValue = "2"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT modifier FROM PokerPairs WHERE score_value = ?",
                   (str(scoreValue),))
    modifier = cursor.fetchone()
    return modifier[0]
# --------------------------------------------------------
# POKER UPDATE METHODS
# --------------------------------------------------------
def update_poker_initial_bet(name, ante, trips, pairs):
    poker_id = get_poker_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                       UPDATE Poker
                       SET ante = ?, trips = ?, pairs = ?
                       WHERE poker_id = ?
                    """, (ante, trips, pairs, poker_id))
    conn.commit()
    conn.close()

    update_character_with_poker(poker_id, name)
    return cm.load_character_by_name(name)

def update_poker_wins(name):
    poker_id = get_poker_id(name)
    wins = get_poker_wins(poker_id)
    wins += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   UPDATE Poker
                   SET wins = ?
                   WHERE poker_id = ?
                """, (
        wins,
        poker_id
    ))
    conn.commit()
    conn.close()

def update_poker_losses(name):
    poker_id = get_poker_id(name)
    losses = get_poker_losses(poker_id)
    losses += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update the Current Bet
    cursor.execute("""
                   UPDATE Poker
                   SET losses = ?
                   WHERE poker_id = ?
                """, (
        losses,
        poker_id
    ))
    conn.commit()
    conn.close()

def update_poker_draws(name):
    poker_id = get_poker_id(name)
    draws = get_poker_draws(poker_id)
    draws += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   UPDATE Poker
                   SET draws = ?
                   WHERE poker_id = ?
               """, (
        draws,
        poker_id
    ))
    conn.commit()
    conn.close()

