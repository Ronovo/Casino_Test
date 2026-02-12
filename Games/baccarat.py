from DAL import character_maintenance as cm, money_maintenance as mm
from DAL import baccarat_maintenance as bm
from Helpers import deckmaintenance as dm
import formatter

def baccaratStart(characterName):
    while 1 > 0:
        # Check if player has any chips for game over state
        characterData = cm.load_character_by_name(characterName)
        chips = mm.get_chips_by_character_id(characterData["id"])
        chipTotal = mm.get_chips_total(chips)

        if chipTotal["Total"] == 0:
            return "GAME_OVER"
        formatter.clear()
        formatter.drawMenuTopper("Welcome to the Baccarat V0.0")
        print("1.) Start Game(Deal In)")
        print("2.) Game Information")
        print("3.) Pay Table")
        print("4.) Main Menu")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 4:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    characterData = cm.load_character_by_name(characterName)
                    currentDeck = dm.restockDeck()
                    dealin(currentDeck, characterData)
                case "2":
                    printBaccaratGameInfo()
                case "3":
                    printPayTableBaccarat()
                case "4":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))


def printBaccaratGameInfo():
    # Page 1
    print("Baccarat is so popular, it's James Bond's favorite game!")
    print("It is also one of the easiest to play!")
    print("The goal of the game is to get as close to 9 as you can.")
    print("If you go over 9, it loops back around to 0.")
    print("i.e. A hand value of 13 = 3 in calculating Baccarat")
    print("Aces = 1")
    print("Face Cards/10s = 0")
    print("Deck resets every game. Card counting does not work")
    input(formatter.getInputText("Enter"))
    #Page 2
    print("You start by betting before the cards are dealt.")
    print("There are 3 bets available : Player, Banker, Tie")
    print("You are betting on the final card values and how close they are to 9")
    print("If Player's hand is closer to 9, You win the 'Player' bet.")
    print("If Dealer's hand is closer to 9, You win the 'Banker' bet.")
    print("If Player and Dealer hand are tied, you win the 'Tie' bet")
    input(formatter.getInputText("Enter"))
    print("After betting, cards are dealt, and the dealer does all the calculations.")
    print("-If your opening hand value is 8 or 9, it is called a 'natural'.")
    print(" You do not receive a 3rd card.")
    print("-If your opening hand value is 6 or 7, You do not receive a 3rd card.")
    print("-If your opening hand value is 0-5, You receive a 3rd card.")
    print("After, the dealer deals the Banks cards based on your current hand value.")
    print("After the dealer's cards are dealt, hand calculations happen, and payouts happen.")
    print("Check Pay Tables for payout information and Special Rules.")
    input(formatter.getInputText("Enter Menu"))
    return

def printPayTableBaccarat():
    formatter.drawMenuTopper("Baccarat Pay Tables")
    print("NORMAL")
    formatter.drawMenuLine()
    print("Betting on Player or Banker pays 1:1.")
    print("Betting on a Tie pays 8:1")
    formatter.drawMenuTopper("BONUS BETS")
    print("You MUST place a normal bet(Not a Tie) before placing this bet.")
    print("DRAGON 7")
    print("You win 40:1 if the dealer wins with a three card hand that equals 7")
    print("PANDA 8")
    print("You win 25:1 if the player wins with a three card hand that equals 8")
    input(formatter.getInputText("Enter Menu"))

