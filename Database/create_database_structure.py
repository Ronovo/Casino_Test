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
    /*
    Top Level Tables (Character and Games)
    */
    CREATE TABLE IF NOT EXISTS Characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        credits INTEGER DEFAULT 0,
        difficulty TEXT,
        blackjack_id INTEGER DEFAULT 0,
        poker_id INTEGER DEFAULT 0,
        gtn_id INTEGER DEFAULT 0,
        baccarat_id INTEGER DEFAULT 0,
        FOREIGN KEY (blackjack_id) REFERENCES Blackjack (blackjack_id),
        FOREIGN KEY (poker_id) REFERENCES Poker (poker_id),
        FOREIGN KEY (gtn_id) REFERENCES GuessTheNumber (gtn_id),
        FOREIGN KEY (baccarat_id) REFERENCES Baccarat (baccarat_id)
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
    
    CREATE TABLE IF NOT EXISTS GuessTheNumber (
        gtn_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pick_id INTEGER DEFAULT 0,
        high_low_id INTEGER DEFAULT 0,
        even_odd_id DEFAULT 0,
        range_id DEFAULT 0,
        lucky_id DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        number_max_pick INTEGER DEFAULT 0,
        dealer_number INTEGER DEFAULT 0,
        FOREIGN KEY (pick_id) REFERENCES Gtn_Bet_Pick (pick_id),
        FOREIGN KEY (high_low_id) REFERENCES Gtn_Bet_HighLow (high_low_id),
        FOREIGN KEY (even_odd_id) REFERENCES Gtn_Bet_EvenOdd (even_odd_id),
        FOREIGN KEY (range_id) REFERENCES Gtn_Bet_Range (range_id)
        FOREIGN KEY (lucky_id) REFERENCES Gtn_Bet_Lucky (lucky_id)
    );
    
    CREATE TABLE IF NOT EXISTS Baccarat (
        baccarat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_bet INTEGER DEFAULT 0,
        banker_bet INTEGER DEFAULT 0,
        tie_bet INTEGER DEFAULT 0, 
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0,
        baccarat_bonus_bet_id INTEGER DEFAULT 0,
        FOREIGN KEY (baccarat_bonus_bet_id) REFERENCES Baccarat_Bonus_Bet (baccarat_bonus_bet_id)
    );
    
    CREATE TABLE IF NOT EXISTS Baccarat_Bonus_Bet (
        baccarat_bonus_bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dragon7 INTEGER DEFAULT 0,
        panda8 INTEGER DEFAULT 0,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
    /*
    Poker Bet Tables
    */
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
    
    /*
    Guess The Number Bet Tables
    */
    CREATE TABLE IF NOT EXISTS Gtn_Bet_Pick (
        pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
        number_picked INTEGER DEFAULT 0,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS Gtn_Bet_HighLow (
        high_low_id INTEGER PRIMARY KEY AUTOINCREMENT,
        high_picked INTEGER DEFAULT 0,
        low_picked INTEGER DEFAULT 0,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS Gtn_Bet_EvenOdd (
        even_odd_id INTEGER PRIMARY KEY AUTOINCREMENT,
        even_picked INTEGER DEFAULT 0,
        odd_picked INTEGER DEFAULT 0,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS Gtn_Bet_Range (
        range_id INTEGER PRIMARY KEY AUTOINCREMENT,
        range_start INTEGER DEFAULT 0,
        range_end INTEGER DEFAULT 0,
        white INTEGER DEFAULT 0,
        red INTEGER DEFAULT 0,
        green INTEGER DEFAULT 0,
        black INTEGER DEFAULT 0,
        purple INTEGER DEFAULT 0,
        orange INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS Gtn_Bet_Lucky (
        lucky_id INTEGER PRIMARY KEY AUTOINCREMENT,
        lucky_number_1 INTEGER DEFAULT 0,
        lucky_number_2 INTEGER DEFAULT 0,
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
    
    /*
    Json Loaded Tables (Achievements, Chips, Pay Tables)
    */
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
    
    CREATE TABLE IF NOT EXISTS GtnModifiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        odds_easy TEXT NOT NULL,
        odds_medium TEXT NOT NULL,
        odds_hard TEXT NOT NULL,
        odds_impossible TEXT NOT NULL,
        base_modifier INTEGER NOT NULL
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