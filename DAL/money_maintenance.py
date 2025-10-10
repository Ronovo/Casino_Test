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

def checkNumber(answer):
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
    formatter.drawMenuLine()
    print("Total = " + str(totals["Total"]) + " credits")
    input(formatter.getInputText("Enter"))
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

#TODO : Add Total Bet to top of the menu
#TODO : Add Validation to inputs
def select_bet_chips(chips):
    chipsWork = dict(chips)
    selectedChips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
    while 1 != 0:
        formatter.clear()
        selectedChipsWork = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
        totalRemaining = get_chips_total(chipsWork)
        formatter.drawMenuTopper("Total of chips remaining : " + str(totalRemaining["Total"]) + " credits")
        print("1.) White Chips ($1) | White Total : " + str(totalRemaining["White"]))
        print("Bet : " + str(selectedChips["White"]) + " | Remaining : " + str(chipsWork["White"]))
        print("\n2.) Red Chips ($5) | Red Total : " + str(totalRemaining["Red"]))
        print("Bet : " + str(selectedChips["Red"]) + " | Remaining : " + str(chipsWork["Red"]))
        print("\n3.) Green Chips ($25) | White Total : " + str(totalRemaining["Green"]))
        print("Bet : " + str(selectedChips["Green"]) + " | Remaining : " + str(chipsWork["Green"]))
        print("\n4.) Black Chips ($100) | White Total : " + str(totalRemaining["Black"]))
        print("Bet : " + str(selectedChips["Black"]) + " | Remaining : " + str(chipsWork["Black"]))
        print("\n5.) Purple Chips ($500) | White Total : " + str(totalRemaining["Purple"]))
        print("Bet : " + str(selectedChips["Purple"]) + " | Remaining : " + str(chipsWork["Purple"]))
        print("\n6.) Orange Chips ($1000) | White Total : " + str(totalRemaining["Orange"]))
        print("Bet : " + str(selectedChips["Orange"]) + " | Remaining : " + str(chipsWork["Orange"]))
        print("\n7.) All In (Bet Every Chip)")
        print("8.) Reset Bets")
        print("9.) Lock In Bet")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            if 0 > int(menuInput) >= 7:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    selectedChipsWork = place_bet_chips("White",selectedChipsWork)
                case "2":
                    selectedChipsWork = place_bet_chips("Red",selectedChipsWork)
                case "3":
                    selectedChipsWork = place_bet_chips("Green",selectedChipsWork)
                case "4":
                    selectedChipsWork = place_bet_chips("Black",selectedChipsWork)
                case "5":
                    selectedChipsWork = place_bet_chips("Purple",selectedChipsWork)
                case "6":
                    selectedChipsWork = place_bet_chips("Orange",selectedChipsWork)
                case "7":
                     for x in chipsWork:
                         selectedChipsWork[x] = chipsWork[x]
                case "8":
                    chipsWork = dict(chips)
                    selectedChips = dict(selectedChipsWork)
                case "9":
                    return selectedChips
        else:
            input(formatter.getInputText("Enter"))
        for x in selectedChips:
            selectedChips[x] += selectedChipsWork[x]
            chipsWork[x] -= selectedChipsWork[x]

def place_bet_chips(color, selectedChips):
    numberOfChips = input("How many " + color + " chips do you want to add to bet?\n")
    numberOfChips = checkNumber(numberOfChips)
    selectedChips[color] += numberOfChips
    return selectedChips

def cashout_chips(color, chips):
    numberOfChips = input("How many " + color + " chips do you want to add to payout?\n")
    numberOfChips = checkNumber(numberOfChips)
    chips[color] += numberOfChips
    return chips

#TODO : Add Validation to inputs
def payOutChips(name, winnings):
    winningsBackup = int(winnings)
    charData = cm.load_character_by_name(name)
    cashoutChips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
    while 1 != 0:
        formatter.clear()
        cashoutChipsWork = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
        totalPayout = get_chips_total(cashoutChips)
        formatter.drawMenuTopper("Total of chips remaining to cash out: " + str(winnings) + " credits")
        print("1.) White Chips ($1)")
        print("Cashout : " + str(cashoutChips["White"]) + " | Total : " + str(totalPayout["White"]) + " credits")
        print("\n2.) Red Chips ($5)")
        print("Cashout : " + str(cashoutChips["Red"]) + " | Remaining : " + str(totalPayout["Red"]) + " credits")
        print("\n3.) Green Chips ($25)")
        print("Cashout : " + str(cashoutChips["Green"]) + " | Remaining : " + str(totalPayout["Green"]) + " credits")
        print("\n4.) Black Chips ($100)")
        print("Cashout : " + str(cashoutChips["Black"]) + " | Remaining : " + str(totalPayout["Black"]) + " credits")
        print("\n5.) Purple Chips ($500)")
        print("Cashout : " + str(cashoutChips["Purple"]) + " | Remaining : " + str(totalPayout["Purple"]) + " credits")
        print("\n6.) Orange Chips ($1000)")
        print("Cashout : " + str(cashoutChips["Orange"]) + " | Remaining : " + str(totalPayout["Orange"]) + " credits")
        print("\n7.) Reset Cashouts")
        print("8.) Lock In Payout(Remaining Balance Deleted)")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            if 0 > int(menuInput) >= 7:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    selectedChipsWork = cashout_chips("White", cashoutChipsWork)
                case "2":
                    selectedChipsWork = cashout_chips("Red", cashoutChipsWork)
                case "3":
                    selectedChipsWork = cashout_chips("Green", cashoutChipsWork)
                case "4":
                    selectedChipsWork = cashout_chips("Black", cashoutChipsWork)
                case "5":
                    selectedChipsWork = cashout_chips("Purple", cashoutChipsWork)
                case "6":
                    selectedChipsWork = cashout_chips("Orange", cashoutChipsWork)
                case "7":
                    cashoutChips = dict(cashoutChipsWork)
                    winnings = winningsBackup
                case "8":
                    return cashoutChips
        else:
            input(formatter.getInputText("Enter"))
        cashoutTotals = get_chips_total(cashoutChipsWork)
        for x in cashoutChipsWork:
            winnings -= cashoutTotals[x]
            cashoutChips[x] += cashoutChipsWork[x]