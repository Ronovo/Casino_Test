"""Export characters to JSON and import them back."""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from casino.engine.chips import Chips
from casino.engine.db import Character, Database

EXPORT_VERSION = "2.0"


def export_character(db: Database, name: str) -> dict[str, Any]:
    character = db.get_character(name)
    if character is None:
        raise ValueError(f"Character '{name}' not found")
    chips = db.load_chips(character.id)
    return {
        "character": {"name": character.name, "credits": chips.total, "difficulty": character.difficulty},
        "chips": chips.as_dict(lowercase=True),
        "stats": db.get_stats(character.id),
        "achievements": [
            {"achievement_name": a.name, "category": a.category, "display_name": a.display_name,
             "description": a.description, "date_unlocked": a.date_unlocked}
            for a in db.achievements(character.id) if a.unlocked
        ],
        "export_info": {"exported_at": datetime.datetime.now().isoformat(), "version": EXPORT_VERSION},
    }


def write_export(db: Database, name: str, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_character(db, name), f, indent=2, ensure_ascii=False)
    return path


def import_character(db: Database, data: dict[str, Any], name: str | None = None) -> Character:
    """Create or update a character from export data. Existing characters keep their difficulty."""
    character_data = data.get("character")
    if not character_data:
        raise ValueError("Invalid export: missing character data")
    name = name or character_data["name"]
    chips = Chips(data.get("chips") or {})

    character = db.get_character(name)
    if character:
        db.save_chips(character.id, chips)
    else:
        character = db.create_character(name, character_data.get("difficulty") or "Medium", chips)

    for game_key, values in (data.get("stats") or {}).items():
        db.set_stats(character.id, game_key, values)

    for achievement in data.get("achievements", []):
        try:
            db.unlock_achievement(character.id, achievement["achievement_name"], achievement.get("date_unlocked"))
        except KeyError:
            pass  # achievement no longer exists
    return character


def read_import(db: Database, path: Path, name: str | None = None) -> Character:
    with open(path, encoding="utf-8") as f:
        return import_character(db, json.load(f), name)
