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
        difficulty TEXT,
        blackjack_id INTEGER DEFAULT 0,
        poker_id INTEGER DEFAULT 0,
        FOREIGN KEY (blackjack_id) REFERENCES Blackjack (blackjack_id),
        FOREIGN KEY (poker_id) REFERENCES GuessTheNumber (poker_id)
    );
    
    CREATE TABLE IF NOT EXISTS Blackjack (
        blackjack_id INTEGER PRIMARY KEY AUTOINCREMENT,
        current_bet INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS Poker (
        poker_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ante_bet_id INTEGER DEFAULT 0,
        blind_bet_id INTEGER DEFAULT 0,
        trips_bet_id DEFAULT 0,
        pairs_bet_id DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        FOREIGN KEY (ante_bet_id) REFERENCES Poker_Bet_Ante (ante_bet_id),
        FOREIGN KEY (blind_bet_id) REFERENCES Poker_Bet_Blind (blind_bet_id),
        FOREIGN KEY (trips_bet_id) REFERENCES Poker_Bet_Trips (trips_bet_id),
        FOREIGN KEY (pairs_bet_id) REFERENCES Poker_Bet_Pairs (pairs_bet_id)
    );
    
    CREATE TABLE IF NOT EXISTS Poker_Bet_Ante (
        ante_bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
        CREATE TABLE IF NOT EXISTS Poker_Bet_Blind (
        blind_bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
        CREATE TABLE IF NOT EXISTS Poker_Bet_Trips (
        trips_bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
        CREATE TABLE IF NOT EXISTS Poker_Bet_Pairs (
        pairs_bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS Achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        display_name TEXT NOT NULL,
        description TEXT
    );
    
    CREATE TABLE IF NOT EXISTS PokerBlinds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        score_value INT NOT NULL,
        odds TEXT NOT NULL,
        modifier DOUBLE NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS PokerTrips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        score_value INT NOT NULL,
        odds TEXT NOT NULL,
        modifier DOUBLE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS PokerPairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        score_value TEXT NOT NULL,
        odds TEXT NOT NULL,
        modifier DOUBLE NOT NULL
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
    
    CREATE TABLE IF NOT EXISTS Chips (
        chip_id INTEGER PRIMARY KEY AUTOINCREMENT,
        color TEXT UNIQUE NOT NULL,
        credit_value INTEGER NOT NULL,
        easy_amount INTEGER NOT NULL,
        medium_amount INTEGER NOT NULL,
        hard_amount INTEGER NOT NULL,
        vhard_amount INTEGER NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS PlayerChips (
        p_chip_id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        white INTEGER NOT NULL DEFAULT 0,
        red INTEGER NOT NULL DEFAULT 0,
        green INTEGER NOT NULL DEFAULT 0,
        black INTEGER NOT NULL DEFAULT 0,
        purple INTEGER NOT NULL DEFAULT 0,
        orange INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (character_id) REFERENCES Characters (id)
    );
    
    """)

    conn.commit()
    conn.close()