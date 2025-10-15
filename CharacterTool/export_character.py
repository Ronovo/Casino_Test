import os
from character_helper_methods import export_character_to_json

# --------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------
# Name from the database - change this to the character you want to export
characterName = "Ronovo Ronove"

# --------------------------------------------------------
# EXPORT
# --------------------------------------------------------
# Get the current working directory and construct the export path
cwd = os.getcwd()
character_folder = os.path.join(cwd, "Character")

# Create the Character folder if it doesn't exist
if not os.path.exists(character_folder):
    os.makedirs(character_folder)
    print(f"Created Character folder at: {character_folder}")

# Construct the full export path
exportPath = os.path.join(character_folder, f"{characterName}.json")

print(f"Exporting character '{characterName}' to: {exportPath}")
print("-" * 60)

try:
    export_character_to_json(characterName, exportPath)
    print("-" * 60)
    print(f"SUCCESS: Export completed successfully!")
    print(f"File saved to: {exportPath}")
except ValueError as e:
    print(f"ERROR: {e}")
    print("Please make sure the character name exists in the database.")
except Exception as e:
    print(f"ERROR: An unexpected error occurred: {e}")