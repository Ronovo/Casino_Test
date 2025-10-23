import sqlite3
from DAL import character_maintenance as cm, money_maintenance as mm

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
def update_ante_chip(name, chips):
    poker_id = get_poker_id(name)
    anteid = get_poker_ante_id(poker_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                  UPDATE Poker_Bet_Ante
                  SET white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE ante_bet_id = ?
               """, (
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        anteid,
    ))
    conn.commit()
    conn.close()

def update_blind_chips(name, chips):
    poker_id = get_poker_id(name)
    blindid = get_poker_blind_id(poker_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                  UPDATE Poker_Bet_Blind
                  SET white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE blind_bet_id = ?
               """, (
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        blindid,
    ))
    conn.commit()
    conn.close()

def updateAnteAndBlindStart(name, blindChips, anteChips):
    poker_id = get_poker_id(name)

    # Check if we need to create connections (if any are missing)
    needs_connection_update = (not has_ante_connection(poker_id) or
                             not has_blind_connection(poker_id) or
                             not has_trips_connection(poker_id) or
                             not has_pairs_connection(poker_id))

    if needs_connection_update:
        # Create missing connections
        if not has_ante_connection(poker_id):
            ante_id = create_ante_connection(anteChips)
        else:
            ante_id = get_poker_ante_id(poker_id)

        if not has_blind_connection(poker_id):
            blind_id = create_blind_connection(blindChips)
        else:
            blind_id = get_poker_blind_id(poker_id)

        if not has_trips_connection(poker_id):
            trips_id = create_trips_connections(name)
        else:
            trips_id = get_poker_trips_id(poker_id)

        if not has_pairs_connection(poker_id):
            pairs_id = create_pairs_connections(name)
        else:
            pairs_id = get_poker_pairs_id(poker_id)

        # Update Poker record with new connection IDs
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Poker
            SET ante_bet_id = ?, blind_bet_id = ?, trips_bet_id = ?, pairs_bet_id = ?
            WHERE poker_id = ?
        """, (ante_id, blind_id, trips_id, pairs_id, poker_id))
        conn.commit()
        conn.close()
    else:
        # Just get existing IDs for updating
        ante_id = get_poker_ante_id(poker_id)
        blind_id = get_poker_blind_id(poker_id)

    # Update ante and blind chip values (always do this)
    update_ante_chip(name, anteChips)
    update_blind_chips(name, blindChips)

def update_trips_chips(name, chips):
    poker_id = get_poker_id(name)
    tripsid = get_poker_trips_id(poker_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                  UPDATE Poker_Bet_Trips
                  SET white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE trips_bet_id = ?
               """, (
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        tripsid,
    ))
    conn.commit()
    conn.close()

