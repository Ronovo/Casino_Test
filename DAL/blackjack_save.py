import sqlite3
from DAL import character_maintenance as cm

DB_PATH = "casino.db"

# --------------------------------------------------------
# BLACKJACK CREATE LINK
# --------------------------------------------------------
def create_new_blackjack_entry():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Blackjack entry
    cursor.execute("""
               INSERT INTO Blackjack (current_bet,wins, losses, draws) VALUES (0, 0, 0, 0);
            """)
    blackjack_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return blackjack_id

def update_character_with_blackjack(blackjack_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE Characters
            SET blackjack_id = ?
            WHERE name = ?
        """, (
        blackjack_id,
        name
    ))

    conn.commit()
    conn.close()

def create_blackjack_connection(characterData):
    """
    Create a connection to a new BlackJackID to the CharacterData
    Expects a dict (like load_character_by_name returns).
    """

    blackjack_id = create_new_blackjack_entry()
    update_character_with_blackjack(blackjack_id, characterData["name"])

    return cm.load_character_by_name(characterData["name"])

# --------------------------------------------------------
# BLACKJACK GET METHODS
# --------------------------------------------------------
def get_blackjack_id(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT blackjack_id FROM Characters WHERE name = ?",
                   (name,))
    id = cursor.fetchone()
    return id[0]

def get_blackjack_wins(blackjack_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT wins FROM Blackjack WHERE blackjack_id = ?",
                   (blackjack_id,))
    wins = cursor.fetchone()
    return wins[0]

def get_blackjack_losses(blackjack_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT losses FROM Blackjack WHERE blackjack_id = ?",
                   (blackjack_id,))
    losses = cursor.fetchone()
    return losses[0]

def get_blackjack_draws(blackjack_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT draws FROM Blackjack WHERE blackjack_id = ?",
                   (blackjack_id,))
    draws = cursor.fetchone()
    return draws[0]

# --------------------------------------------------------
# BLACKJACK UPDATE METHODS
# --------------------------------------------------------
def update_blackjack_wins(name):
    blackjack_id = get_blackjack_id(name)
    wins = get_blackjack_wins(blackjack_id)
    wins += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update the Current Bet
    cursor.execute("""
                   UPDATE Blackjack
                   SET wins = ?
                   WHERE blackjack_id = ?
                """, (
        wins,
        blackjack_id
    ))
    conn.commit()
    conn.close()

def update_blackjack_losses(name):
    blackjack_id = get_blackjack_id(name)
    losses = get_blackjack_losses(blackjack_id)
    losses += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update the Current Bet
    cursor.execute("""
                   UPDATE Blackjack
                   SET losses = ?
                   WHERE blackjack_id = ?
                """, (
        losses,
        blackjack_id
    ))
    conn.commit()
    conn.close()

def update_blackjack_draws(name):
    blackjack_id = get_blackjack_id(name)
    draws = get_blackjack_draws(blackjack_id)
    draws += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update the Current Bet
    cursor.execute("""
                   UPDATE Blackjack
                   SET draws = ?
                   WHERE blackjack_id = ?
                """, (
        draws,
        blackjack_id
    ))
    conn.commit()
    conn.close()

