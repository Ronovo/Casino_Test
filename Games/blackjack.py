import formatter
from Helpers import deckmaintenance as dm
from DAL import money_maintenance as mm
from DAL import achievement_maintenance as am, character_maintenance as cm, blackjack_maintenance as bjs

# TODO : Balance Difficulty (Fix Paytable, only use current table on very hard)
def blackjackStart(characterName):
    while 1 > 0:
        # Check if player has any chips for game over state
        characterData = cm.load_character_by_name(characterName)
        chips = mm.get_chips_by_character_id(characterData["id"])
        chipTotal = mm.get_chips_total(chips)

        if chipTotal["Total"] == 0:
            return "GAME_OVER"
        formatter.clear()
        formatter.drawMenuTopper("Welcome to the Blackjack v2.2")
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
                    printBlackjackGameInfo()
                case "3":
                    printPayTableBlackjack()
                case "4":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def printBlackjackGameInfo():
    #Page 1
    print("The classic game of Blackjack sees you matching up against the house.")
    print("The goal of the game is to get as close to 21 as you can get without going over.")
    print("Dealer Stands on 17.")
    print("Deck resets every game. Card counting does not work")
    input(formatter.getInputText("Enter"))
    print("You start by betting before the cards are dealt.")
    print("After cards are dealt, you can choose to Hit, or Stand")
    print("-Hit - Deal another card")
    print("-Stand - Keep the cards you have")
    print("-Split - if you have a pair, you can treat the cards like 2 hands, with an additional bet")
    print("After your turn, the dealer will go.")
    print("At the end, whoever is the highest without going over 21 wins!")
    input(formatter.getInputText("Enter"))
    print("Card Number Values")
    print("Face Cards (J,K,Q) = 10")
    print("Ace = 2 or 11 (You get to choose every time you calculate)")
    input(formatter.getInputText("Enter Menu"))
    return
def printPayTableBlackjack():
    formatter.clear()
    formatter.drawMenuTopper("Blackjack Pay Table")
    print("Double Down = 2 x Winnings")
    print("Win = 1:1")
    print("21 (Not Blackjack) = 2:1")
    print("Blackjack = 3:1")
    input(formatter.getInputText("Enter Menu"))

