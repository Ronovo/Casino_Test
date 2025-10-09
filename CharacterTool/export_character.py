import os
from character_helper_methods import export_character_to_json

#Name from the database
characterName = "Tester"

#Hardcoded for now. Plug your own in here.
cwd = os.getcwd()
exportPath = cwd + "/Character/" + characterName + ".json"
export_character_to_json(characterName, exportPath)