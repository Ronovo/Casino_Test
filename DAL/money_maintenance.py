import sqlite3
from DAL import character_maintenance as cm, achievement_maintenance as am, blackjack_save as bjs

DB_PATH = "casino.db"

# --------------------------------------------------------
# STORAGE METHODS
# --------------------------------------------------------
def deductCredits(characterData, amount):
    characterData['credits'] -= amount
    return storeCredits(characterData)

def addCredits(characterData, amount):
    characterData['credits'] += amount
    return storeCredits(characterData)

def storeCredits(characterData):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Blackjack entry
    cursor.execute("""
                       UPDATE Characters
                       SET credits = ?
                       WHERE name = ?
                    """, (
        characterData['credits'],
        characterData['name']
    ))
    conn.commit()
    conn.close()
    return cm.load_character_by_name(characterData['name'])

def checkCreditsAchievements(characterData):
    currentCredits = characterData['credits']
    difficulty = characterData['difficulty']
    name = characterData['name']
    if currentCredits >= 1000000:
        am.insert_achievement(name,"Money_1000000")
    elif currentCredits >= 100000:
        am.insert_achievement(name, "Money_100000")
    elif currentCredits >= 10000:
        if difficulty != "Easy":
            am.insert_achievement(name, "Money_10000")
    elif currentCredits >= 1000:
        if difficulty == "Hard":
            am.insert_achievement(name, "Money_1000")

# --------------------------------------------------------
# MAIN METHODS
# --------------------------------------------------------
def setBet(characterData,amount,game):
    match game:
        case "BJ":
            #Update Character's Current Bet
            updateBlackjackBet(characterData['name'],amount)
            #Remove Credits from Character
            deductCredits(characterData,amount)
            #Return updated character data
            return cm.load_character_by_name(characterData['name'])

def payOut(characterData,winFlag,winModifier, game):
    match game:
        case "BJ":
            currentBet = getCurrentBlackjackBet(characterData['name'])
            match winFlag:
                #Win, Payout at Modifier
                case 1:
                    if characterData['credits'] == 1 or characterData['credits'] == 0:
                        winnings = 2
                    elif currentBet == 1:
                        winnings = 2
                    else :
                        winnings = int(currentBet * winModifier)
                    characterData = addCredits(characterData,winnings)
                    print("You won " + str(winnings) + " credits!")
                #Draw, Add Back current bet to Credits
                case -1:
                    characterData = addCredits(characterData,currentBet)
            setBet(characterData, 0, "BJ")
            checkCreditsAchievements(characterData)
            return cm.load_character_by_name(characterData['name'])
# --------------------------------------------------------
# BLACKJACK METHODS
# --------------------------------------------------------
def updateBlackjackBet(name, currentBet):
    bjid = bjs.get_blackjack_id(name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update the Current Bet
    cursor.execute("""
               UPDATE Blackjack
               SET current_bet = ?
               WHERE blackjack_id = ?
            """, (
        currentBet,
        bjid
    ))
    conn.commit()
    conn.close()

def getCurrentBlackjackBet(name):
    bjid = bjs.get_blackjack_id(name)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update the Current Bet
    cursor.execute("""
                  SELECT current_bet
                  FROM Blackjack
                  WHERE blackjack_id = ?
               """, (
        bjid,
    ))
    bet = cursor.fetchone()
    conn.commit()
    conn.close()
    return bet[0]