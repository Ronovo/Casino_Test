import deckmaintenance as dm
import handmaintenance as hm

def testStart():
    currentDeck = dm.restockDeck()
    discard = []
    hand = []
    print("Welcome to the Tester v0.0")
    print("----------------")
    while 1 != 0:
        count = currentDeck.__len__()
        print("\nThere are " + str(count) + " cards left in the deck\n")
        print("Current Commands")
        print("1. Check Hand")
        print("2. Draw")
        print("3. Discard")
        print("4. Shuffle Deck")
        print("5. Restore Deck")
        print("6. Main Menu")
        command = input("Enter your choice now\n")
        command = int(command)
        match command:
            case 1:
                hm.displayHand(hand)
            case 2:
                card = dm.draw(currentDeck)
                hand.append(card)
                print("You drew a " + dm.getCardName(card))
            case 3:
                print("Cards to discard")
                handLength = hand.__len__()
                if handLength == 0:
                    print("There is no card to discard")
                else:
                    hm.displayHand(hand)
                    answer = input("Which card do you want to discard?")
                    if answer.upper() in hand:
                        discard.append(answer.upper())
                        hand.remove(answer.upper())
                    else:
                        print("Card not in hand.")
            case 4:
                currentDeck = dm.shuffle(currentDeck)
            case 5:
                currentDeck = dm.restockDeck()
            case 6:
                return