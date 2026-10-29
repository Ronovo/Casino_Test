"""Import a character from a JSON export.

Usage (from any folder):
    python CharacterTool/import_character.py "CharacterTool/Character/Ronovo Ronove.json"
    python CharacterTool/import_character.py "CharacterTool/Character/Ronovo Ronove.json" --name "Medium_Imported"
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from casino.config import ACHIEVEMENTS_PATH, DB_PATH  # noqa: E402
from casino.engine.db import Database  # noqa: E402
from casino.transfer import read_import  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a character from JSON.")
    parser.add_argument("path", type=Path, help="exported character JSON file")
    parser.add_argument("--name", help="save under a different name than the one in the file")
    args = parser.parse_args()

    db = Database(DB_PATH)
    db.initialize(ACHIEVEMENTS_PATH)
    try:
        character = read_import(db, args.path, args.name)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        sys.exit(f"ERROR: {error}")
    print(f"Imported '{character.name}' ({character.difficulty}).")


if __name__ == "__main__":
    main()
