"""File locations and static configuration, resolved from this file rather than the working directory."""
from __future__ import annotations

import json
import os
from pathlib import Path

from casino.engine.chips import CHIP_VALUES, Chips

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "Data"
TABLES_DIR = DATA_DIR / "Tables"
ACHIEVEMENTS_PATH = DATA_DIR / "achievements.json"
CHIPS_PATH = DATA_DIR / "Money" / "chips.json"
HORSES_PATH = DATA_DIR / "horses.json"
DB_PATH = Path(os.environ.get("CASINO_DB") or ROOT / "casino.db")

# Difficulty name -> its column in chips.json
DIFFICULTIES: dict[str, str] = {
    "Easy": "easy_amount",
    "Medium": "medium_amount",
    "Hard": "hard_amount",
    "Very Hard": "vhard_amount",
}


def load_starting_chips(difficulty: str, path: Path = CHIPS_PATH) -> Chips:
    """Starting rack for a difficulty, as defined in chips.json."""
    column = DIFFICULTIES[difficulty]
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    counts = {}
    for row in rows:
        color = row["color"]
        if CHIP_VALUES.get(color) != row["credit_value"]:
            raise ValueError(f"chips.json value for {color} does not match the engine's chip values")
        counts[color] = row[column]
    return Chips(counts)
