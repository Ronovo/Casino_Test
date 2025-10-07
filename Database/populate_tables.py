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