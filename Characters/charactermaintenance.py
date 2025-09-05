import json
import os
#Display Character Functions
def displayCharacter(characterData):
    print("Your character:")
    print("Name : " + characterData['Name'])
    print("Credits : " + str(characterData['Credits']))
    print("Difficulty : " + characterData['Difficulty'])
    input("Press any key to continue to game...")

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
        createNewCharacter()
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
