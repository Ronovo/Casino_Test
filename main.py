from Games import tester, blackjack, poker
from Characters import charactermaintenance as cm


characterData = cm.loadCharactersAtStart()
characterName = characterData['Name']
while 1 > 0:
    characterData = cm.loadCharacteByName(characterName)
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
            blackjack.blackjackStart(characterData)
        case 3:
            poker.pokerStart(characterData)
        case 4:
            cm.displayCharacter(characterData)
        case 99:
            quit()


