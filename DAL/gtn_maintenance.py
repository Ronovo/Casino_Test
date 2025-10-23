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

def create_range_connection(chips):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Gtn_Bet_Range (white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))
    range_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return range_id

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

def create_even_odd_connection(chips):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Gtn_Bet_EvenOdd (white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))
    even_odd_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return even_odd_id

def create_lucky_connection(chips):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Gtn_Bet_Lucky (white, red, green, black, purple, orange)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        chips.get('White', 0),
        chips.get('Red', 0),
        chips.get('Green', 0),
        chips.get('Black', 0),
        chips.get('Purple', 0),
        chips.get('Orange', 0)
    ))
    lucky_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lucky_id

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

def has_even_odd_connection(gtn_id):
    even_odd_id = get_gtn_even_odd_id(gtn_id)
    return even_odd_id != 0

def has_range_connection(gtn_id):
    range_id = get_gtn_range_id(gtn_id)
    return range_id != 0

def has_lucky_connection(gtn_id):
    lucky_id = get_gtn_lucky_id(gtn_id)
    return lucky_id != 0

def get_gtn_pick_id(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pick_id FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    pick_id = cursor.fetchone()
    conn.close()
    return pick_id[0]

def get_gtn_range_id(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT range_id FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    range_id = cursor.fetchone()
    conn.close()
    return range_id[0]

def get_gtn_high_low_id(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT high_low_id FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    high_low_id = cursor.fetchone()
    conn.close()
    return high_low_id[0]

def get_gtn_even_odd_id(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT even_odd_id FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    even_odd_id = cursor.fetchone()
    conn.close()
    return even_odd_id[0]

def get_gtn_lucky_id(gtn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT lucky_id FROM GuessTheNumber WHERE gtn_id = ?",
                   (gtn_id,))
    lucky_id = cursor.fetchone()
    conn.close()
    return lucky_id[0]

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

def get_even_odd_chips(name):
    gtn_id = get_gtn_id(name)
    even_odd_id = get_gtn_even_odd_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Gtn_Bet_EvenOdd WHERE even_odd_id = ?",
                   (even_odd_id,))
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

def get_range_chips(name):
    gtn_id = get_gtn_id(name)
    range_id = get_gtn_range_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Gtn_Bet_Range WHERE range_id = ?",
                   (range_id,))
    selectedRangeInfo = cursor.fetchone()
    conn.close()
    return {
        "White": int(selectedRangeInfo[3]),  # white chip count
        "Red": int(selectedRangeInfo[4]),  # red chip count
        "Green": int(selectedRangeInfo[5]),  # green chip count
        "Black": int(selectedRangeInfo[6]),  # black chip count
        "Purple": int(selectedRangeInfo[7]),  # purple chip count
        "Orange": int(selectedRangeInfo[8])  # orange chip count
    }

def get_lucky_chips(name):
    gtn_id = get_gtn_id(name)
    lucky_id = get_gtn_lucky_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Gtn_Bet_Lucky WHERE lucky_id = ?",
                   (lucky_id,))
    selectedLuckyInfo = cursor.fetchone()
    conn.close()
    return {
        "White": int(selectedLuckyInfo[3]),  # white chip count
        "Red": int(selectedLuckyInfo[4]),  # red chip count
        "Green": int(selectedLuckyInfo[5]),  # green chip count
        "Black": int(selectedLuckyInfo[6]),  # black chip count
        "Purple": int(selectedLuckyInfo[7]),  # purple chip count
        "Orange": int(selectedLuckyInfo[8])  # orange chip count
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

def get_even_odd_info(even_odd_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Gtn_Bet_EvenOdd WHERE even_odd_id = ?", (even_odd_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    keys = [desc[0] for desc in cursor.description]
    return dict(zip(keys, row))

def get_range_info(range_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Gtn_Bet_Range WHERE range_id = ?", (range_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None
    keys = [desc[0] for desc in cursor.description]
    return dict(zip(keys, row))

def get_lucky_info(lucky_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Gtn_Bet_Lucky WHERE lucky_id = ?", (lucky_id,))
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

def get_even_odd_status(name):
    gtn_id = get_gtn_id(name)
    even_odd_id = get_gtn_even_odd_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT even_picked FROM Gtn_Bet_EvenOdd WHERE even_odd_id = ?",
                   (even_odd_id,))
    maxNumber = cursor.fetchone()
    conn.close()
    return maxNumber[0]

# --------------------------------------------------------
# GTN Update Methods
# --------------------------------------------------------
def updateStartingBet(name, betType, chips, numbersPicked):
    gtn_id = get_gtn_id(name)
    numberPicked = 0
    if len(numbersPicked) == 1:
        numberPicked = numbersPicked[0]
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
        case "Even/Odd":
            if not has_even_odd_connection(gtn_id):
                blankChips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
                # Create missing connections
                even_odd_id = create_even_odd_connection(blankChips)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                                    UPDATE GuessTheNumber
                                    SET even_odd_id = ?
                                    WHERE gtn_id = ?
                                """, (even_odd_id, gtn_id))
                conn.commit()
                conn.close()

            if numberPicked == 1:  # Even
                update_even_odd(name, 1, 0)
            elif numberPicked == 2:  # Odd
                update_even_odd(name, 0, 1)

            # Update Player Chips from Bet Chips
            evenOddPlayerChips = get_even_odd_chips(name)
            for x in evenOddPlayerChips:
                evenOddPlayerChips[x] += chips[x]
            update_even_odd_chips(name, evenOddPlayerChips)
        case "Range":
            if not has_range_connection(gtn_id):
                blankChips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
                # Create missing connections
                range_id = create_range_connection(blankChips)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                           UPDATE GuessTheNumber
                           SET range_id = ?
                           WHERE gtn_id = ?
                       """, (range_id, gtn_id))
                conn.commit()
                conn.close()

            # Update Player Chips from Bet Chips
            rangePlayerChips = get_range_chips(name)
            for x in rangePlayerChips:
                rangePlayerChips[x] += chips[x]
            rangeStart = numberPicked
            rangeEnd = rangeStart + 2
            update_range_chips(name, rangeStart, rangeEnd, rangePlayerChips)
        case "Lucky":
            if not has_lucky_connection(gtn_id):
                blankChips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
                # Create missing connections
                lucky_id = create_lucky_connection(blankChips)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                                   UPDATE GuessTheNumber
                                   SET lucky_id = ?
                                   WHERE gtn_id = ?
                               """, (lucky_id, gtn_id))
                conn.commit()
                conn.close()

            # Update Player Chips from Bet Chips
            luckyPlayerChips = get_lucky_chips(name)
            for x in luckyPlayerChips:
                luckyPlayerChips[x] += chips[x]
            number1 = numbersPicked[0]
            number2 = numbersPicked[1]
            update_lucky_chips(name, number1, number2, luckyPlayerChips)

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

def update_even_odd_chips(name, chips):
    gtn_id = get_gtn_id(name)
    even_odd_id = get_gtn_even_odd_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                  UPDATE Gtn_Bet_EvenOdd
                  SET white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE even_odd_id = ?
               """, (
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        even_odd_id,
    ))
    conn.commit()
    conn.close()

def update_range_chips(name, rangeStart, rangeEnd, chips):
    gtn_id = get_gtn_id(name)
    range_id = get_gtn_range_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
                  UPDATE Gtn_Bet_Range
                  SET range_start = ?, range_end = ?, white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE range_id = ?
               """, (
        rangeStart,
        rangeEnd,
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        range_id,
    ))
    conn.commit()
    conn.close()

def update_lucky_chips(name, number1, number2, chips):
    gtn_id = get_gtn_id(name)
    lucky_id = get_gtn_lucky_id(gtn_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
                  UPDATE Gtn_Bet_Lucky
                  SET lucky_number_1 = ?, lucky_number_2 = ?, white = ?, red = ?, green = ?, black = ?, orange = ?, purple = ?
                  WHERE lucky_id = ?
               """, (
        number1,
        number2,
        chips["White"],
        chips["Red"],
        chips["Green"],
        chips["Black"],
        chips["Orange"],
        chips["Purple"],
        lucky_id,
    ))
    conn.commit()
    conn.close()

def update_gtn_pick_new_game(pick_id):
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


def update_gtn_high_low_new_game(high_low_id):
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

def update_gtn_even_odd_new_game(even_odd_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                      UPDATE Gtn_Bet_EvenOdd
                      SET even_picked = ?, odd_picked = ?, white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
                      WHERE even_odd_id = ?
                   """, (
        0, 0, 0, 0, 0, 0, 0, 0,
        even_odd_id,))

    conn.commit()
    conn.close()

def update_gtn_range_new_game(range_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                      UPDATE Gtn_Bet_Range
                      SET range_start = ?, range_end = ?, white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
                      WHERE range_id = ?
                   """, (
        0, 0, 0, 0, 0, 0, 0, 0,
        range_id,))

    conn.commit()
    conn.close()

def update_gtn_lucky_new_game(lucky_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                      UPDATE Gtn_Bet_Lucky
                      SET lucky_number_1 = ?, lucky_number_2 = ?, white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
                      WHERE lucky_id = ?
                   """, (
        0, 0, 0, 0, 0, 0, 0, 0,
        lucky_id,))

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

def update_even_odd(name, even, odd):
    gtn_id = get_gtn_id(name)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                              UPDATE Gtn_Bet_EvenOdd
                              SET even_picked = ?, odd_picked = ?
                              WHERE even_odd_id = ?
                           """, (
        even, odd, gtn_id,))
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
    else:
        return base_modifier