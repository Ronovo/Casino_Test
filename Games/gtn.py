import formatter
import random
from formatter import drawMenuTopper
from DAL import character_maintenance as cm, gtn_maintenance as gm, money_maintenance as mm


def gtnStart(characterName):
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Welcome to the Guess The Number V0.4")
        print("1.) Start Game")
        print("2.) Game Information")
        print("3.) Bet Types")
        print("4.) Main Menu")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 3:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    startGtn(characterName)
                case "2":
                    printGTNGameInfo()
                case "3":
                    printBetTypes()
                case "4":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def printGTNGameInfo():
    # Page 1
    drawMenuTopper("Guess The Number!")
    print("A simple random number guessing game.")
    print("The game works in 3 easy steps")
    input(formatter.getInputText("Enter"))
    print("1.) Dealer picks a number - Ensures it doesn't change after your bet")
    print("2.) Place your Bet(s)")
    print("3.) Dealer reveals number")
    input(formatter.getInputText("Enter"))
    print("After the reveal, your total will be calculated and your winnings will be distributed")
    input(formatter.getInputText("Enter Menu"))
    return

def printBetTypes():
    drawMenuTopper("Types of Bets")
    print("For calculations below, we assume Easy Difficulty, with a range of 1-10")
    print("1. Exact match - You picked the exact number")
    print("Payout : 5:1,")
    print("2. Above/Below 1 - your guess was close (i.e. # is 4, guess is 5/3")
    print("Payout : 2:1")
    print("3. High/Low - High == 6-10, Low == 1-5")
    print("Payout : 1:1")
    print("4. Even/Odd - Even == Divisible by 2")
    print("Payout : 1:1")
    print("5. Range Guess - Pick 3 numbers in a range (i.e. 1-3)")
    print("Payout : 2:1")
    print("6. Pick 2 numbers - Get an extra guess (nullify +/-1 bonus)")
    print("Payout : 3:1")
    print("7. Lucky Number Combo - Bet twice, guess twice.")
    print("Payout : 20:1 if Guess #1, 5:1 if Guess #2")
    input(formatter.getInputText("Enter Menu"))
    return

def startGtn(name):
    characterData = cm.load_character_by_name(name)
    if characterData['gtn_id'] == 0:
        gm.create_gtn_connection(characterData)
    formatter.clear()
    formatter.drawMenuTopper("Pick your Difficulty")
    print("1.) Easy - Numbers : 1-10")
    print("X.) Medium - Numbers : 1-100")
    print("X.) Hard - Numbers : 1-1000")
    print("X.) Impossible - Numbers : 1-1000000000")
    print("5.) Main Menu")
    menuInput = input(formatter.getInputText("Choice"))
    if menuInput.isnumeric():
        formatter.clear()
        if 0 > int(menuInput) >= 5:
            input(formatter.getInputText("Wrong Number"))
        match menuInput:
            case "1":
                easyBet(name)
            case "2":
                mediumBet(name)
            case "3":
                hardBet(name)
            case "4":
                impossibleBet(name)
            case "5":
                return
            case _:
                input(formatter.getInputText("NonNumber"))
    else:
        input(formatter.getInputText("NonNumber"))