def update_pairs_chips(name, chips):
    poker_id = get_poker_id(name)
    pairsid = get_poker_pairs_id(poker_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                  UPDATE Poker_Bet_Pairs
                  SET white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE pairs_bet_id = ?
               """, (
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        pairsid,
    ))
    conn.commit()
    conn.close()

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

#Select Chips Methods
def get_ante_chips(name):
    poker_id = get_poker_id(name)
    anteid = get_poker_ante_id(poker_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Poker_Bet_Ante WHERE ante_bet_id = ?",
                   (anteid,))
    anteChips = cursor.fetchone()
    conn.close()
    return {
        "White": int(anteChips[1]),  # white chip count
        "Red": int(anteChips[2]),  # red chip count
        "Green": int(anteChips[3]),  # green chip count
        "Black": int(anteChips[4]),  # black chip count
        "Purple": int(anteChips[5]),  # purple chip count
        "Orange": int(anteChips[6])  # orange chip count
    }


def get_blind_chips(name):
    poker_id = get_poker_id(name)
    blindid = get_poker_blind_id(poker_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Poker_Bet_Blind WHERE blind_bet_id = ?",
                   (blindid,))
    blindChips = cursor.fetchone()
    conn.close()
    return {
        "White": int(blindChips[1]),  # white chip count
        "Red": int(blindChips[2]),  # red chip count
        "Green": int(blindChips[3]),  # green chip count
        "Black": int(blindChips[4]),  # black chip count
        "Purple": int(blindChips[5]),  # purple chip count
        "Orange": int(blindChips[6])  # orange chip count
    }


def get_trips_chips(name):
    poker_id = get_poker_id(name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT trips_bet_id FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    result = cursor.fetchone()
    tripsid = result[0]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Poker_Bet_Trips WHERE trips_bet_id = ?",
                   (tripsid,))
    tripsChips = cursor.fetchone()
    conn.commit()
    conn.close()
    return {
        "White": int(tripsChips[1]),  # white chip count
        "Red": int(tripsChips[2]),  # red chip count
        "Green": int(tripsChips[3]),  # green chip count
        "Black": int(tripsChips[4]),  # black chip count
        "Purple": int(tripsChips[5]),  # purple chip count
        "Orange": int(tripsChips[6])  # orange chip count
    }

def get_pairs_chips(name):
    poker_id = get_poker_id(name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pairs_bet_id FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    result = cursor.fetchone()
    pairsid = result[0]

    if pairsid == 0:
        pairsid = create_pairs_connections(name)

    cursor.execute("SELECT * FROM Poker_Bet_Pairs WHERE pairs_bet_id = ?",
                   (pairsid,))
    pairsChips = cursor.fetchone()

    return {
        "White": int(pairsChips[1]),  # white chip count
        "Red": int(pairsChips[2]),  # red chip count
        "Green": int(pairsChips[3]),  # green chip count
        "Black": int(pairsChips[4]),  # black chip count
        "Purple": int(pairsChips[5]),  # purple chip count
        "Orange": int(pairsChips[6])  # orange chip count
    }

def get_poker_ante_id(poker_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT ante_bet_id FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    anteid = cursor.fetchone()
    conn.close()
    return anteid[0]

def has_ante_connection(poker_id):
    ante_id = get_poker_ante_id(poker_id)
    return ante_id != 0

def has_blind_connection(poker_id):
    blind_id = get_poker_blind_id(poker_id)
    return blind_id != 0

def has_trips_connection(poker_id):
    trips_id = get_poker_trips_id(poker_id)
    return trips_id != 0

def has_pairs_connection(poker_id):
    pairs_id = get_poker_pairs_id(poker_id)
    return pairs_id != 0

def get_poker_blind_id(poker_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT blind_bet_id FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    blindid = cursor.fetchone()
    conn.close()
    return blindid[0]

def get_poker_trips_id(poker_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT trips_bet_id FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    tripsid = cursor.fetchone()
    conn.close()
    return tripsid[0]

def get_poker_pairs_id(poker_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pairs_bet_id FROM Poker WHERE poker_id = ?",
                   (poker_id,))
    pairsid = cursor.fetchone()
    conn.close()
    return pairsid[0]

def get_total_bet(name):
    anteChips = get_ante_chips(name)
    anteTotal = mm.get_chips_total(anteChips)
    blindChips = get_blind_chips(name)
    blindTotal = mm.get_chips_total(blindChips)
    tripsChips = get_trips_chips(name)
    tripsTotal = mm.get_chips_total(tripsChips)
    pairsChips = get_pairs_chips(name)
    pairsTotal = mm.get_chips_total(pairsChips)
    betTotal = anteTotal["Total"] + blindTotal["Total"] + tripsTotal["Total"] + pairsTotal["Total"]
    return betTotal

def create_ante_connection(chips):
    """Create a new ante bet entry with specified chip values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Poker_Bet_Ante (white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))
    ante_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ante_id

def create_blind_connection(chips):
    """Create a new blind bet entry with specified chip values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Poker_Bet_Blind (white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))
    blind_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return blind_id

def create_trips_connections(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Poker_Bet_Trips (white, red, green, black, purple, orange) VALUES (0, 0, 0, 0, 0, 0) ;")
    tripsid = cursor.lastrowid

    conn.commit()
    conn.close()
    return tripsid


def create_pairs_connections(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Poker_Bet_Pairs (white, red, green, black, purple, orange) VALUES (0, 0, 0, 0, 0, 0) ;")
    pairsid = cursor.lastrowid

    conn.commit()
    conn.close()
    return pairsid