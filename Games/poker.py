import formatter
from Helpers import deckmaintenance as dm
from DAL import character_maintenance as cm


def pokerStart(characterName):
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Welcome to the Ultimate Texas Hold'em v0.6.9")
        print("1.) Start Game(Deal In)")
        print("2.) Game Information")
        print("3.) Betting Information")
        print("4.) Pay Tables")
        print("5.) Main Menu")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 5:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    characterData = cm.load_character_by_name(characterName)
                    currentDeck = dm.restockDeck()
                    dealin(currentDeck, characterData)
                case "2":
                    printPokerGameInfo()
                case "3":
                    printBettingInformation()
                case "4":
                    printPaytables()
                case "5":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def printPokerGameInfo():
    print("The High Stakes game of Ultimate Texas Hold'em squares you off against the dealer")
    print("The one with the highest 'Score Value' wins")
    print("Minimum Bet : 1 Credit Ante + 1 Credit Blind = 2 credit total")
    print("***High Roller Table Coming Soon***")
    input(formatter.getInputText("Enter"))
    formatter.drawMenuTopper("SCORE VALUE LIST (Ranked Lowest to Highest)")
    print("1 = High Card Value Only")
    print("2 = 2 of a Kind (Pair)")
    print("3 = 2 Pair (2 x 2 cards)")
    print("4 = 3 of a kind (3-Card)")
    print("5 = Straight (5 cards, any suit, in a row)")
    print("6 = Flush (5 cards in a suit, no order)")
    print("7 = Full House (3 of a kind + Pair)")
    print("8 = 4 of a Kind (4-Card)")
    print("9 = Straight Flush (5 cards in a suit, in order)")
    print("10 = Royal Flush (10, Jack, Queen, King, and Aces in a suit)")
    input(formatter.getInputText("Enter Menu"))

def printBettingInformation():
    #Page 1
    print("The betting style is based on the rules of 'Ultimate Texas Hold'em'")
    print("This is a style maximized for a 1v1 Showdown between you and the dealer")
    print("Minimum Bet : 1 Credit Ante + 1 Credit Blind = 2 credit total")
    print("***High Roller Table Coming Soon***")
    input(formatter.getInputText("Enter"))
    formatter.drawMenuTopper("First round of betting: Ante + Blind")
    print("Minimum Bet * 2, since you are always the blind")
    input(formatter.getInputText("Enter Page"))
    formatter.clear()
    #Page 2
    formatter.drawMenuTopper("Bonus Bets")
    formatter.drawMenuTopper("OPTIONAL - 'The Trips Bet'")
    print("Done during the first round, before you get your cards")
    print("Pays out if you score a 3 of a kind or higher(Score Value 5)")
    print("See Game Information for Score Values")
    print("See Pay Tables for payouts.")
    input(formatter.getInputText("Enter"))
    formatter.drawMenuTopper("OPTIONAL - Ultimate Pairs Bonus")
    print("Done during the first round, before you get your cards")
    print("Pays out the higher the pair in your starting hand")
    print("Lost if you don't.")
    print("See Pay Tables for payouts.")
    input(formatter.getInputText("Enter Page"))
    formatter.clear()
    #Page 3
    formatter.drawMenuTopper("Second Round of betting: The Flop")
    print("First three community cards are shown")
    print("You can choose to not bet(Check) or raise(3-4 credits minimum(3-4 * ante))")
    input(formatter.getInputText("Enter"))
    formatter.drawMenuTopper("Third Round of betting: The Turn and River")
    print("Last two community cards are shown")
    print("You can choose to not bet(Check) or raise(2 credits minimum(2 * ante))")
    print("You can also choose to Fold, and lose your ante. This exempts you from the showdown")
    input(formatter.getInputText("Enter Page"))
    formatter.clear()
    #Page 4
    formatter.drawMenuTopper("Reveal and Payout : The Showdown")
    print("Dealer reveals its hand. Outcomes based on score values of best hands possible.")
    print("\nBonus Betting : Trips Bonus and Ultimate Pairs Bonus")
    print("These are independent from the ante + blind. You can win even if you lose the hand.")
    print("Trip bonus - if your hand's score value > 5, you win a payout based on modifier.")
    print("Ultimate Pairs Bonus - if you had pairs in your hand, you win a payout based on modifier.")
    print("See Pay tables on Poker Menu for more information")
    input(formatter.getInputText("Enter Menu"))

