import sqlite3
from DAL import character_maintenance as cm

DB_PATH = "casino.db"

# --------------------------------------------------------
# Poker CREATE LINK
# --------------------------------------------------------
def create_new_gtn_entry():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Poker entry
    cursor.execute("""
               INSERT INTO GuessTheNumber (wins, losses, draws) VALUES (0, 0, 0);
            """)
    gtn_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return gtn_id

def update_character_with_gtn(gtn_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE Characters
            SET gtn_id = ?
            WHERE name = ?
        """, (
        gtn_id,
        name
    ))

    conn.commit()
    conn.close()

def create_gtn_connection(characterData):
    gtn_id = create_new_gtn_entry()
    update_character_with_gtn(gtn_id, characterData["name"])

def create_pick_connection(chips):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Gtn_Bet_Pick (white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))
    pick_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pick_id

def create_high_low_connection(chips):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Gtn_Bet_HighLow (white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))
    high_low_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return high_low_id

# --------------------------------------------------------
# GTN Select Methods
# --------------------------------------------------------
def get_gtn_id(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT gtn_id FROM Characters WHERE name = ?",
                   (name,))
    id = cursor.fetchone()
    return id[0]

def has_pick_connection(gtn_id):
    pick_id = get_gtn_pick_id(gtn_id)
    return pick_id != 0

def has_high_low_connection(gtn_id):
    high_low_id = get_gtn_high_low_id(gtn_id)
    return high_low_id != 0

def get_gtn_pick_id(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pick_id FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    pick_id = cursor.fetchone()
    conn.close()
    return pick_id[0]

def get_gtn_high_low_id(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT high_low_id FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    high_low_id = cursor.fetchone()
    conn.close()
    return high_low_id[0]

def get_pick_chips(name):
    gtn_id = get_gtn_id(name)
    pick_id = get_gtn_pick_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Gtn_Bet_Pick WHERE pick_id = ?",
                   (pick_id,))
    pickChips = cursor.fetchone()
    conn.close()
    return {
        "White": int(pickChips[2]),  # white chip count
        "Red": int(pickChips[3]),  # red chip count
        "Green": int(pickChips[4]),  # green chip count
        "Black": int(pickChips[5]),  # black chip count
        "Purple": int(pickChips[6]),  # purple chip count
        "Orange": int(pickChips[7])  # orange chip count
    }

def get_high_low_chips(name):
    gtn_id = get_gtn_id(name)
    high_low_id = get_gtn_high_low_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Gtn_Bet_HighLow WHERE high_low_id = ?",
                   (high_low_id,))
    highLowChips = cursor.fetchone()
    conn.close()
    return {
        "White": int(highLowChips[3]),  # white chip count
        "Red": int(highLowChips[4]),  # red chip count
        "Green": int(highLowChips[5]),  # green chip count
        "Black": int(highLowChips[6]),  # black chip count
        "Purple": int(highLowChips[7]),  # purple chip count
        "Orange": int(highLowChips[8])  # orange chip count
    }

def get_pick_info(pick_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Gtn_Bet_Pick WHERE pick_id = ?", (pick_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    keys = [desc[0] for desc in cursor.description]
    return dict(zip(keys, row))

def get_high_low_info(high_low_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Gtn_Bet_HighLow WHERE high_low_id = ?", (high_low_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    keys = [desc[0] for desc in cursor.description]
    return dict(zip(keys, row))

def get_max_number(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT number_max_pick FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    maxNumber = cursor.fetchone()
    conn.close()
    return maxNumber[0]

def get_high_low_status(name):
    gtn_id = get_gtn_id(name)
    high_low_id = get_gtn_high_low_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT high_picked FROM Gtn_Bet_HighLow WHERE high_low_id = ?",
                   (high_low_id,))
    maxNumber = cursor.fetchone()
    conn.close()
    return maxNumber[0]

# --------------------------------------------------------
# GTN Update Methods
# --------------------------------------------------------
def updateStartingBet(name, betType, chips, numberPicked):
    gtn_id = get_gtn_id(name)

    match betType:
        case "Pick":
            if not has_pick_connection(gtn_id):
                blankChips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
                # Create missing connections
                pick_id = create_pick_connection(blankChips)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE GuessTheNumber
                    SET pick_id = ?
                    WHERE gtn_id = ?
                """, (pick_id, gtn_id))
                conn.commit()
                conn.close()

            # Update Player Chips from Bet Chips
            pickPlayerChips = get_pick_chips(name)
            for x in pickPlayerChips:
                pickPlayerChips[x] += chips[x]
            update_pick_chips(name, numberPicked, pickPlayerChips)
        case "High/Low":
            if not has_high_low_connection(gtn_id):
                blankChips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
                # Create missing connections
                high_low_id = create_high_low_connection(blankChips)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                            UPDATE GuessTheNumber
                            SET high_low_id = ?
                            WHERE gtn_id = ?
                        """, (high_low_id, gtn_id))
                conn.commit()
                conn.close()

            if numberPicked == 1: #Low
                update_low_high(name, 1, 0)
            elif numberPicked == 2: #High
                update_low_high(name, 0, 1)

            # Update Player Chips from Bet Chips
            highLowPlayerChips = get_high_low_chips(name)
            for x in highLowPlayerChips:
                highLowPlayerChips[x] += chips[x]
            update_low_high_chips(name, highLowPlayerChips)

def update_number_max_pick(name, maxNumber):
    gtn_id = get_gtn_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                          UPDATE GuessTheNumber
                          SET number_max_pick = ?
                          WHERE gtn_id = ?
                       """, (
            maxNumber, gtn_id,))
    conn.commit()
    conn.close()

