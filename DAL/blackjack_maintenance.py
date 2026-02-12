import sqlite3
from DAL import character_maintenance as cm, money_maintenance as mm

DB_PATH = "casino.db"

# --------------------------------------------------------
# BLACKJACK CREATE LINK
# --------------------------------------------------------
def create_new_blackjack_entry():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Blackjack entry
    cursor.execute("""
               INSERT INTO Blackjack (current_bet,wins, losses, draws) VALUES (0, 0, 0, 0);
            """)
    blackjack_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return blackjack_id

def update_character_with_blackjack(blackjack_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE Characters
            SET blackjack_id = ?
            WHERE name = ?
        """, (
        blackjack_id,
        name
    ))

    conn.commit()
    conn.close()

def create_blackjack_connection(characterData):
    blackjack_id = create_new_blackjack_entry()
    update_character_with_blackjack(blackjack_id, characterData["name"])

    return cm.load_character_by_name(characterData["name"])

# --------------------------------------------------------
# BLACKJACK GET METHODS
# --------------------------------------------------------
def get_blackjack_id(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT blackjack_id FROM Characters WHERE name = ?",
                   (name,))
    id = cursor.fetchone()
    return id[0]

def get_blackjack_wins(blackjack_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT wins FROM Blackjack WHERE blackjack_id = ?",
                   (blackjack_id,))
    wins = cursor.fetchone()
    return wins[0]

def get_blackjack_losses(blackjack_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT losses FROM Blackjack WHERE blackjack_id = ?",
                   (blackjack_id,))
    losses = cursor.fetchone()
    return losses[0]

def get_blackjack_draws(blackjack_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT draws FROM Blackjack WHERE blackjack_id = ?",
                   (blackjack_id,))
    draws = cursor.fetchone()
    return draws[0]

# --------------------------------------------------------
# BLACKJACK UPDATE METHODS
# --------------------------------------------------------
def update_blackjack_wins(name):
    blackjack_id = get_blackjack_id(name)
    wins = get_blackjack_wins(blackjack_id)
    wins += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   UPDATE Blackjack
                   SET wins = ?
                   WHERE blackjack_id = ?
                """, (
        wins,
        blackjack_id
    ))
    conn.commit()
    conn.close()

def update_blackjack_losses(name):
    blackjack_id = get_blackjack_id(name)
    losses = get_blackjack_losses(blackjack_id)
    losses += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   UPDATE Blackjack
                   SET losses = ?
                   WHERE blackjack_id = ?
                """, (
        losses,
        blackjack_id
    ))
    conn.commit()
    conn.close()

def update_blackjack_draws(name):
    blackjack_id = get_blackjack_id(name)
    draws = get_blackjack_draws(blackjack_id)
    draws += 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   UPDATE Blackjack
                   SET draws = ?
                   WHERE blackjack_id = ?
                """, (
        draws,
        blackjack_id
    ))
    conn.commit()
    conn.close()

def payOut(characterData,winType, double_down_flag):
        #Current Bet in Chips
        currentBet = getCurrentBlackjackBet(characterData['name'])
        # Get the total bet amount from the dictionary
        match winType:
            #Blackjack - 3:1 (4x payout = 3 win + 1 start)
            case 3:
                #5x payout = 3 win + 2 start (double down)
                if double_down_flag:
                    totalWinnings = payoutHelper(5, currentBet, characterData['name'])
                    print("Blackjack! You won " + str(totalWinnings) + " credits! (3:1 payout w/ Double Down)")
                else:
                    totalWinnings = payoutHelper(4, currentBet, characterData['name'])
                    print("Blackjack! You won " + str(totalWinnings) + " credits! (3:1 payout)")
            #21 - 2:1 (3x payout - 2 win + 1 start
            case 2:
                # 4x payout = 2 win + 2 start (double down)
                if double_down_flag:
                    totalWinnings = payoutHelper(4, currentBet, characterData['name'])
                    print("21! You won " + str(totalWinnings) + " credits! (2:1 payout w/ Double Down)")
                else:
                    totalWinnings = payoutHelper(3, currentBet, characterData['name'])
                    print("21! You won " + str(totalWinnings) + " credits! (2:1 payout)")
            #Win, 1 to 1 - double the bet chips and add to player inventory
            case 1:
                # 3x payout = 1 win + 2 start (double down)
                if double_down_flag:
                    totalWinnings = payoutHelper(3, currentBet, characterData['name'])
                    print("You won " + str(totalWinnings) + " credits! (Double Downed!)")
                else:
                    totalWinnings = payoutHelper(2, currentBet, characterData['name'])
                    print("You won " + str(totalWinnings) + " credits! (Bet chips doubled and added to inventory)")
            #Draw, Add Back current bet to Credits
            #Double Down does not matter
            case -1:
                totalWinnings = payoutHelper(1, currentBet, characterData['name'])
                print("Draw! " + str(totalWinnings) + " credits in chips returned")
        mm.checkCreditsAchievements(characterData['name'])


def payoutHelper(modifier, currentBet, characterName):
    # 3:1 = 4 total
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

def getCurrentBlackjackBet(name):
    bjid = get_blackjack_id(name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current bet and chip values
    cursor.execute("""
                  SELECT current_bet, white, red, green, black, purple, orange
                  FROM Blackjack
                  WHERE blackjack_id = ?
               """, (
        bjid,
    ))
    bet = cursor.fetchone()
    conn.commit()
    conn.close()

    if bet:
        return {
            "Total": bet[0],    # current_bet value
            "White": int(bet[1]/1),    # white chip count
            "Red": int(bet[2]/5),      # red chip count
            "Green": int(bet[3]/25),    # green chip count
            "Black": int(bet[4]/100),    # black chip count
            "Purple": int(bet[5]/500),   # purple chip count
            "Orange": int(bet[6]/1000)    # orange chip count
        }

