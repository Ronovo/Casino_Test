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

def checkCreditsAchievements(characterName):
    characterData = cm.load_character_by_name(characterName)
    chips = get_chips_by_character_id(characterData['id'])
    totals = get_chips_total(chips)
    playerCredits = totals['Total']
    characterData['credits'] = playerCredits
    difficulty = characterData['difficulty']
    if playerCredits >= 1000000:
        am.insert_achievement(characterName,"Money_1000000")
    elif playerCredits >= 100000:
        am.insert_achievement(characterName, "Money_100000")
    elif playerCredits >= 10000:
        #Exlude Easy, since it's the starting amount
        if difficulty != "Easy":
            am.insert_achievement(characterName, "Money_10000")
    elif playerCredits >= 1000:
        if difficulty == "Very Hard" or difficulty == "Hard":
            am.insert_achievement(characterName, "Money_1000")
    elif playerCredits >= 100:
        if difficulty == "Very Hard":
            am.insert_achievement(characterName, "Money_100")

# --------------------------------------------------------
# MAIN METHODS
# --------------------------------------------------------
def setChipBet(characterData,chips,game):
    match game:
        case "BJ":
            #Update Character's Current Bet
            updateBlackjackBet(characterData['name'],chips)
            #Return updated character data
            return cm.load_character_by_name(characterData['name'])

def payOut(characterData,winType, game, double_down_flag):
    match game:
        case "BJ":
            #Current Bet in Chips
            currentBet = getCurrentBlackjackBet(characterData['name'])
            # Get the total bet amount from the dictionary
            totalBetAmount = currentBet["Total"] if currentBet else 0
            match winType:
                #Blackjack - 3:1 (4x payout = 3 win + 1 start)
                case 3:
                    #5x payout = 3 win + 2 start (double down)
                    if double_down_flag:
                        totalWinnings = payoutHelper(5,totalBetAmount, currentBet, characterData['name'])
                        print("Blackjack! You won " + str(totalWinnings) + " credits! (3:1 payout w/ Double Down)")
                    else:
                        totalWinnings = payoutHelper(4,totalBetAmount, currentBet, characterData['name'])
                        print("Blackjack! You won " + str(totalWinnings) + " credits! (3:1 payout)")
                #21 - 2:1 (3x payout - 2 win + 1 start
                case 2:
                    # 4x payout = 2 win + 2 start (double down)
                    if double_down_flag:
                        totalWinnings = payoutHelper(4, totalBetAmount, currentBet, characterData['name'])
                        print("21! You won " + str(totalWinnings) + " credits! (2:1 payout w/ Double Down)")
                    else:
                        totalWinnings = payoutHelper(3, totalBetAmount, currentBet, characterData['name'])
                        print("21! You won " + str(totalWinnings) + " credits! (2:1 payout)")
                #Win, 1 to 1 - double the bet chips and add to player inventory
                case 1:
                    # 3x payout = 1 win + 2 start (double down)
                    if double_down_flag:
                        totalWinnings = payoutHelper(3, totalBetAmount, currentBet, characterData['name'])
                        print("You won " + str(totalWinnings) + " credits! (Double Downed!)")
                    else:
                        totalWinnings = payoutHelper(2, totalBetAmount, currentBet, characterData['name'])
                        print("You won " + str(totalWinnings) + " credits! (Bet chips doubled and added to inventory)")
                #Draw, Add Back current bet to Credits
                #Double Down does not matter
                case -1:
                    totalWinnings = payoutHelper(1, totalBetAmount, currentBet, characterData['name'])
                    print("Draw! " + str(totalWinnings) + " credits in chips returned")
            checkCreditsAchievements(characterData['name'])