def update_dealer_number(name, dealerNumber):
    gtn_id = get_gtn_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                              UPDATE GuessTheNumber
                              SET dealer_number = ?
                              WHERE gtn_id = ?
                           """, (
        dealerNumber, gtn_id,))
    conn.commit()
    conn.close()

def update_pick_chips(name, numberPicked, chips):
    gtn_id = get_gtn_id(name)
    pick_id = get_gtn_pick_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                  UPDATE Gtn_Bet_Pick
                  SET number_picked = ?, white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE pick_id = ?
               """, (
        numberPicked,
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        pick_id,
    ))
    conn.commit()
    conn.close()

def update_low_high_chips(name, chips):
    gtn_id = get_gtn_id(name)
    high_low_id = get_gtn_high_low_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                  UPDATE Gtn_Bet_HighLow
                  SET white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE high_low_id = ?
               """, (
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        high_low_id,
    ))
    conn.commit()
    conn.close()

def update_gtn_pick_new_game(gtn_id, pick_id):
    update_gtn_new_game(gtn_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                      UPDATE Gtn_Bet_Pick
                      SET number_picked = ?, white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
                      WHERE pick_id = ?
                   """, (
        0, 0, 0, 0, 0, 0, 0,
        pick_id,))

    conn.commit()
    conn.close()


def update_gtn_high_low_new_game(gtn_id, high_low_id):
    update_gtn_new_game(gtn_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                      UPDATE Gtn_Bet_HighLow
                      SET high_picked = ?, low_picked = ?, white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
                      WHERE high_low_id = ?
                   """, (
        0, 0, 0, 0, 0, 0, 0, 0,
        high_low_id,))

    conn.commit()
    conn.close()

def update_gtn_new_game(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                      UPDATE GuessTheNumber
                      SET dealer_number = ?, number_max_pick = ?
                      WHERE gtn_id = ?
                    """, (
        0, 0,
        gtn_id,))
    conn.commit()
    conn.close()

def update_low_high(name, low, high):
    gtn_id = get_gtn_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                              UPDATE Gtn_Bet_HighLow
                              SET high_picked = ?, low_picked = ?
                              WHERE high_low_id = ?
                           """, (
        high, low, gtn_id,))
    conn.commit()
    conn.close()
# --------------------------------------------------------
# GTN Get Paytable Methods
# --------------------------------------------------------
def get_base_modifier_by_name(typeName):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT base_modifier FROM GtnModifiers WHERE name = ?",
                   (typeName,))
    modifier = cursor.fetchone()
    return modifier[0]

def get_base_modifier_by_difficulty(maxNumber, base_modifier):
    if maxNumber == 100:
        return base_modifier * 10
    elif maxNumber == 1000:
        return base_modifier * 100
    elif maxNumber == 1000000000:
        return base_modifier * 100000000