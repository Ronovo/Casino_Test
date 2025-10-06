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

def pickHand(communityHand,playerHand):
    resultHand = []
    pickCards = 5
    while pickCards > 0:
        displayCommunityHand = ""
        displayPlayerHand = ""
        displaySelectedHand = ""
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
        for card in resultHand:
            if displaySelectedHand == "":
                displaySelectedHand += card
            else:
                displaySelectedHand += ", " + card

        print("Current Community Hand : " + displayCommunityHand)
        print("Current Player Hand : " + displayPlayerHand)
        print("Currently Selected Hand : " + displaySelectedHand)

        itemOrder = 1
        selectionList = []
        for card in playerHand:
            cardName = dm.getCardName(card)
            print(str(itemOrder) + ".) " + cardName)
            selectionList.append(card)
            itemOrder += 1
        for card in communityHand:
            cardName = dm.getCardName(card)
            print(str(itemOrder) + ".) " + cardName)
            selectionList.append(card)
            itemOrder += 1


        print(str(pickCards) + " cards remaining.")
        selection = input("Pick a card...\n")
        selectedCard = selectionList[(int(selection) - 1)]
        for x in communityHand:
            if selectedCard == x:
                resultHand.append(selectedCard)
                communityHand.remove(selectedCard)
                displayCommunityHand = ""
        if displayCommunityHand != "":
            for x in playerHand:
                if selectedCard == x:
                    resultHand.append(selectedCard)
                    playerHand.remove(selectedCard)
        pickCards -= 1
    return resultHand

def flipCommunityCard(hand, cardIndex):
        card = hand[cardIndex]
        name = dm.getCardName(card)
        print("The dealer flips over a " + name + "(" + card + ")")

def getCardNameByNumber(numericValue):
    """Convert numeric value back to card name for display"""
    match numericValue:
        case 14:
            return "Ace"
        case 13:
            return "King"
        case 12:
            return "Queen"
        case 11:
            return "Jack"
        case 10:
            return "10"
        case _:
            return str(numericValue)

