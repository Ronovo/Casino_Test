import formatter
from Games import blackjack, poker, gtn
from DAL import character_maintenance as cm, money_maintenance as mm
from Database import create_database_structure as dbcreate
from Database import load_helper_methods as fillTables
import os

#Initialize Database
dbcreate.init_db()

fillTables.loadDatabaseJson()

#Run the character menu
characterName = cm.load_characters_at_start()

while 1 > 0:
    formatter.clear()
    formatter.drawMenuTopper("Welcome to Ronovo's Casino v1.5")
    print("Main Menu")
    formatter.drawMenuLine()
    print("1.) Blackjack v2.0 (Production Ready)")
    print("2.) Texas Hold'em Poker(V1.2 : Achievement Update)")
    print("3.) Guess the Number - V0.0 Planning")
    print("4.) Baccarat - COMING SOON")
    print("5.) Horse Racing - COMING SOON")
    print("6.) Roulette - COMING SOON")
    print("7.) Shooting Range Bets - COMING SOON")
    print("8.) Display Character Information")
    print("9.) Betting Chips Menu")
    print("10.) Quit")
    menuInput = input(formatter.getInputText("Choice"))
    if menuInput.isnumeric():
        formatter.clear()
        if 0 > int(menuInput) >= 10:
            input(formatter.getInputText("Wrong Number"))
        match menuInput:
            case "1":
                blackjack.blackjackStart(characterName)
            case "2":
                poker.pokerStart(characterName)
            case "3":
                gtn.gtnStart(characterName)
            case "5":
                print("Horse Racing - COMING SOON")
                input(formatter.getInputText("Enter"))
            case "6":
                print("Roulette - COMING SOON")
                input(formatter.getInputText("Enter"))
            case "7":
                print("Shooting Range Bets - COMING SOON")
                input(formatter.getInputText("Enter"))
            case "8":
                cm.display_character(characterName, True)
            case "9":
                mm.chipsMenu(characterName)
            case "10":
                quit()
            case _:
                input(formatter.getInputText("NonNumber"))
    else:
        input(formatter.getInputText("NonNumber"))


