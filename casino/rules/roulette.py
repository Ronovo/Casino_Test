"""The American roulette wheel and bet resolution. Pockets are strings so '00' fits alongside '0'-'36'."""
from __future__ import annotations

WHEEL = ("0", "28", "9", "26", "30", "11", "7", "20", "32", "17", "5", "22", "34", "15", "3", "24",
         "36", "13", "1", "00", "27", "10", "25", "29", "12", "8", "19", "31", "18", "6", "21", "33",
         "16", "4", "23", "35", "14", "2")
RED_NUMBERS = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})


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
