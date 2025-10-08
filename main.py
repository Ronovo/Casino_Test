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
    formatter.drawMenuTopper("Welcome to Ronovo's Casino v1.0")
    print("Main Menu")
    print("1.) Blackjack v2.0 (Production Ready)")
    print("2.) Texas Hold'em Poker(V0.6.9)")
    print("3.) Display Character Information")
    print("4.) Quit")
    menuInput = input(formatter.getInputText("Choice"))
    if menuInput.isnumeric():
        formatter.clear()
        if 0 > int(menuInput) >= 4:
            input(formatter.getInputText("Wrong Number"))
        match menuInput:
            case "1":
                blackjack.blackjackStart(characterName)
                pass
            case "2":
                poker.pokerStart(characterName)
                pass
            case "3":
                cm.display_character(characterName)
                pass
            case "4":
                quit()
            case _:
                input(formatter.getInputText("NonNumber"))
    else:
        input(formatter.getInputText("NonNumber"))


