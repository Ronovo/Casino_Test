# Clear screen
import os

inputText = {
    "NonNumber": "That is not a number. Please Try again...\n",
    "Wrong Number" : "Wrong Number. Plese Try Again...\n",
    "Enter" : "\nPress Enter to continue...\n",
    "Choice" : "Please make your choice...\n",
    "x" : "Please select a number, not x...\n",
    "Enter Page" : "\nPress Enter for next page...\n",
    "Enter Menu" : "\nPress Enter to return to the menu...\n",
    "Set Bet" : "Set new bet amount...\n"
}

def getInputText(key):
    return inputText[key]

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def drawMenuLine():
    print("--------------------------------------")

def drawMenuTopper(menuText):
    drawMenuLine()
    print(menuText)
    drawMenuLine()