from Helpers import deckmaintenance as dm
import formatter

def displayHand(hand):
    handLength = hand.__len__()
    if handLength == 0:
        print("There are no cards in your hand")
    else:
        formatter.drawMenuTopper("Cards in hand")
        handCount = 0
        while handCount != handLength:
            card = hand[handCount]
            print(str(handCount + 1) + ".) " + dm.getCardName(card) + "(" + card + ")")
            handCount += 1