import sqlite3
from DAL import character_maintenance as cm, achievement_maintenance as am

DB_PATH = "casino.db"

# --------------------------------------------------------
# STORAGE METHODS
# --------------------------------------------------------
def updateCurrentBet(name,currentBet):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create The new Blackjack entry
    cursor.execute("""
               UPDATE Characters
               SET current_bet = ?
               WHERE name = ?
            """, (
        currentBet,
        name
    ))
    conn.commit()
    conn.close()

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
def setBet(characterData,amount):
    #Update Character's Current Bet
    updateCurrentBet(characterData['name'],amount)
    #Remove Credits from Character
    deductCredits(characterData,amount)
    #Return updated character data
    return cm.load_character_by_name(characterData['name'])

def payOut(characterData,winFlag,winModifier):
    currentBet = characterData['current_bet']
    match winFlag:
        #Win, Payout at Modifier
        case 1:
            if characterData['credits'] == 1 or characterData['credits'] == 0:
                winnings = 2
            else :
                winnings = int(currentBet * winModifier)
            characterData = addCredits(characterData,winnings)
        #Draw, Add Back current bet to Credits
        case -1:
            characterData = addCredits(characterData,characterData['current_bet'])
    updateCurrentBet(characterData['name'], 0)
    checkCreditsAchievements(characterData)
    return cm.load_character_by_name(characterData['name'])