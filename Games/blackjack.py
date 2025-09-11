import deckmaintenance as dm
import handmaintenance as hm
import monymaintenance as mm
from Characters import charactermaintenance as cm

def blackjackStart(characterData):
    print("Welcome to the Blackjack v0.1")
    print("----------------")
    while 1 != 0:
        print("1. Start Game(Deal In)")
        print("2. Game Information")
        print("3. Main Menu")
        z = input("Enter your choice now!\n")
        z = int(z)
        match z:
            case 1:
                characterData = cm.loadCharacteByName(characterData['Name'])
                currentDeck = dm.restockDeck()
                dealin(currentDeck, characterData)
            case 2:
                printBlackjackGameInfo()
            case 3:
                return

def printBlackjackGameInfo():
    print("The classic game of Blackjack sees you matching up against the house.")
    print("The goal of the game is to get as close to 21 as you can get without going over.")
    print("Winning payout 3:2, Dealer Stands on 17.")
    print("-----------------------------------------")
    print("You start by betting before the cards are dealt.")
    print("After cards are dealt, you can choose to Hit, or Stand")
    print("-Hit - Deal another card")
    print("-Stand - Keep the cards you have.")
    print("After your turn, the dealer will go.")
    print("At the end, whoever is the highest without going over 21 wins!")
    print("-----------------------------------------")
    print("Card Number Values")
    print("Face Cards (J,K,Q) = 10")
    print("Ace = 2 or 11 (You get to choose every time you calculate)")
    input("Press any key to continue...\n")
    return

def dealin(currentDeck, characterData):
    #Set Up
    hand = []
    dealerHand = []

    bet = input("How much do you want to bet? You have " + str(characterData['Credits']) + "\n")
    characterData = mm.setBet(characterData,int(bet))

    for x in range(2):
        card = dm.draw(currentDeck)
        print("You drew a " + dm.getCardName(card))
        hand.append(card)
    sumOfHand = checkSumOfHand(hand)

    for x in range(2):
        card = dm.draw(currentDeck)
        dealerHand.append(card)
    sumOfDealerHand = checkDealerSumOfHand(dealerHand, 1)
    print("\n")

    while sumOfHand <= 21:
        print("Current Commands")
        print("1. Check Table")
        print("2. Draw")
        print("3. Stay")
        print("4. Blackjack Menu")
        command = input("Enter your choice now\n")
        command = int(command)
        match command:
            case 1:
                hm.displayHand(hand)
                checkDealerSumOfHand(dealerHand, 1)
            case 2:
                card = dm.draw(currentDeck)
                hand.append(card)
                print("You drew a " + dm.getCardName(card))
            case 3:
                print("You have chosen to stay. Let's see how you match up.")
                break
            case 4:
                return
        sumOfHand = checkSumOfHand(hand)

    #Instant Lose
    if sumOfHand > 21:
        print("You Lose!")
        characterData = mm.payOut(characterData, 0, 0)
        cm.insertAchievement("Blackjack_Lose", characterData)
        return

    checkDealerSumOfHand(dealerHand, 0)
    #Dealer Ai (Stand at 18)
    while sumOfDealerHand <= 21:
        if sumOfDealerHand >= 18:
            print("The Dealer Stands.")
            break
        else:
            card = dm.draw(currentDeck)
            dealerHand.append(card)
            name = dm.getCardName(card)
            print("The dealer drew a " + name + "(" + card + ")")
            sumOfDealerHand = checkDealerSumOfHand(dealerHand, 2)
    if sumOfDealerHand > 21:
        result = "You win!"
        characterData = mm.payOut(characterData,1,1.5)
        if sumOfHand == 21:
            cm.insertAchievement("Blackjack_21", characterData)
        else:
            cm.insertAchievement("Blackjack_Win", characterData)
    else:
        if sumOfHand < sumOfDealerHand:
            result = "The house wins!"
            characterData = mm.payOut(characterData, 0, 0)
            cm.insertAchievement("Blackjack_Lose", characterData)
        elif sumOfHand > sumOfDealerHand:
            result = "You win!"
            characterData = mm.payOut(characterData, 1, 1.5)
            if sumOfHand == 21:
                cm.insertAchievement("Blackjack_21", characterData)
            else:
                cm.insertAchievement("Blackjack_Win", characterData)
        else:
            result = "It's a draw!"
            characterData = mm.payOut(characterData, -1, 0)
            cm.insertAchievement("Blackjack_Draw", characterData)
    cm.saveCharacter(characterData)
    print(result)
    return result

def calculateSumOfHand(hand, dealerFlag):
    sum = 0
    for x in hand:
        number = x[0:1]
        sum += getNumericValue(number, dealerFlag, sum)
    return sum

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