def easyBet(name):
    maxNumber = 10
    gm.update_number_max_pick(name, maxNumber)
    dealerNumber = dealerRoll(maxNumber)
    gm.update_dealer_number(name,dealerNumber)

    pickBet = 0
    highLowBet = 0
    highLowBetType = ""
    evenOddBet = 0
    evenOddBetType = ""
    rangeBet = 0
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Easy Difficulty Betting Menu")
        print("1.) Pick a number - Payout : 5:1 | Current Bet : " + str(pickBet))
        if highLowBetType == "":
            print("2.) Higher/Lower - Payout : 1:1 | Current Bet : " + str(highLowBet))
        else:
            print("2.) Higher/Lower - Payout : 1:1 | Current Bet : " + str(highLowBet) + " | " + highLowBetType)
        if evenOddBetType == "":
            print("3.) Even/Odd - Payout : 1:1 | Current Bet : " + str(evenOddBet))
        else:
            print("3.) Even/Odd - Payout : 1:1 | Current Bet : " + str(evenOddBet) + " | " + evenOddBetType)
        print("4.) Range Pick(3 Numbers) - Payout : 2:1 | Current Bet : " + str(rangeBet))
        print("X.) Lucky Number Combo - Payout: 20:1 if Number #1, 5:1 if Number #2")
        print("6.) Lock In Bet")
        print("7.) Go Back")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 5:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    pickBet += pickANumber(name)
                case "2":
                    highLowBet += highLow(maxNumber, name)
                    highFlag = gm.get_high_low_status(name)
                    if highFlag == 1:
                        highLowBetType = "High"
                    else:
                        highLowBetType = "Low"
                case "3":
                    evenOddBet += evenOdd(name)
                    evenFlag = gm.get_even_odd_status(name)
                    if evenFlag == 1:
                        evenOddBetType = "Even"
                    else:
                        evenOddBetType = "Odd"
                case "4":
                    rangeBet += pickARange(name)
                case "5":
                    input("Coming Soon")
                    pass
                case "6":
                    calculateWinsAndTotal(name, dealerNumber, maxNumber)
                    return
                case "7":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def mediumBet(name):
    pass

def hardBet(name):
    pass

def impossibleBet(name):
    pass

def pickANumber(name):
    print("You are placing a 'Pick The Number' bet.")
    picked_number = input("Pick a number between 1-10\n")
    selectedChips = mm.get_bet_chips_total(name,False)
    cm.remove_player_chips(name, selectedChips)
    gm.updateStartingBet(name,"Pick", selectedChips, picked_number)
    pickChipsTotal = mm.get_chips_total(selectedChips)
    return pickChipsTotal["Total"]

def pickARange(name):
    print("You are placing a 'Pick A Range' bet.")
    print("You choose the starting number of the range.")
    rangeStart = input("Pick a number between 1-8\n")
    selectedChips = mm.get_bet_chips_total(name,False)
    cm.remove_player_chips(name, selectedChips)
    gm.updateStartingBet(name,"Range", selectedChips, int(rangeStart))
    rangeChipsTotal = mm.get_chips_total(selectedChips)
    return rangeChipsTotal["Total"]

def highLow(maxNumber, name):
    formatter.clear()
    print("You are placing a 'High/Low Bet.")
    lowLimit = int(maxNumber / 2)
    highLimit = int(lowLimit + 1)
    print("Low Bet = Number Will be 1-" + str(lowLimit))
    print("High Bet = Number Will be " + str(highLimit) + "-" + str(maxNumber))
    while 1 > 0:
        print("1.) Low Bet")
        print("2.) High Bet")
        print("3.) Go Back")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 3:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    number = 1 #Send Low Number Into Place Bet Method
                    break
                case "2":
                    number = 2  # Send High Number Into Place Bet Method
                    break
                case "3":
                    highLowPlayerChips = gm.get_high_low_chips(name)
                    highLowTotals = mm.get_chips_total(highLowPlayerChips)
                    return highLowTotals["Total"]
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

    selectedChips = mm.get_bet_chips_total(name, False)
    cm.remove_player_chips(name, selectedChips)

    gm.updateStartingBet(name, "High/Low", selectedChips, number)
    highLowChipsTotal = mm.get_chips_total(selectedChips)
    return highLowChipsTotal["Total"]

