import formatter
from formatter import drawMenuTopper


def gtnStart(characterName):
    while 1 > 0:
        formatter.clear()
        formatter.drawMenuTopper("Welcome to the Guess The Number V0.0")
        print("1.) Start Game - COMING SOON")
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
                    print("Game coming soon")
                    input(formatter.getInputText("Enter"))
                    '''
                    characterData = cm.load_character_by_name(characterName)
                    currentDeck = dm.restockDeck()
                    dealin(currentDeck, characterData)
                    '''
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
    print("Payout : 9:1,")
    print("2. Range Guess - You pick the range the number might be in.")
    print("Payout : 9-x:1, x = count of the numbers you picked")
    print("3. High/Low - High == 6-10, Low == >=1-5")
    print("Payout : 1:1")
    print("4. Even/Odd - Even == Divisible by 2")
    print("Payout : 1:1")
    input(formatter.getInputText("Enter Menu"))
    return