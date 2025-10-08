import sqlite3
import json
import datetime

DB_PATH = "../casino.db"

def export_character_to_json(character_name, export_path):
    """Export a character and all associated data to a JSON file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get character data
        cursor.execute("""
            SELECT id, name, credits, difficulty, blackjack_id, poker_id
            FROM Characters WHERE name = ?
        """, (character_name,))

        character_row = cursor.fetchone()
        if not character_row:
            conn.close()
            raise ValueError(f"Character '{character_name}' not found in database")

        char_id, name, credits, difficulty, blackjack_id, poker_id = character_row

        # Get blackjack data if exists
        blackjack_data = None
        if blackjack_id and blackjack_id > 0:
            cursor.execute("""
                SELECT current_bet, wins, losses, draws
                FROM Blackjack WHERE blackjack_id = ?
            """, (blackjack_id,))
            blackjack_row = cursor.fetchone()
            if blackjack_row:
                blackjack_data = {
                    "current_bet": blackjack_row[0],
                    "wins": blackjack_row[1],
                    "losses": blackjack_row[2],
                    "draws": blackjack_row[3]
                }

        # Get poker data if exists
        poker_data = None
        if poker_id and poker_id > 0:
            cursor.execute("""
                SELECT ante, trips, pairs, wins, losses, draws
                FROM Poker WHERE poker_id = ?
            """, (poker_id,))
            poker_row = cursor.fetchone()
            if poker_row:
                poker_data = {
                    "ante": poker_row[0],
                    "trips": poker_row[1],
                    "pairs": poker_row[2],
                    "wins": poker_row[3],
                    "losses": poker_row[4],
                    "draws": poker_row[5]
                }

        # Get character achievements
        cursor.execute("""
            SELECT A.name, A.category, A.display_name, A.description, CA.date_unlocked
            FROM CharacterAchievements CA
            JOIN Achievements A ON CA.achievement_id = A.id
            WHERE CA.character_id = ?
            ORDER BY CA.date_unlocked
        """, (char_id,))

        achievements = []
        for row in cursor.fetchall():
            achievements.append({
                "achievement_name": row[0],
                "category": row[1],
                "display_name": row[2],
                "description": row[3],
                "date_unlocked": row[4]
            })

        # Structure the export data
        export_data = {
            "character": {
                "name": name,
                "credits": credits,
                "difficulty": difficulty
            },
            "blackjack": blackjack_data,
            "poker": poker_data,
            "achievements": achievements,
            "export_info": {
                "exported_at": datetime.datetime.now().isoformat(),
                "version": "1.0"
            }
        }

        # Write to JSON file
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"Character '{character_name}' exported to {export_path}")

    except Exception as e:
        print(f"Error exporting character: {e}")
        raise
    finally:
        conn.close()

def import_character_from_json(import_path, character_name=None):
    """Import a character and all associated data from a JSON file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Read the JSON file
        with open(import_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)

        # Extract character data
        char_data = import_data.get("character")
        if not char_data:
            raise ValueError("Invalid JSON file: missing character data")

        # Use provided name or get from file
        name = character_name if character_name else char_data["name"]

        # Check if character already exists
        cursor.execute("SELECT id FROM Characters WHERE name = ?", (name,))
        existing_char = cursor.fetchone()

        # Insert or update character
        if existing_char:
            # Update existing character
            char_id = existing_char[0]
            cursor.execute("""
                UPDATE Characters
                SET credits = ?, difficulty = ?, name = ?
                WHERE id = ?
            """, (char_data["credits"], char_data["difficulty"], name, char_id))
            print(f"Updated existing character '{name}'")
        else:
            # Insert new character (without blackjack_id and poker_id for now)
            cursor.execute("""
                INSERT INTO Characters (name, credits, difficulty)
                VALUES (?, ?, ?)
            """, (name, char_data["credits"], char_data["difficulty"]))
            char_id = cursor.lastrowid
            print(f"Created new character '{name}'")

        # Handle blackjack data
        blackjack_data = import_data.get("blackjack")
        if blackjack_data:
            if existing_char and char_data.get("blackjack_id"):
                # Update existing blackjack record
                blackjack_id = char_data["blackjack_id"]
                cursor.execute("""
                    UPDATE Blackjack
                    SET current_bet = ?, wins = ?, losses = ?, draws = ?
                    WHERE blackjack_id = ?
                """, (blackjack_data["current_bet"], blackjack_data["wins"],
                      blackjack_data["losses"], blackjack_data["draws"], blackjack_id))
            else:
                # Insert new blackjack record
                cursor.execute("""
                    INSERT INTO Blackjack (current_bet, wins, losses, draws)
                    VALUES (?, ?, ?, ?)
                """, (blackjack_data["current_bet"], blackjack_data["wins"],
                      blackjack_data["losses"], blackjack_data["draws"]))
                blackjack_id = cursor.lastrowid

                # Update character with blackjack_id
                cursor.execute("""
                    UPDATE Characters SET blackjack_id = ? WHERE id = ?
                """, (blackjack_id, char_id))

        # Handle poker data
        poker_data = import_data.get("poker")
        if poker_data:
            if existing_char and char_data.get("poker_id"):
                # Update existing poker record
                poker_id = char_data["poker_id"]
                cursor.execute("""
                    UPDATE Poker
                    SET ante = ?, trips = ?, pairs = ?, wins = ?, losses = ?, draws = ?
                    WHERE poker_id = ?
                """, (poker_data["ante"], poker_data["trips"], poker_data["pairs"],
                      poker_data["wins"], poker_data["losses"], poker_data["draws"], poker_id))
            else:
                # Insert new poker record
                cursor.execute("""
                    INSERT INTO Poker (ante, trips, pairs, wins, losses, draws)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (poker_data["ante"], poker_data["trips"], poker_data["pairs"],
                      poker_data["wins"], poker_data["losses"], poker_data["draws"]))
                poker_id = cursor.lastrowid

                # Update character with poker_id
                cursor.execute("""
                    UPDATE Characters SET poker_id = ? WHERE id = ?
                """, (poker_id, char_id))

        # Handle achievements
        achievements = import_data.get("achievements", [])
        for achievement in achievements:
            # Get achievement ID by name
            cursor.execute("""
                SELECT id FROM Achievements WHERE name = ?
            """, (achievement["achievement_name"],))

            ach_row = cursor.fetchone()
            if ach_row:
                achievement_id = ach_row[0]

                # Check if character already has this achievement
                cursor.execute("""
                    SELECT id FROM CharacterAchievements
                    WHERE character_id = ? AND achievement_id = ?
                """, (char_id, achievement_id))

                if not cursor.fetchone():
                    # Insert new character achievement
                    cursor.execute("""
                        INSERT INTO CharacterAchievements (character_id, achievement_id, date_unlocked)
                        VALUES (?, ?, ?)
                    """, (char_id, achievement_id, achievement.get("date_unlocked", datetime.datetime.now().isoformat())))

        conn.commit()
        print(f"Character '{name}' imported successfully")

    except FileNotFoundError:
        print(f"Error: File '{import_path}' not found")
        raise
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file '{import_path}'")
        raise
    except Exception as e:
        conn.rollback()
        print(f"Error importing character: {e}")
        raise
    finally:
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