def payoutHelper(modifier, totalBetAmount, currentBet, characterName):
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
        #Get Total to return
        totalWinningChips = get_chips_total(blackjackChips)
        return totalWinningChips["Total"]
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
               SET current_bet = ?, white = ?, red = ?, green = ?, black = ?, purple = ?, orange = ?
               WHERE blackjack_id = ?
            """, (
        currentBet["Total"],
        currentBet["White"],
        currentBet["Red"],
        currentBet["Green"],
        currentBet["Black"],
        currentBet["Purple"],
        currentBet["Orange"],
        bjid
    ))
    conn.commit()
    conn.close()

def getCurrentBlackjackBet(name):
    bjid = bjs.get_blackjack_id(name)

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
                    selectedChipsWork = place_bet_chips("White",selectedChipsWork, chipsWork)
                case "2":
                    selectedChipsWork = place_bet_chips("Red",selectedChipsWork, chipsWork)
                case "3":
                    selectedChipsWork = place_bet_chips("Green",selectedChipsWork, chipsWork)
                case "4":
                    selectedChipsWork = place_bet_chips("Black",selectedChipsWork, chipsWork)
                case "5":
                    selectedChipsWork = place_bet_chips("Purple",selectedChipsWork, chipsWork)
                case "6":
                    selectedChipsWork = place_bet_chips("Orange",selectedChipsWork, chipsWork)
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

def place_bet_chips(color, selectedChips, availableChips=None):
    numberOfChips = input("How many " + color + " chips do you want to add to bet?\n")
    numberOfChips = checkNumber(numberOfChips)
    
    # Handle negative numbers - set to 0
    if numberOfChips < 0:
        numberOfChips = 0
    
    # Validate against available chips if provided
    if availableChips is not None:
        available = availableChips.get(color, 0)
        if numberOfChips > available:
            print(f"You only have {available} {color} chips available. Setting to maximum available.")
            numberOfChips = available
    
    selectedChips[color] += numberOfChips
    return selectedChips

def add_chips(color, chips, availableChips=None):
    numberOfChips = input("How many " + color + " chips do you want to add to exchange?\n")
    numberOfChips = checkNumber(numberOfChips)
    
    # Handle negative numbers - set to 0
    if numberOfChips < 0:
        numberOfChips = 0
    
    # Validate against available chips if provided
    if availableChips is not None:
        available = availableChips.get(color, 0)
        if numberOfChips > available:
            print(f"You only have {available} {color} chips available. Setting to maximum available.")
            numberOfChips = available
    
    chips[color] += numberOfChips
    return chips

def add_chips_from_credits(color, chips, availableCredits):
    """Add chips to exchange, validating against available credits."""
    # Get the chip value based on color
    chip_values = {
        "White": 1,
        "Red": 5,
        "Green": 25,
        "Black": 100,
        "Purple": 500,
        "Orange": 1000
    }
    
    numberOfChips = input("How many " + color + " chips do you want to add to exchange?\n")
    numberOfChips = checkNumber(numberOfChips)
    
    # Handle negative numbers - set to 0
    if numberOfChips < 0:
        numberOfChips = 0
    
    # Calculate cost and validate against available credits
    chip_value = chip_values.get(color, 0)
    total_cost = numberOfChips * chip_value
    
    if total_cost > availableCredits:
        max_chips = availableCredits // chip_value
        print(f"You only have {availableCredits} credits available. Maximum {color} chips you can get: {max_chips}. Setting to maximum.")
        numberOfChips = max_chips
    
    chips[color] += numberOfChips
    return chips

def exhangeChips(name):
    displayCreditTotal = 0
    finalExchangeChipsIn = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
    finalExchangeChipsOut = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
    characterData = cm.load_character_by_name(name)
    finalPlayerChips = get_chips_by_character_id(characterData["id"])
    while 1 != 0:
        formatter.clear()
        formatter.drawMenuTopper("Chip Exchange")
        #Add the Total
        print("Exchange Credits = " + str(displayCreditTotal))
        print("1.) Add Credits to Exchange")
        print("2.) Add Chips from Exchange credits")
        print("3.) Lock In Chip Exchange")
        print("4.) Quit to Main Menu (No Saving)")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 4:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    finalExchangeChipsIn, finalPlayerChips = add_exchange_credits(finalExchangeChipsIn, finalPlayerChips)
                    finalExchangeCreditTotals = get_chips_total(finalExchangeChipsIn)
                    displayCreditTotal = finalExchangeCreditTotals["Total"]
                case "2":
                    finalExchangeChipsOut, displayCreditTotal = add_chips_from_total(finalExchangeChipsOut, displayCreditTotal)
                case "3":
                    characterData = cm.load_character_by_name(name)
                    playerChips = get_chips_by_character_id(characterData["id"])
                    for x in finalExchangeChipsIn:
                        playerChips[x] -= finalExchangeChipsIn[x]
                    for x in finalExchangeChipsOut:
                        playerChips[x] += finalExchangeChipsOut[x]
                    cm.update_player_chips(playerChips, characterData["id"])
                    return
                case "4":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def add_exchange_credits(finalExchangeChipsIn, finalPlayerChips):
   #Intialzie The Start Variables
   exchangeChipsWorkStart = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
   finalExchangeChipsStart = dict(finalExchangeChipsIn)
   exchangeChips = dict(finalExchangeChipsStart)
   playerChipsStart = dict(finalPlayerChips)
   playerChips = dict(finalPlayerChips)
   while 1 != 0:
       playerTotals = get_chips_total(playerChips)
       exchangeTotals = get_chips_total(exchangeChips)
       exchangeChipsWork = dict(exchangeChipsWorkStart)
       formatter.clear()
       formatter.drawMenuTopper("Total of chips remaining: " + str(exchangeTotals["Total"]) + " credits")
       print("1.) White Chips ($1)")
       print("Player : " + str(playerChips["White"]) + " | Total : " + str(playerTotals["White"]) + " credits")
       print("Exchange : " + str(exchangeChips["White"]) + " | Total : " + str(exchangeTotals["White"]) + " credits")
       print("\n2.) Red Chips ($5)")
       print("Player : " + str(playerChips["Red"]) + " | Total : " + str(playerTotals["Red"]) + " credits")
       print("Exchange : " + str(exchangeChips["Red"]) + " | Total : " + str(exchangeTotals["Red"]) + " credits")
       print("\n3.) Green Chips ($25)")
       print("Player : " + str(playerChips["Green"]) + " | Total : " + str(playerTotals["Green"]) + " credits")
       print("Exchange : " + str(exchangeChips["Green"]) + " | Total : " + str(exchangeTotals["Green"]) + " credits")
       print("\n4.) Black Chips ($100)")
       print("Player : " + str(playerChips["Black"]) + " | Total : " + str(playerTotals["Black"]) + " credits")
       print("Exchange : " + str(exchangeChips["Black"]) + " | Total : " + str(exchangeTotals["Black"]) + " credits")
       print("\n5.) Purple Chips ($500)")
       print("Player : " + str(playerChips["Purple"]) + " | Total : " + str(playerTotals["Purple"]) + " credits")
       print("Exchange : " + str(exchangeChips["Purple"]) + " | Total : " + str(exchangeTotals["Purple"]) + " credits")
       print("\n6.) Orange Chips ($1000)")
       print("Player : " + str(playerChips["Orange"]) + " | Total : " + str(playerTotals["Orange"]) + " credits")
       print("Exchange : " + str(exchangeChips["Orange"]) + " | Total : " + str(exchangeTotals["Orange"]) + " credits")
       print("\n7.) Reset The Current Exchange")
       print("8.) Lock In Exchange")
       menuInput = input(formatter.getInputText("Choice"))
       if menuInput.isnumeric():
           if 0 > int(menuInput) >= 7:
               input(formatter.getInputText("Wrong Number"))
           match menuInput:
               case "1":
                   exchangeChipsWork = add_chips("White", exchangeChipsWork, playerChips)
               case "2":
                   exchangeChipsWork = add_chips("Red", exchangeChipsWork, playerChips)
               case "3":
                   exchangeChipsWork = add_chips("Green", exchangeChipsWork, playerChips)
               case "4":
                   exchangeChipsWork = add_chips("Black", exchangeChipsWork, playerChips)
               case "5":
                   exchangeChipsWork = add_chips("Purple", exchangeChipsWork, playerChips)
               case "6":
                   exchangeChipsWork = add_chips("Orange", exchangeChipsWork, playerChips)
               case "7":
                   exchangeChips = dict(finalExchangeChipsStart)
                   playerChips = dict(playerChipsStart)
                   finalExchangeChipsIn = dict(finalExchangeChipsStart)
               case "8":
                   return finalExchangeChipsIn, finalPlayerChips
       else:
           input(formatter.getInputText("Enter"))
       for x in exchangeChips:
           #
           if playerChips[x] != 0:
               playerChips[x] -= exchangeChipsWork[x]
               finalPlayerChips[x] -= exchangeChipsWork[x]
               exchangeChips[x] += exchangeChipsWork[x]
               finalExchangeChipsIn[x] += exchangeChipsWork[x]


def add_chips_from_total(finalExchangeChipsOut, displayCreditTotal):
    # Intialzie The Start Variables
    displayCreditTotalStart = int(displayCreditTotal)
    exchangeChipsWorkStart = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0}
    finalExchangeChipsStart = dict(finalExchangeChipsOut)
    exchangeChips = dict(finalExchangeChipsStart)
    while 1 != 0:
        exchangeTotals = get_chips_total(exchangeChips)
        exchangeChipsWork = dict(exchangeChipsWorkStart)
        formatter.clear()
        formatter.drawMenuTopper("Total Credits To Assign: " + str(displayCreditTotal) + " credits")
        print("1.) White Chips ($1)")
        print("Exchange : " + str(exchangeChips["White"]) + " | Total : " + str(exchangeTotals["White"]) + " credits")
        print("\n2.) Red Chips ($5)")
        print("Exchange : " + str(exchangeChips["Red"]) + " | Total : " + str(exchangeTotals["Red"]) + " credits")
        print("\n3.) Green Chips ($25)")
        print("Exchange : " + str(exchangeChips["Green"]) + " | Total : " + str(exchangeTotals["Green"]) + " credits")
        print("\n4.) Black Chips ($100)")
        print("Exchange : " + str(exchangeChips["Black"]) + " | Total : " + str(exchangeTotals["Black"]) + " credits")
        print("\n5.) Purple Chips ($500)")
        print("Exchange : " + str(exchangeChips["Purple"]) + " | Total : " + str(exchangeTotals["Purple"]) + " credits")
        print("\n6.) Orange Chips ($1000)")
        print("Exchange : " + str(exchangeChips["Orange"]) + " | Total : " + str(exchangeTotals["Orange"]) + " credits")
        print("\n7.) Reset The Current Exchange")
        print("8.) Lock In Exchange")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            if 0 > int(menuInput) >= 7:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    exchangeChipsWork = add_chips_from_credits("White", exchangeChipsWork, displayCreditTotal)
                case "2":
                    exchangeChipsWork = add_chips_from_credits("Red", exchangeChipsWork, displayCreditTotal)
                case "3":
                    exchangeChipsWork = add_chips_from_credits("Green", exchangeChipsWork, displayCreditTotal)
                case "4":
                    exchangeChipsWork = add_chips_from_credits("Black", exchangeChipsWork, displayCreditTotal)
                case "5":
                    exchangeChipsWork = add_chips_from_credits("Purple", exchangeChipsWork, displayCreditTotal)
                case "6":
                    exchangeChipsWork = add_chips_from_credits("Orange", exchangeChipsWork, displayCreditTotal)
                case "7":
                    exchangeChips = dict(finalExchangeChipsStart)
                    finalExchangeChipsOut = dict(finalExchangeChipsStart)
                    displayCreditTotal = int(displayCreditTotalStart)
                case "8":
                    return finalExchangeChipsOut, displayCreditTotal
        else:
            input(formatter.getInputText("Enter"))
        for x in exchangeChipsWork:
            finalExchangeChipsOut[x] += exchangeChipsWork[x]
            exchangeChips[x] += exchangeChipsWork[x]
        workTotals = get_chips_total(exchangeChipsWork)
        displayCreditTotal -= workTotals["Total"]


def get_bet_chips_total(name):
    characterData = cm.load_character_by_name(name)
    chips = get_chips_by_character_id(characterData['id'])
    selectedChips = select_bet_chips(chips)
    return selectedChips

def chips_pay_out_menu(name, winnings):
    characterData = cm.load_character_by_name(name)
    cashoutChips = select_bet_chips(characterData["name"])
    payoutTotals = get_chips_total(cashoutChips)
    print("Payout Credit Total is : " + str(payoutTotals["Total"]))
    cm.update_player_chips_add(name, cashoutChips)
    print("Chips saved to character")
    return payoutTotals["Total"]