def printPaytables():
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Pay Tables")
        print("1.) Winning Calculation Formula")
        print("2.) Ante and Play Bets")
        print("3.) Blind Bonus")
        print("4.) Trips Bonus")
        print("5.) Ultimate Pairs Bonus")
        print("6.) Poker Menu")
        menuInput = input(formatter.getInputText("Choice"))
        if menuInput.isnumeric():
            formatter.clear()
            if 0 > int(menuInput) >= 3:
                input(formatter.getInputText("Wrong Number"))
            match menuInput:
                case "1":
                    formatter.drawMenuTopper("Calculating Winnings")
                    print("Ante - 1:1")
                    print("Play - 1:1")
                    print("Blind - x if win, 1:1 if lost")
                    print("'Trips' Bet - x regardless of win")
                    print("'Pairs' Bet - x regardless of win")
                    formatter.drawMenuTopper("Loss")
                    print("Loss = ante + play + blind")
                    formatter.drawMenuTopper("Win")
                    print("Win = ante + play + (blind * x)")
                    formatter.drawMenuTopper("Bonus")
                    print("Bonus = (Trips * x) + (Pairs * x)")
                    formatter.drawMenuTopper("Final Total")
                    print("total = (Win/Loss) + Bonus")
                    formatter.drawMenuLine()
                    input(formatter.getInputText("Enter Menu"))
                case "2":
                    formatter.drawMenuTopper("Ante and Play Bets")
                    print("These pay out at a 1:1 scale")
                    print("The Ante is your initial bet.")
                    print("The Play Bet is all the money you raised on the Ante.")
                    print("*Push if Draw*")
                    print("*Win if Win*")
                    print("*Lose if Lose*")
                    input(formatter.getInputText("Enter Menu"))
                case "3":
                    formatter.drawMenuTopper("BLIND PAYOUT (Straight or better)")
                    print("Royal Flush = 500:1")
                    print("Straight Flush = 50:1")
                    print("Four of a Kind = 10:1")
                    print("Full House = 3:1")
                    print("Flush = 3:2")
                    print("Straight = 1:1")
                    print("Score Value < 5 - push")
                    print("Loss - Lose bet")
                    input(formatter.getInputText("Enter Menu"))
                case "4":
                    formatter.drawMenuTopper("TRIPS Payout (3 of a kind or better)")
                    print("Royal Flush = 50:1")
                    print("Straight Flush = 40:1")
                    print("Four of a Kind = 30:1")
                    print("Full House = 8:1")
                    print("Flush = 6:1")
                    print("Straight = 5:1")
                    print("3 of a Kind = 3:1")
                    print("Score Value < 4 - Lose Bet")
                    input(formatter.getInputText("Enter Menu"))
                case "5":
                    formatter.drawMenuTopper("ULTIMATE PAIRS BONUS Payout (Starting Hand Pair)")
                    print("Pair of Aces = 25:1")
                    print("Pair of Kings = 10:1")
                    print("Pair of Queens = 8:1")
                    print("Pair of Jacks = 6:1")
                    print("Pair of 10s = 5:1")
                    print("Pair of number cards < 10 = 3:1")
                    print("All others- Lose Bet")
                    input(formatter.getInputText("Enter Menu"))
                case "6":
                    return
                case _:
                    input(formatter.getInputText("NonNumber"))
        else:
            input(formatter.getInputText("NonNumber"))

