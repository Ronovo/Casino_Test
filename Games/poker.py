from Characters import  charactermaintenance as cm
import deckmaintenance as dm

def pokerStart(characterData):
    print("Welcome to the Texas Hold'em v0.0")
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
                printPokerGameInfo()
            case 3:
                return

def printPokerGameInfo():
    print("The High Stakes game of Texas Hold'em squares you off against 4 other players")
    print("Score List coming soon")

def dealin(currentDeck, characterData):
    # Set Up
    hand = []
    dealerHand = []
    communityHand = []

    for x in range(2):
        card = dm.draw(currentDeck)
        print("You drew a " + dm.getCardName(card))
        hand.append(card)

    for x in range(2):
        card = dm.draw(currentDeck)
        dealerHand.append(card)

    for x in range(5):
        card = dm.draw(currentDeck)
        communityHand.append(card)

    flipCommunityCard(communityHand,0)
    flipCommunityCard(communityHand,1)
    flipCommunityCard(communityHand, 2)
    flipCommunityCard(communityHand, 3)
    flipCommunityCard(communityHand, 4)

    resultHand = pickHand(communityHand,hand)
    result = ""
    for x in resultHand:
        if result == "":
            result += x
        else:
            result += ", " + x
    print("Your selected hand is : " + result)
    input("Press any key to continue...\n")

#TODO : Make 10 show as 10(Suit) instead of 1(suit)
def pickHand(communityHand,playerHand):
    resultHand = []
    pickCards = 5
    while pickCards > 0:
        displayCommunityHand = ""
        displayPlayerHand = ""
        for card in communityHand:
            if displayCommunityHand == "":
                displayCommunityHand += card
            else:
                displayCommunityHand += ", " + card

        for card in playerHand:
            if displayPlayerHand == "":
                displayPlayerHand += card
            else:
                displayPlayerHand += ", " + card

        print("Current Community Hand : " + displayCommunityHand)
        print("Current Player Hand : " + displayPlayerHand)

        print(str(pickCards) + " cards remaining.")
        selection = input("Pick a card...\n")
        for x in communityHand:
            if selection == x:
                resultHand.append(selection)
                communityHand.remove(selection)
                displayCommunityHand = ""
        if displayCommunityHand != "":
            for x in playerHand:
                if selection == x:
                    resultHand.append(selection)
                    playerHand.remove(selection)
                    displayPlayerHand = ""
        pickCards -= 1
    return resultHand


        #print community hand
        #print player hand
        #have player pick card
        #Remove card from hand
    return resultHand


def flipCommunityCard(hand, cardIndex):
        card = hand[cardIndex]
        name = dm.getCardName(card)
        print("The dealer flips over a " + name + "(" + card + ")")

'''
Logic:
Deal 2 cards
Lay 3 cards in middle
Flip 1 card
Bet Round 1
flip 2 card
Bet ROund 2
Flip 3rd card
Build hand
resolve
'''