"""Game registry: table JSON files in Data/Tables pick a game type by its `game` key."""
from __future__ import annotations

from pathlib import Path

from casino.engine.game import Game, TableConfig
from casino.games.baccarat import BaccaratGame
from casino.games.blackjack import BlackjackGame
from casino.games.gtn import GuessTheNumberGame
from casino.games.poker import UltimateHoldemGame
from casino.games.racing import HorseRacingGame
from casino.games.roulette import RouletteGame

GAME_TYPES: dict[str, type[Game]] = {
    game.game_key: game
    for game in (BlackjackGame, UltimateHoldemGame, BaccaratGame, GuessTheNumberGame, RouletteGame,
                 HorseRacingGame)
}


def load_games(tables_dir: str | Path) -> list[Game]:
    games = []
    for path in sorted(Path(tables_dir).glob("*.json")):
        table = TableConfig.from_file(path)
        if table.game not in GAME_TYPES:
            raise ValueError(f"{path.name}: unknown game type '{table.game}'")
        games.append(GAME_TYPES[table.game](table))
    return sorted(games, key=lambda game: (game.table.order, game.title))
