import sqlite3

DB_PATH = "casino.db"

# --------------------------------------------------------
# ACHIEVEMENT SYSTEM
# --------------------------------------------------------
def insert_achievement(character_name, achievement_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Characters WHERE name = ?", (character_name,))
    char = cursor.fetchone()
    if not char:
        print("Character not found.")
        conn.close()
        return
    char_id = char[0]

    cursor.execute("SELECT id, display_name, description FROM Achievements WHERE name = ?", (achievement_name,))
    achievement = cursor.fetchone()
    if not achievement:
        print("Achievement not found.")
        conn.close()
        return

    try:
        cursor.execute("""
            INSERT INTO CharacterAchievements (character_id, achievement_id)
            VALUES (?, ?)
        """, (char_id, achievement[0]))
        conn.commit()
        print("**************************")
        print("New Achievement Unlocked!")
        print(f"{achievement[1]} : {achievement[2]}")
        print("**************************")
    except sqlite3.IntegrityError:
        #Achievement already unlocked
        pass
    finally:
        conn.close()