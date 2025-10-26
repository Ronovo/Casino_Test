from DAL import character_maintenance as cm, money_maintenance as mm
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
            if 0 > int(menuInput) >= 3:
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
    print("Aces = 2")
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
    print("Check Pay Tables for payout information.")
    input(formatter.getInputText("Enter Menu"))
    return

def printPayTableBaccarat():
    pass

def printPayTableBlackjack():
    formatter.clear()
    formatter.drawMenuTopper("Baccarat Pay Table")
    print("Player = 1:1")
    print("Banker = 1:1")
    print("Natural = 2:1 if you win.")
    print("Tie = 8:1")
    input(formatter.getInputText("Enter Menu"))

def dealin(currentDeck, characterData):
    print("Game coming soon.")