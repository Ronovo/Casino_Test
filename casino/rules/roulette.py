"""Roulette wheels and bet resolution. Pockets are strings so American '00' fits alongside '0'-'36'."""
from __future__ import annotations

EUROPEAN_WHEEL = ("0", "32", "15", "19", "4", "21", "2", "25", "17", "34", "6", "27", "13", "36", "11", "30",
                  "8", "23", "10", "5", "24", "16", "33", "1", "20", "14", "31", "9", "22", "18", "29", "7",
                  "28", "12", "35", "3", "26")
AMERICAN_WHEEL = ("0", "28", "9", "26", "30", "11", "7", "20", "32", "17", "5", "22", "34", "15", "3", "24",
                  "36", "13", "1", "00", "27", "10", "25", "29", "12", "8", "19", "31", "18", "6", "21", "33",
                  "16", "4", "23", "35", "14", "2")
WHEELS = {"european": EUROPEAN_WHEEL, "american": AMERICAN_WHEEL}
RED_NUMBERS = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})
BET_KINDS = ("straight", "red_black", "odd_even", "low_high", "dozen", "column")


def color_of(pocket: str) -> str:
    if pocket in ("0", "00"):
        return "green"
    return "red" if int(pocket) in RED_NUMBERS else "black"


def wins(kind: str, selection: str | int, pocket: str) -> bool:
    if kind == "straight":
        return str(selection) == pocket
    if pocket in ("0", "00"):
        return False
    number = int(pocket)
    match kind:
        case "red_black":
            return (selection == "Red") == (number in RED_NUMBERS)
        case "odd_even":
            return (selection == "Even") == (number % 2 == 0)
        case "low_high":
            return (selection == "Low") == (number <= 18)
        case "dozen":
            return (number - 1) // 12 + 1 == int(selection)
        case "column":
            return (number - 1) % 3 + 1 == int(selection)
    raise ValueError(f"Unknown bet kind: {kind}")
