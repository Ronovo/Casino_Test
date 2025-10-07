from Games import tester, blackjack, poker
from DAL import character_maintenance as cm
from Database import create_database_structure as dbcreate
from Database import populate_tables as filltables
import os

#Initialize Database
dbcreate.init_db()
#Load any new achievements added since last run
# Load achievements
cwd = os.getcwd()
filepath = cwd + "/Database/achievements.json"
filltables.load_achievements_from_json(filepath)
#Run the character menu
characterName = cm.load_characters_at_start()

while 1 > 0:
    print("Welcome to Ronovo's Casino v0.3")
    print("*******************************")
    print("NOW WITH BETTING")
    print("*******************************")
    print("-------------------------------")
    print("Main Menu")
    print("1.) Test Deck Functions")
    print("2.) Blackjack v1.2 (Now with Achievements!)")
    print("3.) Texas Hold'em Poker(V1.0)")
    print("4.) Display Character Information")
    print("99.) Quit")
    x = input("Please enter your answer!\n")
    x = int(x)
    match x:
        case 1:
            tester.testStart()
        case 2:
            blackjack.blackjackStart(characterName)
            pass
        case 3:
            poker.pokerStart(characterName)
            pass
        case 4:
            cm.display_character(characterName)
            pass
        case 99:
            quit()


