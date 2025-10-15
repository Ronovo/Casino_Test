import os
from character_helper_methods import import_character_from_json

charactername = "Ronovo Ronove"
cwd = os.getcwd()
exportPath = cwd + "/Character/" + charactername + ".json"
# Override Name if you want to save under a different name then the one in the file
#Switch to true if you do and add the differentName
override = False
differentName = "Medium_Imported"

if not override:
    import_character_from_json(exportPath)

else:
    import_character_from_json(exportPath, differentName)