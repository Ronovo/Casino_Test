import sqlite3

DB_PATH = "casino.db"

# --------------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------------
def init_db():
    """Initialize database and create tables if needed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS Characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        credits INTEGER DEFAULT 0,
        current_bet INTEGER DEFAULT 0,
        difficulty TEXT,
        blackjack_id INTEGER DEFAULT 0,
        gtn_id INTEGER DEFAULT 0,
        FOREIGN KEY (blackjack_id) REFERENCES Blackjack (blackjack_id),
        FOREIGN KEY (gtn_id) REFERENCES GuessTheNumber (gtn_id)
    );
    
    CREATE TABLE IF NOT EXISTS Blackjack (
        blackjack_id INTEGER PRIMARY KEY AUTOINCREMENT,
        wins INTEGER DEFAULT 0,
        loses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS GuessTheNumber (
        gtn_id INTEGER PRIMARY KEY AUTOINCREMENT,
        wins INTEGER DEFAULT 0,
        loses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS Achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS CharacterAchievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        achievement_id INTEGER NOT NULL,
        date_unlocked TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (character_id) REFERENCES Characters (id),
        FOREIGN KEY (achievement_id) REFERENCES Achievements (id),
        UNIQUE (character_id, achievement_id)
    );
    """)

    conn.commit()
    conn.close()