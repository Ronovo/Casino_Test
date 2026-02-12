import sqlite3
from DAL import character_maintenance as cm, money_maintenance as mm

DB_PATH = "casino.db"

# --------------------------------------------------------
# BACCARAT CREATE LINK
# --------------------------------------------------------
def create_new_baccarat_entry():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Baccarat entry
    cursor.execute("""
               INSERT INTO baccarat DEFAULT VALUES;
            """)
    baccarat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return baccarat_id

def update_character_with_baccarat(baccarat_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE Characters
            SET baccarat_id = ?
            WHERE name = ?
        """, (
        baccarat_id,
        name
    ))

    conn.commit()
    conn.close()

def create_baccarat_connection(characterData):
    baccarat_id = create_new_baccarat_entry()
    update_character_with_baccarat(baccarat_id, characterData["name"])

    return cm.load_character_by_name(characterData["name"])


def update_bet_type(name, betType):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    baccarat_id = get_baccarat_id(name)
    player_bet = 0
    banker_bet = 0
    tie_bet = 0
    match betType:
        case "Player":
            player_bet = 1
        case "Banker":
            banker_bet = 1
        case "Tie":
            tie_bet = 1
    cursor.execute("""
            UPDATE Baccarat
            SET player_bet = ?, banker_bet = ?, tie_bet = ?
            WHERE baccarat_id = ?
        """, (
        player_bet,
        banker_bet,
        tie_bet,
        baccarat_id
    ))

    conn.commit()
    conn.close()

def get_baccarat_id(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT baccarat_id FROM Characters WHERE name = ?",
                   (name,))
    id = cursor.fetchone()
    return id[0]

def payOut(characterData,modifier):
    # Current Bet in Chips
    currentBet = getCurrentBaccaratBet(characterData['name'])
    totalWinnings = payoutHelper(modifier, currentBet, characterData['name'])
    print("You won " + str(totalWinnings) + " credits!")
    mm.checkCreditsAchievements(characterData['name'])


def payoutHelper(modifier, currentBet, characterName):
    blackjackChips = {
        "White": currentBet["White"] * modifier,
        "Red": currentBet["Red"] * modifier,
        "Green": currentBet["Green"] * modifier,
        "Black": currentBet["Black"] * modifier,
        "Purple": currentBet["Purple"] * modifier,
        "Orange": currentBet["Orange"] * modifier
    }
    # Add blackjack chips to player's inventory
    cm.update_player_chips_add(characterName, blackjackChips)
    # Get Total to return
    totalWinningChips = mm.get_chips_total(blackjackChips)
    return totalWinningChips["Total"]

def getCurrentBaccaratBet(name):
    baccarat_id = get_baccarat_id(name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current bet and chip values
    cursor.execute("""
                  SELECT white, red, green, black, purple, orange
                  FROM Baccarat
                  WHERE baccarat_id = ?
               """, (
        baccarat_id,
    ))
    bet = cursor.fetchone()
    conn.commit()
    conn.close()

    if bet:
        return {
            "White": int(bet[0]),    # white chip count
            "Red": int(bet[1]),      # red chip count
            "Green": int(bet[2]),    # green chip count
            "Black": int(bet[3]),    # black chip count
            "Purple": int(bet[4]),   # purple chip count
            "Orange": int(bet[5])    # orange chip count
        }

def getCurrentBaccaratBetType(name):
    baccarat_id = get_baccarat_id(name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current bet and chip values
    cursor.execute("""
                  SELECT player_bet, banker_bet, tie_bet
                  FROM Baccarat
                  WHERE baccarat_id = ?
               """, (
        baccarat_id,
    ))
    bet = cursor.fetchone()
    conn.commit()
    conn.close()

    if bet:
        return {
            "Player Bet": int(bet[0]),
            "Banker Bet": int(bet[1]),
            "Tie Bet": int(bet[2])
        }