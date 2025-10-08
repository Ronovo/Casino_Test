import formatter
from Games import blackjack, poker
from DAL import character_maintenance as cm
from Database import create_database_structure as dbcreate
from Database import load_helper_methods as filltables
import os

#Initialize Database
dbcreate.init_db()

#Load achievements
cwd = os.getcwd()
achievementpath = cwd + "/Database/achievements.json"
filltables.load_achievements_from_json(achievementpath)
#Load Paytables
blindsPath = cwd + "/Paytables/blind_modifier.json"
filltables.load_poker_blinds(blindsPath)
tripsPath = cwd + "/Paytables/trips_modifier.json"
filltables.load_poker_trips(tripsPath)
pairsPath = cwd + "/Paytables/pairs_modifier.json"
filltables.load_poker_pairs(pairsPath)
#Run the character menu
characterName = cm.load_characters_at_start()

while 1 > 0:
    formatter.clear()
    formatter.drawMenuTopper("Welcome to Ronovo's Casino v1.5")
    print("Main Menu")
    print("1.) Blackjack v2.0 (Production Ready)")
    print("2.) Texas Hold'em Poker(V1.2 : Achievement Update)")
    print("3.) Guess the Number - COMING SOON")
    print("4.) Horse/Dog Racing - COMING SOON")
    print("5.) Roulette - COMING SOON")
    print("6.) Shooting Range Bets - COMING SOON")
    print("7.) Display Character Information")
    print("8.) Quit")
    menuInput = input(formatter.getInputText("Choice"))
    if menuInput.isnumeric():
        formatter.clear()
        if 0 > int(menuInput) >= 4:
            input(formatter.getInputText("Wrong Number"))
        match menuInput:
            case "1":
                blackjack.blackjackStart(characterName)
            case "2":
                poker.pokerStart(characterName)
            case "3":
                print("Guess the Number - COMING SOON")
                input(formatter.getInputText("Enter"))
            case "4":
                print("Horse/Dog Racing - COMING SOON")
                input(formatter.getInputText("Enter"))
            case "5":
                print("Roulette - COMING SOON")
                input(formatter.getInputText("Enter"))
            case "6":
                print("Shooting Range Bets - COMING SOON")
                input(formatter.getInputText("Enter"))
            case "7":
                cm.display_character(characterName, True)
            case "8":
                quit()
            case _:
                input(formatter.getInputText("NonNumber"))
    else:
        input(formatter.getInputText("NonNumber"))


