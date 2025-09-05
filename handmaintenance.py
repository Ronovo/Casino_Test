import deckmaintenance as dm

def displayHand(hand):
    handLength = hand.__len__()
    if handLength == 0:
        print("There are no cards in your hand")
    else:
        print("Cards in hand")
        print("-------------")
        handCount = 0
        while handCount != handLength:
            card = hand[handCount]
            print(str(handCount + 1) + ".) " + dm.getCardName(card) + "(" + card + ")")
            handCount += 1