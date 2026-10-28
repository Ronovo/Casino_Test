"""Guess the Number: the dealer draws a number, you bet on what it is."""
from __future__ import annotations

from typing import Any, Mapping

from casino.engine.bets import Bet, BetError, Outcome, format_ratio, read_stake, settle
from casino.engine.game import Game, Round, pay_section
from casino.engine.session import Session
from casino.rules import gtn as rules
from casino.rules.gtn import Difficulty

BET_NAMES = {"pick": "Pick a Number", "high_low": "High / Low", "even_odd": "Even / Odd",
             "range": "Range", "lucky": "Lucky Combo"}


def _whole(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def read_selection(kind: str, value: Any, difficulty: Difficulty) -> Any:
    """Validate a client's selection for one bet kind and return it in the form rules.resolve expects."""
    top = difficulty.max_number
    if kind in ("pick", "range"):
        last = top if kind == "pick" else top - difficulty.range_size + 1
        if not _whole(value, 1, last):
            raise BetError(f"{BET_NAMES[kind]}: choose a number from 1 to {last:,}.")
        return value
    if kind in ("high_low", "even_odd"):
        choices = ("High", "Low") if kind == "high_low" else ("Even", "Odd")
        if value not in choices:
            raise BetError(f"{BET_NAMES[kind]}: choose {choices[0]} or {choices[1]}.")
        return value
    if (not isinstance(value, list) or len(value) != 2 or not all(_whole(number, 1, top) for number in value)
            or value[0] == value[1]):
        raise BetError(f"Lucky Combo: choose two different numbers from 1 to {top:,}.")
    return tuple(value)


class GuessRound(Round):
    def __init__(self, game: "GuessTheNumberGame", session: Session, difficulty: Difficulty, bets: dict[str, Bet]):
        super().__init__(game, session)
        self.difficulty = difficulty
        self.bets = bets
        self.number = session.rng.randint(1, difficulty.max_number)
        settlements, notes = [], []
        for kind, bet in bets.items():
            resolution = rules.resolve(kind, bet.selection, self.number, difficulty, game.table.paytable)
            settlements.append(settle(session.wallet, bet, resolution.outcome, resolution.ratio or 1))
            if resolution.detail:
                notes.append(f"{bet.label}: {resolution.detail}")
            if resolution.outcome is Outcome.WIN:
                session.unlock("GTN_Win")
                if kind == "pick" and bet.selection == self.number:
                    session.unlock("GTN_Exact")
                    if difficulty.max_number >= 100_000_000:
                        session.unlock("GTN_Impossible")
                if kind == "lucky" and bet.selection[0] == self.number:
                    session.unlock("GTN_Lucky")
        self.finish(settlements, notes)

    @property
    def staked(self) -> int:
        return sum(bet.amount for bet in self.bets.values())

    def table_view(self) -> dict[str, Any]:
        return {"number": self.number, "digits": self.difficulty.digits, "difficulty": self.difficulty.name}


class GuessTheNumberGame(Game):
    game_key = "gtn"
    display_name = "Guess the Number"

    @property
    def difficulties(self) -> list[Difficulty]:
        return [Difficulty(item["name"], item["max_number"]) for item in self.setting("difficulties", [])]

    def _ratios(self, difficulty: Difficulty) -> dict[str, str]:
        pay = self.table.paytable
        return {"exact": format_ratio(rules.ratio_for("pick", "exact", difficulty, pay)),
                "close": format_ratio(pay["close"]),
                "high_low": format_ratio(pay["high_low"]),
                "even_odd": format_ratio(pay["even_odd"]),
                "range": format_ratio(pay["range"]),
                "lucky_1": format_ratio(rules.ratio_for("lucky", "lucky_1", difficulty, pay)),
                "lucky_2": format_ratio(rules.ratio_for("lucky", "lucky_2", difficulty, pay))}

    def rules_pages(self) -> list[list[str]]:
        return [
            ["A simple number guessing game in three steps:",
             "1) Pick a difficulty.",
             "2) Place as many different bets as you like.",
             "3) The dealer reveals the number and every bet is paid out."],
            ["Bets (examples use Easy, 1 to 10):",
             "Pick a Number: an exact match pays big. Within 1 of the number pays less.",
             "High / Low: Low is 1-5, High is 6-10.",
             "Even / Odd: whether the number divides by 2.",
             "Range: choose where a run of 2 numbers starts (1-2, 2-3, ...).",
             "Lucky Combo: choose two numbers. The first pays more than the second.",
             "Harder difficulties scale the exact-match payouts, the 'close' window and the range size."],
        ]

    def paytable(self) -> list[dict[str, Any]]:
        sections = []
        for difficulty in self.difficulties:
            ratios = self._ratios(difficulty)
            sections.append(pay_section(f"{difficulty.name} (1 to {difficulty.max_number:,})", [
                ["Exact pick", ratios["exact"]],
                [f"Pick within {difficulty.scale:,}", ratios["close"]],
                ["High / Low", ratios["high_low"]],
                ["Even / Odd", ratios["even_odd"]],
                [f"Range of {difficulty.range_size:,}", ratios["range"]],
                ["Lucky #1", ratios["lucky_1"]],
                ["Lucky #2", ratios["lucky_2"]],
            ]))
        return sections

    def layout(self) -> dict[str, Any]:
        return {"bets": [{"key": key, "label": label} for key, label in BET_NAMES.items()],
                "difficulties": [{"name": d.name, "max_number": d.max_number, "scale": d.scale, "half": d.half,
                                  "range_size": d.range_size, "digits": d.digits, "ratios": self._ratios(d)}
                                 for d in self.difficulties]}

    def start(self, session: Session, data: Mapping[str, Any]) -> GuessRound:
        difficulty = next((d for d in self.difficulties if d.name == data.get("difficulty")), None)
        if difficulty is None:
            raise BetError("Pick a difficulty first.")
        raw_bets = data.get("bets")
        if not isinstance(raw_bets, Mapping) or not raw_bets:
            raise BetError("Place at least one bet first.")
        bets = {}
        for kind, item in raw_bets.items():
            if kind not in BET_NAMES or not isinstance(item, Mapping):
                raise BetError("That bet isn't on offer.")
            selection = read_selection(kind, item.get("selection"), difficulty)
            amount = read_stake(item.get("amount"), BET_NAMES[kind], self.table.min_bet, self.table.max_bet)
            bets[kind] = Bet(BET_NAMES[kind], amount, selection)
        self.take_stakes(session, sum(bet.amount for bet in bets.values()))
        return GuessRound(self, session, difficulty, bets)
