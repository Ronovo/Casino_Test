from Characters import charactermaintenance as cm

def removeMoney(characterData,amount):
    characterData['Credits'] -= amount
    return characterData

def addMoney(characterData,amount):
    characterData['Credits'] += amount
    return characterData

def setBet(characterData,amount):
    characterData['Current Bet'] += amount
    return characterData

def payOut(characterData,winFlag,winModifier):
    currentBet = characterData['Current Bet']
    match winFlag:
        #Win, Payout at Modifier
        case 1:
            winnings = int(currentBet * winModifier)
            characterData = addMoney(characterData,winnings)
        #Lose, Take the current bet
        case 0:
            characterData = removeMoney(characterData,characterData['Current Bet'])
        #Draw, Add Back current bet to Credits
        case -1:
            characterData = addMoney(characterData,characterData['Current Bet'])
    characterData['Current Bet'] = 0
    cm.saveCharacter(characterData)
    return characterData