def dealin(currentDeck, characterData):
    # Set Up
    # The "Pocket" (Player's Hand)
    hand = []
    # Dealer's Hand (Won't be shown until reveal)
    dealerHand = []
    # 5 cards in the middle ("Flop" + 2 rounds)
    communityHand = []

    #Deal to Player
    for x in range(2):
        card = dm.draw(currentDeck)
        print("You drew a " + dm.getCardName(card))
        hand.append(card)

    #Deal to Dealer
    for x in range(2):
        card = dm.draw(currentDeck)
        dealerHand.append(card)

    #Deal out the community cards (They are not displayed at first)
    for x in range(5):
        card = dm.draw(currentDeck)
        communityHand.append(card)

    #Betting Round 1 Goes Here. Minimum bet
    input("Press any key to flip the flop(first 3 cards)...\n")
    flipCommunityCard(communityHand,0)
    flipCommunityCard(communityHand,1)
    flipCommunityCard(communityHand, 2)

    # Betting Round 2 Goes Here.
    input("Press any key to flip the next card...\n")
    flipCommunityCard(communityHand, 3)

    #Betting Round 3 Goes Here
    input("Press any key to flip the next card...\n")
    flipCommunityCard(communityHand, 4)

    #Showdown betting before reveal goes here
    input("Press any key to choose your hand..\n")

    #Pick your "hand" to show from the community and your "pocket"
    resultHand = pickHand(communityHand,hand)
    result = getStringValueOfHand(resultHand)
    print("Your selected hand is : " + result)
    scoreValue = calculateScoreValue(resultHand, False)
    typeOfHand = decodeScoreValue(scoreValue)
    print("Your score value for this hand is " + str(scoreValue))
    print("Your hand type is : " + typeOfHand)
    input("Press any key to continue...\n")

    dealerChoice = communityHand + dealerHand
    dealerHand = findBestHand(dealerChoice)
    dealerResult = getCardNameByNumber(dealerHand)
    print("The Dealer's hand is : " + dealerResult)
    dealerScoreValue = calculateScoreValue(dealerHand,False)
    dealerTypeOfHand = decodeScoreValue(dealerScoreValue)
    print("The dealer's score value for this hand is " + str(dealerScoreValue))
    print("The dealer's hand type is : " + dealerTypeOfHand)
    input("Press any key to continue...\n")

    if scoreValue > dealerScoreValue:
        print("You win!")
    elif scoreValue < dealerScoreValue:
        print("You lose!")
    else:
        print("It's a tie!")
    input("Press any key to continue...\n")
    

def pickHand(communityHand,playerHand):
    resultHand = []
    #Create Work versions of the hands, not references
    communityHandWork = list(communityHand)
    playerHandWork = list(playerHand)
    pickCards = 5
    while pickCards > 0:
        displayCommunityHand = ""
        displayPlayerHand = ""
        displaySelectedHand = ""
        for card in communityHandWork:
            if displayCommunityHand == "":
                displayCommunityHand += card
            else:
                displayCommunityHand += ", " + card
        for card in playerHandWork:
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
        for card in playerHandWork:
            cardName = dm.getCardName(card)
            print(str(itemOrder) + ".) " + cardName)
            selectionList.append(card)
            itemOrder += 1
        for card in communityHandWork:
            cardName = dm.getCardName(card)
            print(str(itemOrder) + ".) " + cardName)
            selectionList.append(card)
            itemOrder += 1
        print(str(itemOrder) + ".) Calculate Best Combo")


        print(str(pickCards) + " cards remaining.")
        selection = input("Pick a card...\n")
        if int(selection) == itemOrder:
            calculateScoreValue(selectionList)
            input("Press any key to continue...")
        else:
            selectedCard = selectionList[(int(selection) - 1)]
            for x in communityHandWork:
                if selectedCard == x:
                    resultHand.append(selectedCard)
                    communityHandWork.remove(selectedCard)
                    displayCommunityHand = ""
            if displayCommunityHand != "":
                for x in playerHandWork:
                    if selectedCard == x:
                        resultHand.append(selectedCard)
                        playerHandWork.remove(selectedCard)
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

