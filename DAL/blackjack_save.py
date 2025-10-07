import sqlite3
from DAL import character_maintenance as cm

DB_PATH = "casino.db"

# --------------------------------------------------------
# BLACKJACK SAVE
# --------------------------------------------------------
def create_new_blackjack_entry():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Blackjack entry
    cursor.execute("""
               INSERT INTO Blackjack (wins, loses, draws) VALUES (0, 0, 0);
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