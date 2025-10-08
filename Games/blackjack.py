import formatter
from Helpers import handmaintenance as hm, deckmaintenance as dm
from DAL import money_maintenance as mm
from DAL import achievement_maintenance as am, character_maintenance as cm, blackjack_maintenance as bjs


def blackjackStart(characterName):
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Welcome to the Blackjack v2.0")
        print("1.) Start Game(Deal In)")
        print("2.) Game Information")
        print("3.) Main Menu")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 3:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    characterData = cm.load_character_by_name(characterName)
                    currentDeck = dm.restockDeck()
                    dealin(currentDeck, characterData)
                case "2":
                    printBlackjackGameInfo()
                case "3":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def printBlackjackGameInfo():
    #Page 1
    print("The classic game of Blackjack sees you matching up against the house.")
    print("The goal of the game is to get as close to 21 as you can get without going over.")
    print("Winning payout 3:2, Dealer Stands on 17.")
    input(formatter.getInputText("Enter"))
    print("You start by betting before the cards are dealt.")
    print("After cards are dealt, you can choose to Hit, or Stand")
    print("-Hit - Deal another card")
    print("-Stand - Keep the cards you have.")
    print("After your turn, the dealer will go.")
    print("At the end, whoever is the highest without going over 21 wins!")
    input(formatter.getInputText("Enter"))
    print("Card Number Values")
    print("Face Cards (J,K,Q) = 10")
    print("Ace = 2 or 11 (You get to choose every time you calculate)")
    input(formatter.getInputText("Enter Menu"))
    return

def dealin(currentDeck, characterData):
    #Set Up
    hand = []
    dealerHand = []

    if characterData['credits'] == 0 :
        print("You have no money! Go back to the menu, bum!")
        input(formatter.getInputText("Enter"))
        return

    # Create a new Blackjack entry for the character if this is the first time
    if characterData['blackjack_id'] == 0:
        characterData = bjs.create_blackjack_connection(characterData)
    bet = input("How much do you want to bet? You have " + str(characterData['credits']) + "\n")
    bet = mm.checkBetNumber(bet)
    if bet == 0:
        bet = 1
        print("Invalid Entry, defaulting to 1")
    characterData = mm.setBet(characterData,int(bet),'BJ')

    for x in range(2):
        card = dm.draw(currentDeck)
        print("You drew a " + dm.getCardName(card))
        hand.append(card)
    sumOfHand = checkSumOfHand(hand)
    input(formatter.getInputText("Enter"))

    for x in range(2):
        card = dm.draw(currentDeck)
        dealerHand.append(card)
    sumOfDealerHand = checkDealerSumOfHand(dealerHand, 1)
    input(formatter.getInputText("Enter"))

    while sumOfHand <= 21:
        formatter.drawMenuTopper("Current Commands")
        print("1. Draw")
        print("2. Stay")
        print("3. Blackjack Menu(Lose Bet)")
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
                    break
                case "3":
                    mm.setBet(characterData,0,"BJ")
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))
        input(formatter.getInputText("Enter"))
        formatter.clear()
        hm.displayHand(hand)
        sumOfHand = checkSumOfHand(hand)
        checkDealerSumOfHand(dealerHand, 1)

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
        result = blackjack_win(characterData, sumOfHand)
    else:
        if sumOfHand < sumOfDealerHand:
            result = blackjack_lose(characterData)
        elif sumOfHand > sumOfDealerHand:
           result = blackjack_win(characterData, sumOfHand)
        else:
           result = blackjack_draw(characterData)
    print(result)
    input(formatter.getInputText("Enter"))
    return result

def calculateSumOfHand(hand, dealerFlag):
    sum = 0
    for x in hand:
        number = x[0:1]
        sum += getNumericValue(number, dealerFlag, sum)
    return sum

#Specific Logic For BlackJack
def getNumericValue(value, dealerFlag, dealerHandValue):
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
    print("Your hand is currently worth " + str(sumOfHand))
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

def blackjack_win(characterData, sumOfHand):
    formatter.clear()
    result = "You Win!"
    characterData = mm.payOut(characterData, 1, 1.5, "BJ")
    bjs.update_blackjack_wins(characterData['name'])
    if sumOfHand == 21:
        result = "You Win with 21!"
        am.insert_achievement(characterData["name"], "Blackjack_21")
    else:
        am.insert_achievement(characterData["name"], "Blackjack_Win")
    return result

def blackjack_lose(characterData):
    formatter.clear()
    result = "The House Wins!"
    characterData = mm.payOut(characterData, 0, 0, "BJ")
    bjs.update_blackjack_losses(characterData['name'])
    am.insert_achievement(characterData["name"], "Blackjack_Lose")
    return result

def blackjack_draw(characterData):
    formatter.clear()
    result = "It's a draw! All bets returned"
    characterData = mm.payOut(characterData, -1, 0, "BJ")
    bjs.update_blackjack_draws(characterData['name'])
    am.insert_achievement(characterData["name"], "Blackjack_Draw")
    return result