def calculateScoreValue(currentCards):
    #Step 0 : Print the hand
    displayCurrentCards = ""
    for card in currentCards:
        if displayCurrentCards == "":
            displayCurrentCards += card
        else:
            displayCurrentCards += ", " + card

    print("Current Hand to select from : " + displayCurrentCards)

    # Step 1 : Find Highest Value (High Card)
    # Since Suits have no inherent value, we don't care about that. Just number value.
    highCard = ""
    highNumber = 0
    numberList = []
    for card in currentCards:
        value = card[0:1]
        number = dm.getNumericValue(value)
        if number > highNumber:
            highCard = card
            highNumber = number
        #Used for pairing next loop through
        numberList.append(number)
    print("High Card : " + highCard)
    
    # Step 2: Check for pairs, three of a kind, four of a kind, and two pairs
    numberCounts = {}
    for number in numberList:
        if number in numberCounts:
            numberCounts[number] += 1
        else:
            numberCounts[number] = 1
    
    # Find the different types of matches
    pairs = []
    threeOfAKind = []
    fourOfAKind = []
    
    for number, count in numberCounts.items():
        if count == 4:
            fourOfAKind.append(number)
        elif count == 3:
            threeOfAKind.append(number)
        elif count == 2:
            pairs.append(number)
    
    # Determine and display the highest ranking hand type
    if fourOfAKind:
        # Four of a kind beats everything
        highestFour = max(fourOfAKind)
        print("Four of a Kind: " + getCardNameByNumber(highestFour))
    elif threeOfAKind and pairs:
        # Full House: 3 of a kind + 2 of a kind beats everything except four of a kind
        highestThree = max(threeOfAKind)
        highestPair = max(pairs)
        print("Full House: " + getCardNameByNumber(highestThree) + "s over " + getCardNameByNumber(highestPair) + "s")
    elif threeOfAKind:
        # Three of a kind is better than two pairs or pairs
        highestThree = max(threeOfAKind)
        print("Three of a Kind: " + getCardNameByNumber(highestThree))
    elif len(pairs) >= 2:
        # Two pairs beats single pair
        pairs.sort(reverse=True)  # Sort in descending order
        print("Two Pairs: " + getCardNameByNumber(pairs[0]) + " and " + getCardNameByNumber(pairs[1]))
    elif len(pairs) == 1:
        # Single pair is the lowest ranking
        print("Pair: " + getCardNameByNumber(pairs[0]))

    # Step 3 Check for straights (5 consecutive cards)
    uniqueNumbers = sorted(list(set(numberList)))  # Remove duplicates and sort
    straightFound = False
    straightHigh = 0
    
    # Check for regular straight (including Ace-high straight)
    for i in range(len(uniqueNumbers) - 4):
        if (uniqueNumbers[i+1] == uniqueNumbers[i] + 1 and
            uniqueNumbers[i+2] == uniqueNumbers[i] + 2 and
            uniqueNumbers[i+3] == uniqueNumbers[i] + 3 and
            uniqueNumbers[i+4] == uniqueNumbers[i] + 4):
            straightFound = True
            straightHigh = uniqueNumbers[i+4]
    
    # Check for Ace-low straight (A, 2, 3, 4, 5)
    # In this case, Ace (14) acts as 1
    if not straightFound and 14 in uniqueNumbers:  # If Ace is present
        aceLowNumbers = [1 if x == 14 else x for x in uniqueNumbers]  # Convert Ace to 1
        aceLowNumbers = sorted(list(set(aceLowNumbers)))  # Remove duplicates and sort
        
        for i in range(len(aceLowNumbers) - 4):
            if (aceLowNumbers[i+1] == aceLowNumbers[i] + 1 and
                aceLowNumbers[i+2] == aceLowNumbers[i] + 2 and
                aceLowNumbers[i+3] == aceLowNumbers[i] + 3 and
                aceLowNumbers[i+4] == aceLowNumbers[i] + 4):
                if aceLowNumbers[i] == 1:  # Ace-low straight
                    straightFound = True
                    straightHigh = 5  # 5-high straight
    
    if straightFound:
        print("Straight: " + getCardNameByNumber(straightHigh) + " high")

    # Step 4 : Sort into Suits
    hearts = []
    clubs = []
    spades = []
    diamonds = []
    for card in currentCards:
        suit = dm.getSuit(card)
        match(suit):
            case "Spades":
                spades.append(card)
            case "Hearts":
                hearts.append(card)
            case "Clubs":
                clubs.append(card)
            case "Diamonds":
                diamonds.append(card)


    suitsList = [spades,hearts,clubs,diamonds]
    suitNames = ["Spades", "Hearts", "Clubs", "Diamonds"]
    
    for i, selectedSuit in enumerate(suitsList):
        # Step 5: Check 5-card suit win conditions
        if len(selectedSuit) == 5:
            # Get numeric values for the suit
            suitNumbers = []
            for card in selectedSuit:
                number = dm.getNumericValue(card[0:1])
                suitNumbers.append(number)
            
            suitNumbers.sort()  # Sort for easier checking
            
            # Check for Royal Flush (10, J, Q, K, A in same suit)
            if suitNumbers == [10, 11, 12, 13, 14]:
                print("Royal Flush in " + suitNames[i] + "!")
                return  # Royal flush is the highest, no need to check further
            
            # Check for Straight Flush (5 consecutive cards in same suit)
            straightFlushFound = False
            
            # Check regular straight flush
            for j in range(len(suitNumbers) - 4):
                if (suitNumbers[j+1] == suitNumbers[j] + 1 and
                    suitNumbers[j+2] == suitNumbers[j] + 2 and
                    suitNumbers[j+3] == suitNumbers[j] + 3 and
                    suitNumbers[j+4] == suitNumbers[j] + 4):
                    straightFlushFound = True
                    print("Straight Flush in " + suitNames[i] + ": " + getCardNameByNumber(suitNumbers[j+4]) + " high")
                    return  # Straight flush found, no need to check further
            
            # Check for Ace-low straight flush (A, 2, 3, 4, 5)
            if not straightFlushFound and 14 in suitNumbers:
                aceLowSuit = [1 if x == 14 else x for x in suitNumbers]
                aceLowSuit.sort()
                
                if aceLowSuit == [1, 2, 3, 4, 5]:
                    print("Straight Flush in " + suitNames[i] + ": 5 high (Ace-low)")
                    return  # Ace-low straight flush found
            
            # If no royal flush or straight flush, it's a regular flush
            if not straightFlushFound:
                print("Flush in " + suitNames[i])
                return  # Flush found, no need to check other suits