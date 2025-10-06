from Games import poker
import deckmaintenance as dm

#############################
# TESTS
##############################
def generalTest():
    print("----------------------------------")
    print("General Test : Deal 7 Random Cards")
    print("----------------------------------")
    hand = []
    currentDeck = dm.restockDeck()

    for x in range(7):
        card = dm.draw(currentDeck)
        hand.append(card)

    poker.calculateScoreValue(hand)
    print("\n")

def highValueOnly():
    print("----------------------------------")
    print("High Value Only Test")
    print("----------------------------------")
    hand = ["AS","3D","4C","8D","1S"]
    poker.calculateScoreValue(hand)
    print("\n")

def twoKindTest():
    print("----------------------------------")
    print("2 of a Kind Test")
    print("----------------------------------")
    hand = ["AS","AD","4C","8D","1S"]
    poker.calculateScoreValue(hand)
    print("\n")

def twoPairTest():
    print("----------------------------------")
    print("2 Pair Test")
    print("----------------------------------")
    hand = ["AS","AD","4C","4D","1S"]
    poker.calculateScoreValue(hand)
    print("\n")

def threeKindTest():
    print("----------------------------------")
    print("3 of a Kind Test")
    print("----------------------------------")
    hand = ["AS","AD","AC","8D","1S"]
    poker.calculateScoreValue(hand)
    print("\n")

def fourKindTest():
    print("----------------------------------")
    print("4 of a Kind Test")
    print("----------------------------------")
    hand = ["AS","AD","AC","AH","1S"]
    poker.calculateScoreValue(hand)
    print("\n")

def straightLowTest():
    print("----------------------------------")
    print("Straight(Low) Test")
    print("----------------------------------")
    hand = ["AS","2D","3C","4H","5S"]
    poker.calculateScoreValue(hand)
    print("\n")

def straightHighTest():
    print("----------------------------------")
    print("Straight(High) Test")
    print("----------------------------------")
    hand = ["1S","JD","QC","KH","AS"]
    poker.calculateScoreValue(hand)
    print("\n")

def flushTest():
    print("----------------------------------")
    print("Flush Test")
    print("----------------------------------")
    hand = ["AS","2S","5S","7S","1S"]
    poker.calculateScoreValue(hand)
    print("\n")

def fullHouseTest():
    print("----------------------------------")
    print("Full House Test")
    print("----------------------------------")
    hand = ["AS","AD","AC","8D","8S"]
    poker.calculateScoreValue(hand)
    print("\n")

def straightFlushLowTest():
    print("----------------------------------")
    print("Straight Flush(Low) Test")
    print("----------------------------------")
    hand = ["AS","2S","3S","4S","5S"]
    poker.calculateScoreValue(hand)
    print("\n")

def straightFlushHighTest():
    print("----------------------------------")
    print("Straight Flush(High) Test")
    print("----------------------------------")
    hand = ["KS","QS","JS","1S","9S"]
    poker.calculateScoreValue(hand)
    print("\n")

def royalFlushTest():
    print("----------------------------------")
    print("Royal Flush(Straight Flush High) Test")
    print("----------------------------------")
    hand = ["1S","JS","QS","KS","AS"]
    poker.calculateScoreValue(hand)
    print("\n")

#############################
# RUN TESTS
# Comment out any tests you don't want to run
##############################
#Run to check if a random set will work
generalTest()

#TYPE TESTS
# High Value only
highValueOnly()

# 2 of a Kind
twoKindTest()

# 2 pair
twoPairTest()

# 3 of a kind
threeKindTest()

# 4 of a kind
fourKindTest()

# Straight
straightLowTest()
straightHighTest()

# Flush
flushTest()

# Full House
fullHouseTest()

# Straight Flush
straightFlushLowTest()
straightFlushHighTest()

# Royal Flush
royalFlushTest()
