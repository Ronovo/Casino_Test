"""Export a character to CharacterTool/Character/<name>.json.

Usage (from any folder):  python CharacterTool/export_character.py "Ronovo Ronove"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from casino.config import ACHIEVEMENTS_PATH, CHARACTER_EXPORT_DIR, DB_PATH  # noqa: E402
from casino.engine.db import Database  # noqa: E402
from casino.transfer import write_export  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a character to JSON.")
    parser.add_argument("name", help="character name as it appears in the game")
    parser.add_argument("--out", type=Path, default=CHARACTER_EXPORT_DIR, help="folder to write the JSON file to")
    args = parser.parse_args()

    db = Database(DB_PATH)
    db.initialize(ACHIEVEMENTS_PATH)
    try:
        path = write_export(db, args.name, args.out)
    except ValueError as error:
        sys.exit(f"ERROR: {error}")
    print(f"Exported '{args.name}' to {path}")


if __name__ == "__main__":
    main()