def evenOdd(name):
    formatter.clear()
    print("You are placing a 'Even/Odd Bet.")
    print("Even Bet = Number Divisible by 2")
    print("Odd Bet = Number Not Divisible by 2")
    while 1 > 0:
        print("1.) Even Bet")
        print("2.) Odd Bet")
        print("3.) Go Back")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 3:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    number = 1 #Send Even Into Place Bet Method
                    break
                case "2":
                    number = 2  # Send Odd Into Place Bet Method
                    break
                case "3":
                    evenOddPlayerChips = gm.get_even_odd_chips(name)
                    evenOddTotals = mm.get_chips_total(evenOddPlayerChips)
                    return evenOddTotals["Total"]
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

    selectedChips = mm.get_bet_chips_total(name, False)
    cm.remove_player_chips(name, selectedChips)

    gm.updateStartingBet(name, "Even/Odd", selectedChips, number)
    evenOddChipsTotal = mm.get_chips_total(selectedChips)
    return evenOddChipsTotal["Total"]

def dealerRoll(maxNumber):
    return random.randint(1, maxNumber)

def calculateWinsAndTotal(name, dealerNumber, maxNumber):
    # Get the Ids for calculating
    gtn_id = gm.get_gtn_id(name)
    pick_id = gm.get_gtn_pick_id(gtn_id)
    high_low_id = gm.get_gtn_high_low_id(gtn_id)
    even_odd_id = gm.get_gtn_even_odd_id(gtn_id)
    range_id = gm.get_gtn_range_id(gtn_id)
    # Pick a Number Logic
    if pick_id != 0:
        pickInfo = gm.get_pick_info(pick_id)
        if pickInfo["number_picked"] != 0:
            pickedNumber = pickInfo["number_picked"]
            print("Your Number : " + str(pickedNumber) + " | Dealer's Number : " + str(dealerNumber))
            base_modifier = 0
            if pickedNumber == dealerNumber:
                print("Spot on! You Win!(5:1)\n")
                base_modifier = gm.get_base_modifier_by_name("Pick The Number")
            elif (pickedNumber + 1) == dealerNumber or (pickedNumber - 1) == dealerNumber:
                print("You were Close! You Still Win (2:1)!\n")
                base_modifier = gm.get_base_modifier_by_name("Above/Below")
            else:
                print("You lose the pick number bet!!\n")
            if base_modifier != 0:
                base_modifier = gm.get_base_modifier_by_difficulty(gm.get_max_number(gtn_id), base_modifier)
                characterData = cm.load_character_by_name(name)
                playerChips = mm.get_chips_by_character_id(characterData['id'])
                pickChips = gm.get_pick_chips(name)
                pickChipsTotals = mm.get_chips_total(pickChips)
                print("Total Pick A Number Bet Before Payout : " + str(pickChipsTotals["Total"]))
                for x in pickChips:
                    pickChips[x] += (pickChips[x] * base_modifier)
                    playerChips[x] += pickChips[x]
                pickChipsTotals = mm.get_chips_total(pickChips)
                print("Total Pick A Number Bet Winnings : " + str(pickChipsTotals["Total"]))
                cm.update_player_chips(playerChips, characterData['id'])
            input(formatter.getInputText("Enter"))
    # High/Low logic
    if high_low_id != 0:
        highLowInfo = gm.get_high_low_info(high_low_id)
        base_modifier = 0
        lowLimit = int(maxNumber / 2)
        if highLowInfo["high_picked"] == 1:
            print("Dealer's Number : " + str(dealerNumber))
            print("You Picked High")
            highLimit = lowLimit + 1
            print("Number range to win : " + str(highLimit) + "-" + str(maxNumber))
            if dealerNumber >= highLimit:
                print("You win! 1:1")
                base_modifier = 1
            else:
                print("You Lose!")
        if highLowInfo["low_picked"] == 1:
            print("Dealer's Number : " + str(dealerNumber))
            print("You Picked Low")
            print("Number range to win : 1-" + str(lowLimit))
            if dealerNumber <= lowLimit:
                print("You win! 1:1")
                base_modifier = 1
            else:
                print("You Lose!")
        if base_modifier != 0:
            characterData = cm.load_character_by_name(name)
            playerChips = mm.get_chips_by_character_id(characterData['id'])
            highLowChips = gm.get_high_low_chips(name)
            highLowChipsTotals = mm.get_chips_total(highLowChips)
            print("Total High/Low Bet Before Payout : " + str(highLowChipsTotals["Total"]))
            for x in highLowChips:
                highLowChips[x] += highLowChips[x]
                playerChips[x] += highLowChips[x]
            highLowChipsTotals = mm.get_chips_total(highLowChips)
            print("Total High/Low Bet Winnings : " + str(highLowChipsTotals["Total"]))
            cm.update_player_chips(playerChips, characterData['id'])
        input(formatter.getInputText("Enter"))
    # Even/Odd logic
    if even_odd_id != 0:
        evenOddInfo = gm.get_even_odd_info(even_odd_id)
        base_modifier = 0
        if evenOddInfo["even_picked"] == 1:
            print("Dealer's Number : " + str(dealerNumber))
            print("You Picked Even")
            if dealerNumber % 2 == 0:
                print("You win! 1:1")
                base_modifier = 1
            else:
                print("You Lose!")
        if evenOddInfo["odd_picked"] == 1:
            print("Dealer's Number : " + str(dealerNumber))
            print("You Picked Odd")
            if dealerNumber % 2 != 0:
                print("You win! 1:1")
                base_modifier = 1
            else:
                print("You Lose!")
        if base_modifier != 0:
            characterData = cm.load_character_by_name(name)
            playerChips = mm.get_chips_by_character_id(characterData['id'])
            evenOddChips = gm.get_even_odd_chips(name)
            evenOddChipsTotals = mm.get_chips_total(evenOddChips)
            print("Total Even/Odd Bet Before Payout : " + str(evenOddChipsTotals["Total"]))
            for x in evenOddChips:
                evenOddChips[x] += evenOddChips[x]
                playerChips[x] += evenOddChips[x]
            evenOddChipsTotals = mm.get_chips_total(evenOddChips)
            print("Total Even/Odd Bet Winnings : " + str(evenOddChipsTotals["Total"]))
            cm.update_player_chips(playerChips, characterData['id'])
        input(formatter.getInputText("Enter"))
    if range_id != 0:
        rangeInfo = gm.get_range_info(range_id)
        if rangeInfo["range_start"] != 0:
            rangeStart = rangeInfo["range_start"]
            rangeEnd = rangeInfo["range_end"]
            print("Dealer's Number : " + str(dealerNumber))
            print("Your picked range is " + str(rangeStart) + "-" + str(rangeEnd))
            base_modifier = 0
            if rangeStart <= dealerNumber <= rangeEnd:
                print("It's in range! You Win!(2:1)\n")
                base_modifier = gm.get_base_modifier_by_name("Range")
            else:
                print("Number not in range, you lose!\n")
            if base_modifier != 0:
                base_modifier = gm.get_base_modifier_by_difficulty(gm.get_max_number(gtn_id), base_modifier)
                characterData = cm.load_character_by_name(name)
                playerChips = mm.get_chips_by_character_id(characterData['id'])
                rangeChips = gm.get_range_chips(name)
                rangeChipsTotals = mm.get_chips_total(rangeChips)
                print("Total Pick A Range Bet Before Payout : " + str(rangeChipsTotals["Total"]))
                for x in rangeChips:
                    rangeChips[x] += (rangeChips[x] * base_modifier)
                    playerChips[x] += rangeChips[x]
                rangeChipsTotals = mm.get_chips_total(rangeChips)
                print("Total Pick A Range Bet Winnings : " + str(rangeChipsTotals["Total"]))
                cm.update_player_chips(playerChips, characterData['id'])
            input(formatter.getInputText("Enter"))
    #Set Up Player for the next game
    gm.update_gtn_new_game(gtn_id)
    gm.update_gtn_high_low_new_game(high_low_id)
    gm.update_gtn_pick_new_game(pick_id)
    gm.update_gtn_even_odd_new_game(even_odd_id)
    gm.update_gtn_range_new_game(range_id)


