from Games import tester, blackjack
from Characters import charactermaintenance as cm

characterData = cm.loadCharactersAtStart()
while 1 > 0:
    print("Welcome to Ronovo's Casino v0.2")
    print("-------------------------------")
    print("Main Menu")
    print("1.) Test Deck Functions")
    print("2.) Blackjack v1.0")
    print("3.) Display Character Information")
    print("4.) Quit")
    x = input("Please enter your answer!\n")
    x = int(x)
    match x:
        case 1:
            tester.testStart()
        case 2:
            blackjack.blackjackStart()
        case 3:
            cm.displayCharacter(characterData)
        case 4:
            quit()



