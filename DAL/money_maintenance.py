import sqlite3

import formatter
from DAL import character_maintenance as cm, achievement_maintenance as am, blackjack_maintenance as bjs

DB_PATH = "casino.db"

# --------------------------------------------------------
# STORAGE METHODS
# --------------------------------------------------------
def deductCredits(characterData, amount):
    if amount < 0:
        amount *= -1
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
        #Exlude Easy, since it's the starting amount
        if difficulty != "Easy":
            am.insert_achievement(name, "Money_10000")
    elif currentCredits >= 1000:
        if difficulty == "Very Hard" or difficulty == "Hard":
            am.insert_achievement(name, "Money_1000")
    elif currentCredits >= 100:
        if difficulty == "Very Hard":
            am.insert_achievement(name, "Money_100")

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

def checkBetNumber(answer):
    if answer.isnumeric():
        bet = int(answer)
    else:
        bet = 0
    return bet

# --------------------------------------------------------
# Chips Logic
# --------------------------------------------------------
def getStartingChips(name,difficulty,total):
    characterData = cm.load_character_by_name(name)
    chips = {}
    match difficulty:
        case "Easy":
            chips = getChipsByDifficulty("easy_amount")
        case "Medium":
            chips = getChipsByDifficulty("medium_amount")
        case "Hard":
            chips = getChipsByDifficulty("hard_amount")
        case "Very Hard":
            chips = getChipsByDifficulty("vhard_amount")
    return chips

def getChipsByDifficulty(difficulty):
    startingChips = {}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql_query = f"SELECT color, {difficulty} FROM Chips;"
    # Update the Current Bet
    cursor.execute(sql_query)
    chips = cursor.fetchall()
    for chip in chips:
        startingChips[chip[0]] = chip[1]
    conn.commit()
    conn.close()
    return startingChips

def chipsMenu(name):
    char = cm.load_character_by_name(name)
    chips = get_chips_by_character_id(char["id"])
    totals = get_chips_total(chips)
    formatter.clear()
    formatter.drawMenuTopper("Chips Menu")
    print("White Chips ($1) : " + str(chips["White"]) + " = " + str(totals["White"]) + " credits")
    print("Red Chips ($5) : " + str(chips["Red"]) + " = " + str(totals["Red"]) + " credits")
    print("Green Chips ($25) : " + str(chips["Green"]) + " = " + str(totals["Green"]) + " credits")
    print("Black Chips ($100) : " + str(chips["Black"]) + " = " + str(totals["Black"]) + " credits")
    print("Purple Chips ($500) : " + str(chips["Purple"]) + " = " + str(totals["Purple"]) + " credits")
    print("Orange Chips ($1000) : " + str(chips["Orange"]) + " = " + str(totals["Orange"]) + " credits")
    print("Total = " + str(totals["Total"]) + " credits")
    formatter.getInputText("Enter")
    return

def get_chips_by_character_id(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql_query = f"SELECT * FROM PlayerChips WHERE character_id = {id};"

    cursor.execute(sql_query)
    chips = cursor.fetchone()
    player_chips = {
        "White": chips[2],
        "Red": chips[3],
        "Green": chips[4],
        "Black": chips[5],
        "Purple": chips[6],
        "Orange": chips[7],
    }
    return player_chips

def get_chips_total(chips):
    whiteTotal = chips["White"]
    redTotal = chips["Red"] * 5
    greenTotal = chips["Green"] * 25
    blackTotal = chips["Black"] * 100
    purpleTotal = chips["Purple"] * 500
    orangeTotal = chips["Orange"] * 1000
    chipTotal = orangeTotal + purpleTotal + blackTotal + greenTotal + redTotal + chips["White"]
    totals = {"White" : whiteTotal, "Red" : redTotal, "Green" : greenTotal,
              "Black" : blackTotal, "Purple" : purpleTotal, "Orange" : orangeTotal,
              "Total" : chipTotal}
    return totals