def dealin(currentDeck, characterData):
    #Set Up
    hand = []
    dealerHand = []

    # TODO : If current bet is 0, return
    # Create a new Blackjack entry for the character if this is the first time
    if characterData['blackjack_id'] == 0:
        characterData = bjs.create_blackjack_connection(characterData)
    selectedChips = mm.get_bet_chips_total(characterData["name"])
    cm.remove_player_chips(characterData["name"], selectedChips)
    totalBetChips = mm.get_chips_total(selectedChips)
    mm.setChipBet(characterData,totalBetChips,'BJ')

    formatter.clear()
    for x in range(2):
        card = dm.draw(currentDeck)
        print("You drew a " + dm.getCardName(card))
        hand.append(card)
    input(formatter.getInputText("Enter"))
    sumOfHand = checkSumOfHand(hand)

    if sumOfHand == 21:
        result = blackjack_win(characterData,sumOfHand,True,False,hand)
        print(result)
        input(formatter.getInputText("Enter"))
        formatter.clear()
        return result

    for x in range(2):
        card = dm.draw(currentDeck)
        dealerHand.append(card)
    sumOfDealerHand = checkDealerSumOfHand(dealerHand, 1)
    input(formatter.getInputText("Enter"))

    doubleDownOption = "3"
    pairs = checkPairs(hand)
    double_down_flag = False
    while sumOfHand <= 21:
        formatter.clear()
        formatter.drawMenuTopper("Current Commands | Credits Bet : " + str(totalBetChips["Total"]) + " credits")
        print("Hand:")
        print(hand)
        print("Sum of your hand : " + str(sumOfHand))
        formatter.drawMenuLine()
        print("1. Draw")
        print("2. Stay")
        print(doubleDownOption + ". Double Down")
        print("4. Walk Away(Lose Bet)")
        if pairs:
            print("5. Bonus Action - Split Pairs (2 chances, 2x Bet)")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 4:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    card = dm.draw(currentDeck)
                    hand.append(card)
                    print("You drew a " + dm.getCardName(card))
                case "2":
                    print("You have chosen to stay. Let's see how you match up.")
                    break
                case "3":
                    if doubleDownOption != "X":
                        double_down_flag = True
                        cm.remove_player_chips(characterData["name"], selectedChips)
                        for x in selectedChips:
                            selectedChips[x] *= 2
                        totalBetChips = mm.get_chips_total(selectedChips)
                        mm.setChipBet(characterData, totalBetChips, 'BJ')
                        print("It has been doubled")
                    else:
                        print("That option is no longer valid")
                case "4":
                    chips = {"White" : 0, "Red" : 0, "Green" : 0, "Black" : 0, "Purple" : 0, "Orange" : 0, "Total" : 0}
                    mm.setChipBet(characterData,chips,"BJ")
                    return
                case "5":
                    print("Split logic coming soon")
                    #split(hand, currentDeck, totalBetChips, characterData)
                    #TODO : Split Achievement
                    #return
                    pass
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))
        input(formatter.getInputText("Enter"))
        formatter.clear()
        doubleDownOption = "X"
        sumOfHand = checkSumOfHand(hand)
        checkDealerSumOfHand(dealerHand, 1)
    #TODO : Add Split Achievement

    #Instant Lose
    if sumOfHand > 21:
        result = blackjack_lose(characterData)
        print(result)
        input(formatter.getInputText("Enter"))
        formatter.clear()
        return result

    checkDealerSumOfHand(dealerHand, 0)
    #Dealer Ai (Stand at 18)
    while sumOfDealerHand <= 21:
        if sumOfDealerHand >= 18:
            print("The Dealer Stands.")
            input(formatter.getInputText("Enter"))
            break
        else:
            card = dm.draw(currentDeck)
            dealerHand.append(card)
            name = dm.getCardName(card)
            print("The dealer drew a " + name + "(" + card + ")")
            sumOfDealerHand = checkDealerSumOfHand(dealerHand, 2)
            input(formatter.getInputText("Enter"))

    formatter.clear()
    formatter.drawMenuTopper("Final Totals")
    print("Your Hand Total = " + str(sumOfHand))
    print("Dealer Hand Total = " + str(sumOfDealerHand))
    formatter.drawMenuLine()
    if sumOfDealerHand > 21:
        result = blackjack_win(characterData, sumOfHand, False,double_down_flag, hand)
    else:
        if sumOfHand < sumOfDealerHand:
            result = blackjack_lose(characterData)
        elif sumOfHand > sumOfDealerHand:
           result = blackjack_win(characterData, sumOfHand, False,double_down_flag, hand)
        else:
           result = blackjack_draw(characterData)
    #Reset the Blackjack Chips count
    chips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0, "Total": 0}
    mm.setChipBet(characterData, chips, "BJ")
    print(result)
    input(formatter.getInputText("Enter"))
    return result

def checkPairs(hand):
    lastNumber = ""
    for card in hand:
        number = card[0:1]
        if lastNumber == number:
            return True
        lastNumber = number
    return False

'''
def split(hand, currentDeck, totalBetChips, characterData):
    print("You Split Your Cards!")
    print("Start of Deck 1:")
    card1 = dm.draw(currentDeck)
    print("You drew a " + dm.getCardName(card1))
    hand1 = [hand[0],card1]
    sumHand1 = calculateSumOfHand(hand1, False)
    # Loop through hand1 with play menu
    while sumHand1 < 21:
        hand1 = play_menu(currentDeck, hand1, totalBetChips, characterData,1)
        sumHand1 = calculateSumOfHand(hand1, False)
    # Payout Deck 1
    if sumHand1 <= 21:
        result1 = blackjack_win(characterData, sumHand1, False, hand1, False)
    else:
        result1 = blackjack_lose(characterData, False)
    print(result1)
    input(formatter.getInputText("Enter"))
    #Draw 2nd card
    print("Start of Deck 1:")
    card2 = dm.draw(currentDeck)
    print("You drew a " + dm.getCardName(card2))
    hand2 = [hand[0], card2]
    sumHand2 = calculateSumOfHand(hand2,False)
    #Loop through hand2 with play menu
    while sumHand2 < 21:
        hand2 = play_menu(currentDeck, hand2, totalBetChips, characterData,2)
        sumHand2 = calculateSumOfHand(hand2,False)
    #Payout Deck2
    if sumHand2 <= 21:
        result2 = blackjack_win(characterData, sumHand2, False, hand2, False)
    else:
        result2 = blackjack_lose(characterData, False)
    print(result2)

def play_menu(currentDeck,hand, totalBetChips, characterData, handNumber):
    while 1 != 0:
        doubleDownOptionPlayMenu = "3"
        formatter.drawMenuTopper("Current Commands (Hand " + str(handNumber) + ")")
        print("Hand : ")
        print(hand)
        print("1. Draw")
        print("2. Stay")
        print(doubleDownOptionPlayMenu + ". Double Down")
        print("4. Walk Away(Lose Bet)")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 3:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    card = dm.draw(currentDeck)
                    hand.append(card)
                    print("You drew a " + dm.getCardName(card))
                case "2":
                    print("You have chosen to stay. Let's see how you match up.")
                    return hand
                case "3":
                    if doubleDownOptionPlayMenu != "X":
                        for x in totalBetChips:
                            totalBetChips[x] *= 2
                        doubleDownOptionPlayMenu = "X"
                    else:
                        print("That option is no longer valid")
                        input(formatter.getInputText("Enter"))
                case "4":
                    chips = {"White": 0, "Red": 0, "Green": 0, "Black": 0, "Purple": 0, "Orange": 0, "Total": 0}
                    mm.setChipBet(characterData, chips, "BJ")
                    return hand
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))
        input(formatter.getInputText("Enter"))
        formatter.clear()
'''