def calculateScoreValue(currentCards, display = True):
    """
    Method with the meat of the poker logic. Returns the highest rank of cards in your hand
    Accepts any size array of cards.
    Scores are weighted from 1-10
    1 = High Card Value Only
    2 = 2 of a Kind (Pair)
    3 = 2 Pair (2 x 2 cards)
    4 = 3 of a kind (3-Card)
    5 = Straight (5 cards, any suit, in a row)
    6 = Flush (5 cards in a suit, no order)
    7 = Full House (3 of a kind + Pair)
    8 = 4 of a Kind (4-Card)
    9 = Straight Flush (5 cards in a suit, in order)
    10 = Royal Flush (10, Jack, Queen, King, and Aces in a suit)
    """
    scoreValue = 1

    #Step 0 : Print the hand
    displayCurrentCards = ""
    for card in currentCards:
        if displayCurrentCards == "":
            displayCurrentCards += card
        else:
            displayCurrentCards += ", " + card
    if display:
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
    if display:
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
        if display:
            print("Four of a Kind: " + getCardNameByNumber(highestFour))
        scoreValue = updateScoreValue(8,scoreValue)
    elif threeOfAKind and pairs:
        # Full House: 3 of a kind + 2 of a kind beats everything except four of a kind
        highestThree = max(threeOfAKind)
        highestPair = max(pairs)
        if display:
            print("Full House: " + getCardNameByNumber(highestThree) + "s over " + getCardNameByNumber(highestPair) + "s")
        scoreValue = updateScoreValue(7,scoreValue)
    elif threeOfAKind:
        # Three of a kind is better than two pairs or pairs
        highestThree = max(threeOfAKind)
        if display:
            print("Three of a Kind: " + getCardNameByNumber(highestThree))
        scoreValue = updateScoreValue(4,scoreValue)
    elif len(pairs) >= 2:
        # Two pairs beats single pair
        pairs.sort(reverse=True)  # Sort in descending order
        if display:
            print("Two Pairs: " + getCardNameByNumber(pairs[0]) + " and " + getCardNameByNumber(pairs[1]))
        scoreValue = updateScoreValue(3,scoreValue)
    elif len(pairs) == 1:
        # Single pair is the lowest ranking
        if display:
            print("Pair: " + getCardNameByNumber(pairs[0]))
        scoreValue = updateScoreValue(2,scoreValue)

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
        if display:
            print("Straight: " + getCardNameByNumber(straightHigh) + " high")
        scoreValue = updateScoreValue(5,scoreValue)

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
                if display:
                    print("Royal Flush in " + suitNames[i] + "!")
                scoreValue = updateScoreValue(10, scoreValue)
                return scoreValue  # Royal flush is the highest, no need to check further
            
            # Check for Straight Flush (5 consecutive cards in same suit)
            straightFlushFound = False
            
            # Check regular straight flush
            for j in range(len(suitNumbers) - 4):
                if (suitNumbers[j+1] == suitNumbers[j] + 1 and
                    suitNumbers[j+2] == suitNumbers[j] + 2 and
                    suitNumbers[j+3] == suitNumbers[j] + 3 and
                    suitNumbers[j+4] == suitNumbers[j] + 4):
                    straightFlushFound = True
                    scoreValue = updateScoreValue(9, scoreValue)
                    return scoreValue  # Straight flush found, no need to check further
            
            # Check for Ace-low straight flush (A, 2, 3, 4, 5)
            if not straightFlushFound and 14 in suitNumbers:
                aceLowSuit = [1 if x == 14 else x for x in suitNumbers]
                aceLowSuit.sort()
                
                if aceLowSuit == [1, 2, 3, 4, 5]:
                    if display:
                        print("Straight Flush in " + suitNames[i] + ": 5 high (Ace-low)")
                    scoreValue = updateScoreValue(9, scoreValue)
                    return scoreValue  # Ace-low straight flush found
            
            # If no royal flush or straight flush, it's a regular flush
            if not straightFlushFound:
                if display:
                    print("Flush in " + suitNames[i])
                scoreValue = updateScoreValue(6, scoreValue)
                return scoreValue # Flush found, no need to check other suits

    return scoreValue

def updateScoreValue(value, score):
    if value > score:
        score = value
    return score

def decodeScoreValue(value):
    match(value):
        case 1:
            return "High Card Only"
        case 2:
            return "2 of a Kind(Pair)"
        case 3:
            return "2 Pairs"
        case 4:
            return "3 of a Kind"
        case 5:
            return "Straight"
        case 6:
            return "Flush"
        case 7:
            return "Full House"
        case 8:
            return "4 of a Kind"
        case 9:
            return "Straight Flush"
        case 10:
            return "Royal Flush"

def findBestHand(allCards):
    from itertools import combinations

    bestScore = 0
    bestHand = []
    
    # Generate all possible 5-card combinations
    for combo in combinations(allCards, 5):
        comboList = list(combo)
        
        # Calculate score for this combination (without printing)
        score = calculateScoreValue(comboList,False)
        
        # Keep track of the best hand found so far
        if score > bestScore:
            bestScore = score
            bestHand = comboList
    
    return bestHand

def getStringValueOfHand(hand):
    result = ""
    for x in hand:
        if result == "":
            result += x
        else:
            result += ", " + x
    return result
