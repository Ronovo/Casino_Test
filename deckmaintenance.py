import random

#Note 1S = 10S (Kept 1 digit for simplicity of code)
newDeck = ['AS', '2S', '3S', '4S', '5S', '6S', '7S', '8S', '9S', '1S', 'JS', 'QS', 'KS',
           'AH', '2H', '3H', '4H', '5H', '6H', '7H', '8H', '9H', '1H', 'JH', 'QH', 'KH',
           'AC', '2C', '3C', '4C', '5C', '6C', '7C', '8C', '9C', '1C', 'JC', 'QC', 'KC',
           'AD', '2D', '3D', '4D', '5D', '6D', '7D', '8D', '9D', '1D', 'JD', 'QD', 'KD']

def restockDeck():
    deck = newDeck.copy() 
    shuffle(deck)
    return deck

def shuffle(currentDeck):
    random.shuffle(currentDeck)
    return currentDeck

def faceOrNumber(value):
    match value:
        case '1':
            return '10'
        case 'A':
            return 'Ace'
        case 'J':
            return 'Jack'
        case 'Q':
            return 'Queen'
        case 'K':
            return 'King'
        case _:
             return value

def discard(discard, card):
    countDiscard = discard.__len__()
    discard.insert(countDiscard, card)

def draw(currentDeck):
    card = currentDeck[0]
    currentDeck.pop(0)
    return card

def getCardName(card):
    numberResult = getCardNumberString(card)
    suitResult = getSuit(card)
    result = numberResult + ' of ' + suitResult
    return result

def getCardNumberString(card):
    number = card[0:1]
    return faceOrNumber(number)

def getSuit(card):
    suit = card[1:]
    match suit:
        case 'S':
            return 'Spades'
        case 'H':
            return 'Hearts'
        case 'C':
            return 'Clubs'
        case 'D':
            return 'Diamonds'

# Used for Ranking Order, for example, Poker.
# If a game needs to use their own version, they can adapt this as needed
def getNumericValue(value):
    match value:
        case '1':
            return 10
        case 'J':
            return 11
        case 'Q':
            return 12
        case 'K':
            return 13
        case 'A':
            return 14
        case _:
            return int(value)