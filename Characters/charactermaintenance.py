import json
import os
#Character Functions
def displayCharacter(characterData):
    print("Your character:")
    print("Name : " + characterData['Name'])
    print("Credits : " + str(characterData['Credits']))
    print("Difficulty : " + characterData['Difficulty'])
    if characterData['Achievements']:
        achievementList = ""
        lengthOfAchivements = len(characterData['Achievements'])
        z = 1
        for x in characterData['Achievements']:
            if z < lengthOfAchivements:
                achievementList += x['displayName'] + ", "
            else:
                achievementList += x['displayName']
            z += 1
        print("Achievements : " + achievementList)
    else:
        print("No Achievements Currently!")
    input("Press any key to continue to game...")

def insertAchievement(achievementName, characterData):
    cwd = os.getcwd()
    path = cwd + "/Characters"
    newPath = path + '/achievements.json'
    with open(newPath, mode="r", encoding="utf-8") as read_file:
        achievements = json.load(read_file)

    newAchievement = None
    # Find the achievement by name
    for achievement in achievements:
        if achievement['name'] == achievementName:
            newAchievement = achievement

    if newAchievement is None:
        return None

    if characterData['Achievements'] is None:
        characterData['Achievements'] = []

    for existing_achievement in characterData['Achievements']:
        if existing_achievement['name'] == newAchievement['name']:
            return None

    # Add the achievement to the character's achievements list

    characterData['Achievements'].append(newAchievement)
    saveCharacter(characterData)
    print("**************************")
    print("New Achievement")
    print(newAchievement['displayName'] + " : " + newAchievement['description'])
    print("**************************")

#Character Creation Functions
def createNewCharacter():
    with open("Characters/SampleCharacter.json", mode="r", encoding="utf-8") as read_file:
        newCharacterData = json.load(read_file)
    print("Welcome to the character creator.")
    print("Let's start with your name. Who is going to be betting?")
    name = input("Enter name here:\n")
    newCharacterData['Name'] = name
    print("Now let's start with your difficulty (This ties into achievements)")
    print("Options:")
    print("1. 10,000 Credits - Easy Mode")
    print("2. 1,000 Credits - Normal Mode")
    print("3. 10 Credits - Hard Mode")
    difficulty = input("Enter your difficulty now (1-3):\n")
    difficulty = int(difficulty)
    match difficulty:
        case 1:
            newCharacterData['Difficulty'] = "Easy"
            newCharacterData['Credits'] = 10000
        case 2:
            newCharacterData['Difficulty'] = "Medium"
            newCharacterData['Credits'] = 1000
        case 3:
            newCharacterData['Difficulty'] = "Hard"
            newCharacterData['Credits'] = 10
    displayCharacter(newCharacterData)

    fileName = "Characters/Saved Games/" + name + ".json"
    with open(fileName, mode="w", encoding="utf-8") as write_file:
        json.dump(newCharacterData, write_file)
    return newCharacterData

#Loading Functions
def loadCharactersAtStart():
    fileList = loadCharactersNames()
    print("Character Menu")
    print("--------------")
    n = 1
    for option in fileList:
        print(str(n) + ".) " + option)
        n += 1
    print(str(n) + ".) Create New Character")
    print(str(n + 1) + ".) Quit\n")
    answer = input("Please choose an option\n")
    if int(answer) == n:
        characterData = createNewCharacter()
        return characterData
    elif int(answer) == (n + 1):
        quit()
    else:
        fileIndex = int(answer) - 1
        grabFile = fileList[fileIndex]
        cwd = os.getcwd()
        path = cwd + "/Characters/Saved Games"
        newPath = path + '/' + grabFile + '.json'
        with open(newPath, mode="r", encoding="utf-8") as read_file:
            characterData = json.load(read_file)
        displayCharacter(characterData)
        return characterData

def loadCharacteByName(name):
    cwd = os.getcwd()
    path = cwd + "/Characters/Saved Games"
    newPath = path + '/' + name + '.json'
    with open(newPath, mode="r", encoding="utf-8") as read_file:
        characterData = json.load(read_file)
    return characterData

def loadCharactersNames():
    print("Load Game Called")

    cwd = os.getcwd()
    path = cwd + "/Characters/Saved Games"
    items = os.listdir(path)
    fileList = []
    for file in items:
        nameLength = len(file)
        cutoff = nameLength - 5
        file = file[0:cutoff]
        fileList.append(file)
    return fileList

#Save Functions
def saveCharacter(characterData):
    fileName = "Characters/Saved Games/" + characterData['Name'] + ".json"
    with open(fileName, mode="w", encoding="utf-8") as write_file:
        json.dump(characterData, write_file)