def calculateSumOfHand(hand, dealerFlag):
    sum = 0
    for x in hand:
        number = x[0:1]
        sum += getNumericValue(number, dealerFlag, sum, hand)
    return sum

#Specific Logic For BlackJack
def getNumericValue(value, dealerFlag, dealerHandValue, hand):
    match value:
        case '1':
            return 10
        case 'J':
            return 10
        case 'Q':
            return 10
        case 'K':
            return 10
        case 'A':
            if dealerFlag:
                if (dealerHandValue + 11) > 22:
                    return 2
                else:
                    return 11
            else:
                print("Hand: ")
                print(hand)
                z = input('Do you want the Ace to count for 11 or 2 in the calculation? Default = 2\n')
                if z == "2":
                    return 2
                elif z == "11":
                    return 11
                else:
                    return 2
        case _:
            return int(value)

def checkSumOfHand(hand):
    sumOfHand = calculateSumOfHand(hand, False)
    print("Your hand is currently worth " + str(sumOfHand) + "\n")
    return sumOfHand

def checkDealerSumOfHand(hand, cardIndex):
    dealer = calculateSumOfHand(hand, True)
    if cardIndex == 0:
        card = hand[0]
        name0 = dm.getCardName(card)
        print("The dealer flips over a " + name0 + "(" + card + ")")
        card = hand[1]
        name1 = dm.getCardName(card)
        print("The dealer also had a " + name1 + "(" + card + ")" + " face up")
        print("The Dealer's hand is worth " + str(dealer))
    if cardIndex == 1:
        card = hand[cardIndex]
        name = dm.getCardName(card)
        print("The Dealer has 2 cards, with a " + name + "(" + card + ")" + " face up.")
    if cardIndex == 2:
        print("The Dealer's hand is worth " + str(dealer))
    return dealer

def blackjack_win(characterData, sumOfHand, blackjackCheck, double_down_flag, hand=None, winCount = True):
    formatter.clear()
    result = "You Win!"

    #Flag is only false if it is a split, so that it does not count to wins
    #TODO : Count Splits
    if winCount:
        bjs.update_blackjack_wins(characterData['name'])
        am.insert_achievement(characterData["name"], "Blackjack_Win")
    if sumOfHand == 21:
        winType = 2
        if blackjackCheck:
            black_jack_flag = checkHandForBlackjack(hand)
            if black_jack_flag:
                winType = 3
        bjs.payOut(characterData, winType, double_down_flag)
        if winCount:
            am.insert_achievement(characterData["name"], "Blackjack_21")
    else :
        bjs.payOut(characterData, 1, double_down_flag)
    return result

def blackjack_lose(characterData, loseCount=True):
    result = "The House Wins!"
    if loseCount:
        bjs.update_blackjack_losses(characterData['name'])
        am.insert_achievement(characterData["name"], "Blackjack_Lose")
    return result

def blackjack_draw(characterData):
    formatter.clear()
    result = "It's a draw! All bets returned"
    bjs.payOut(characterData, -1,False)
    bjs.update_blackjack_draws(characterData['name'])
    am.insert_achievement(characterData["name"], "Blackjack_Draw")
    return result

def checkHandForBlackjack(hand):
    black_jack_present = False
    for x in hand:
        number = x[0:1]
        suit = x[1:2]
        if number == "J":
            if suit == "C" or suit == "S":
                black_jack_present = True
    return black_jack_present
