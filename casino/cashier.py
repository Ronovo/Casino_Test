"""The cashier: break chips into smaller ones or color up into bigger ones. Totals never change."""
from __future__ import annotations

from casino.engine.chips import CHIP_VALUES, COLORS, Chips


def break_chips(chips: Chips, color: str, count: int, into: str) -> Chips:
    """Swap `count` chips of `color` for smaller `into` chips, with any remainder in the fewest chips. The floor
    has already checked `into` is smaller."""
    remaining = chips - Chips({color: count})
    target, rest = divmod(CHIP_VALUES[color] * count, CHIP_VALUES[into])
    return remaining + Chips({into: target}) + Chips.make_change(rest)


def smaller_than(chips: Chips, color: str) -> Chips:
    return Chips({c: chips[c] for c in COLORS if CHIP_VALUES[c] < CHIP_VALUES[color]})


def color_up(chips: Chips, into: str, count: int) -> Chips:
    """Combine smaller chips into `count` chips of `into`."""
    smaller = smaller_than(chips, into)
    larger = chips - smaller
    _, rest = smaller.split_off(CHIP_VALUES[into] * count)
    return larger + rest + Chips({into: count})