def dealin(currentDeck, characterData):
    # Set Up
    hand = []
    dealerHand = []

    # TODO : If current bet is 0, return
    # Create a new baccarat entry for the character if this is the first time
    if characterData['baccarat_id'] == 0:
        characterData = bm.create_baccarat_connection(characterData)
    betType = get_bet_type()
    bm.update_bet_type(characterData["name"], betType)
    selectedChips = mm.get_bet_chips_total(characterData["name"])
    cm.remove_player_chips(characterData["name"], selectedChips)
    mm.setChipBet(characterData, selectedChips, 'Baccarat')

    formatter.clear()
    for x in range(2):
        card = dm.draw(currentDeck)
        print("You drew a " + dm.getCardName(card))
        hand.append(card)
    input(formatter.getInputText("Enter"))
    sumOfHand = checkSumOfHand(hand)
    if sumOfHand > 9:
        sumOfHand = wrapAroundHandValue(sumOfHand)
    print("Your hand is currently worth " + str(sumOfHand) + "\n")

    naturalFlag = False
    thirdCardValue = 0
    if sumOfHand == 8 or sumOfHand == 9:
        naturalFlag = True
        print("You got a natural! You do not get another card.")
    elif sumOfHand < 6:
        card = dm.draw(currentDeck)
        print("You are in range for another card")
        print("You drew a " + dm.getCardName(card))
        hand.append(card)
        checkThirdCardDeck = [card]
        thirdCardValue = checkSumOfHand(checkThirdCardDeck)
        sumOfHand += thirdCardValue
        if sumOfHand > 9:
            sumOfHand = wrapAroundHandValue(sumOfHand)
        print("Sum of your hand : " + str(sumOfHand))
    else:
        print("You are in range to not receive another card")

    input(formatter.getInputText("Enter"))
    for x in range(2):
        card = dm.draw(currentDeck)
        dealerHand.append(card)
    sumOfDealerHand = checkDealerSumOfHand(dealerHand)
    print("The Dealer's hand is worth " + str(sumOfDealerHand))
    if sumOfDealerHand > 9:
        sumOfDealerHand = wrapAroundHandValue(sumOfDealerHand)
        print("The Dealer's hand is worth " + str(sumOfDealerHand))
    input(formatter.getInputText("Enter"))

    #Dealer Logic
    #If length of Player's hand = 2
    #   if dealerhand < 5
    #       Dealer Draws Card
    #If length of player's hand = 3, use chart
    #   BANKERS HAND SUM    | 3rd card if player's 3rd card is
    #    0-2                       Any Card
    #    3                           != 8
    #    4                            2-7
    #    5                            4-7
    #    6                            6-7
    #    7 (Stand)                     X
    #    8-9 (Natural Stand)           X
    playerHandLength = len(hand)
    if naturalFlag is False:
        if playerHandLength == 2:
            if sumOfDealerHand < 5:
                dealerHand = dealerDrawsCard(currentDeck, dealerHand)
                sumOfDealerHand = getNewDealerHandValue(dealerHand, sumOfDealerHand)
            elif sumOfDealerHand >= 7:
                print("Dealer got a Natural!")
                print("Dealer stands")
            else:
                print("Dealer Stands")
        else:
            if sumOfDealerHand < sumOfHand :
                match sumOfDealerHand:
                    case 0|1|2:
                        dealerHand = dealerDrawsCard(currentDeck, dealerHand)
                        sumOfDealerHand = getNewDealerHandValue(dealerHand, sumOfDealerHand)
                    case 3:
                        if thirdCardValue < 8:
                            dealerHand = dealerDrawsCard(currentDeck, dealerHand)
                            sumOfDealerHand = getNewDealerHandValue(dealerHand, sumOfDealerHand)
                    case 4:
                        if 2 <= thirdCardValue <= 7:
                            dealerHand = dealerDrawsCard(currentDeck, dealerHand)
                            sumOfDealerHand = getNewDealerHandValue(dealerHand, sumOfDealerHand)
                    case 5:
                        if 4 <= thirdCardValue <= 7:
                            dealerHand = dealerDrawsCard(currentDeck, dealerHand)
                            sumOfDealerHand = getNewDealerHandValue(dealerHand, sumOfDealerHand)
                    case 6:
                        if 6 <= thirdCardValue <= 7:
                            dealerHand = dealerDrawsCard(currentDeck, dealerHand)
                            sumOfDealerHand = getNewDealerHandValue(dealerHand, sumOfDealerHand)
                    case 7:
                        print("Dealer Stands")
                    case 8,9:
                        print("Dealer got a Natural!")
                        print("Dealer stands")
    print("Final Sum of Dealer Hand : " + str(sumOfDealerHand))
    input(formatter.getInputText("Enter"))
    finalBetType = bm.getCurrentBaccaratBetType(characterData['name'])
    if sumOfDealerHand == sumOfHand:
        print("Tie!")
        if finalBetType['Tie Bet']:
            baccarat_tie(characterData)
    else:
        playerHandDifference = differenceFromNine(sumOfHand)
        dealerHandDifference = differenceFromNine(sumOfDealerHand)
        if playerHandDifference < dealerHandDifference:
            print("Player Wins")
            if finalBetType['Player Bet']:
                baccarat_player_win(characterData)
        else:
            print("Bank Wins!")
            if finalBetType['Banker Bet']:
                baccarat_dealer_win(characterData)

def get_bet_type():
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Choose Your Bet Type")
        print("1.) Player")
        print("2.) Banker")
        print("3.) Tie")
        print("4.) Main Menu")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 4:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    return "Player"
                case "2":
                    return "Banker"
                case "3":
                    return "Tie"
                case "4":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def checkSumOfHand(hand):
    sumOfHand = calculateSumOfHand(hand)
    return sumOfHand

def checkDealerSumOfHand(hand):
    dealerSumOfHand = calculateSumOfHand(hand)
    return dealerSumOfHand

def calculateSumOfHand(hand):
    sum = 0
    for x in hand:
        number = x[0:1]
        sum += getNumericValue(number)
    return sum

#Specific Logic For Baccarat
def getNumericValue(value):
    match value:
        case '1':
            return 0
        case 'J':
            return 0
        case 'Q':
            return 0
        case 'K':
            return 0
        case 'A':
            return 2
        case _:
            return int(value)

def wrapAroundHandValue(sumOfHand):
    if sumOfHand > 29:
        print("Your number is 30 or higher. Subtracting 30 to wrap it around.")
        sumOfHand -= 30
    elif sumOfHand > 19:
        print("Your number is 20 or higher. Subtracting 30 to wrap it around.")
        sumOfHand -= 20
    else:
        print("Your number is 10 or higher. Subtracting 10 to wrap it around.")
        sumOfHand -= 10
    return sumOfHand

def dealerDrawsCard(currentDeck,hand):
    card = dm.draw(currentDeck)
    print("Dealer is in range for another card")
    print("Dealer draws a " + dm.getCardName(card))
    hand.append(card)
    return hand

def getNewDealerHandValue(dealerHand, sumOfDealerHand):
    card = dealerHand[2]
    checkDealerThirdCardDeck = [card]
    dealerThirdCardValue = checkSumOfHand(checkDealerThirdCardDeck)
    sumOfDealerHand += dealerThirdCardValue
    if sumOfDealerHand > 9:
        sumOfDealerHand = wrapAroundHandValue(sumOfDealerHand)
    return sumOfDealerHand

def differenceFromNine(inputSum):
    return 9 - inputSum

def baccarat_player_win(characterData):
    formatter.clear()
    result = "You win the Player Hand Payout"
    bm.payOut(characterData,2)
    return result

def baccarat_dealer_win(characterData):
    formatter.clear()
    result = "You win the Dealer Hand Payout"
    bm.payOut(characterData, 2)
    return result

def baccarat_tie(characterData):
    formatter.clear()
    result = "You win the Tie Payout"
    bm.payOut(characterData, 9)
    return result