"""Horse racing maths: how strong a horse is today, exact odds on the finishing order, and steward handicapping.

Each horse's run is its strength plus Gumbel-distributed luck. With that noise the finishing order follows the
Plackett-Luce model, so the chance of any horse finishing in the first k places has a closed form and the
odds on the board are exact rather than estimated.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from itertools import permutations
from typing import Sequence

GOING = {"Firm": -1.0, "Good": -0.35, "Soft": 0.35, "Heavy": 1.0}
# Furlongs -> how much the trip favors stayers (+) over sprinters (-).
DISTANCES = {5: -1.0, 6: -0.6, 8: 0.0, 10: 0.5, 12: 1.0}
BET_PLACES = {"win": 1, "place": 2, "show": 3}
ODDS_LADDER = (0.05, 0.1, 0.2, 0.4, 0.5, 0.6, 0.8, 1, 1.2, 1.4, 1.5, 1.6, 1.8, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8,
               9, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 99)
SECONDS_PER_FURLONG = 12.2
SECONDS_PER_LENGTH = 0.17
LENGTHS_PER_POINT = 0.45
MAX_LENGTHS_BEHIND = 25.0


@dataclass(frozen=True)
class Horse:
    key: str
    name: str
    rating: float
    # -1 pure sprinter .. +1 pure stayer
    stamina: float
    # -1 needs firm ground .. +1 loves the mud
    mud: float
    style: str
    silks: str


@dataclass(frozen=True)
class Conditions:
    distance: int
    going: str


@dataclass(frozen=True)
class Model:
    # Scale of the luck added to every run. Bigger means more upsets.
    spread: float = 5.0
    # Rating points gained by a horse perfectly suited to the trip or the ground (and lost by one that isn't).
    aptitude: float = 4.0
    # Rating points lost per pound of handicap weight.
    weight_cost: float = 0.5


@dataclass(frozen=True)
class HandicapRules:
    # How many of a horse's latest races the stewards look at.
    window: int = 8
    # A horse that wins with at least this many wins in the window is winning too much.
    hot_wins: int = 2
    penalty_lb: int = 6
    # Weight taken off each time a weighted horse finishes outside the first three.
    relief_lb: int = 1
    max_lb: int = 30


def strength(horse: Horse, conditions: Conditions, weight: int, model: Model) -> float:
    """Today's rating: base ability, adjusted for trip, ground and the weight the horse has to carry."""
    return (horse.rating
            + model.aptitude * horse.stamina * DISTANCES[conditions.distance]
            + model.aptitude * horse.mud * GOING[conditions.going]
            - model.weight_cost * weight)


def win_probabilities(strengths: Sequence[float], spread: float) -> list[float]:
    top = max(strengths)
    weights = [math.exp((value - top) / spread) for value in strengths]
    total = sum(weights)
    return [weight / total for weight in weights]


def finish_probabilities(strengths: Sequence[float], spread: float) -> list[dict[str, float]]:
    """For each runner, the exact chance of finishing 1st ("win"), in the first 2 ("place") and first 3 ("show")."""
    if len(strengths) < 3:
        raise ValueError("A race needs at least three runners")
    win = win_probabilities(strengths, spread)
    chances = [{"win": 0.0, "place": 0.0, "show": 0.0} for _ in strengths]
    for first, second, third in permutations(range(len(strengths)), 3):
        # Each place is won by a runner in proportion to its share of the runners still behind the leaders.
        chance = (win[first] * win[second] / (1 - win[first])
                  * win[third] / (1 - win[first] - win[second]))
        chances[first]["win"] += chance
        for runner in (first, second):
            chances[runner]["place"] += chance
        for runner in (first, second, third):
            chances[runner]["show"] += chance
    return chances


def offered_odds(probability: float, margin: float) -> float | None:
    """The best ladder price that still leaves the house its margin, or None if no price is short enough."""
    fair = (1 - margin) / probability - 1
    prices = [price for price in ODDS_LADDER if price <= fair]
    return prices[-1] if prices else None


def run_race(strengths: Sequence[float], spread: float, rng: random.Random) -> list[float]:
    """One run per horse: strength plus Gumbel luck. The highest score wins."""
    scores = []
    for value in strengths:
        chance = min(max(rng.random(), 1e-12), 1 - 1e-12)
        scores.append(value - spread * math.log(-math.log(chance)))
    return scores


def finishing_order(scores: Sequence[float]) -> list[int]:
    """Runner indexes from first to last."""
    return sorted(range(len(scores)), key=lambda index: -scores[index])


def lengths_behind(scores: Sequence[float]) -> list[float]:
    best = max(scores)
    return [min((best - score) * LENGTHS_PER_POINT, MAX_LENGTHS_BEHIND) for score in scores]


def race_times(scores: Sequence[float], conditions: Conditions) -> list[float]:
    """Finishing time in seconds for each runner. Softer ground runs slower."""
    winner = conditions.distance * SECONDS_PER_FURLONG * (1 + 0.03 * (GOING[conditions.going] + 1))
    return [round(winner + lengths * SECONDS_PER_LENGTH, 2) for lengths in lengths_behind(scores)]


def review_weight(weight: int, recent: Sequence[int], rules: HandicapRules) -> int:
    """A horse's handicap weight after the stewards review its latest finishing positions (newest last)."""
    window = list(recent)[-rules.window:]
    if not window:
        return weight
    if window[-1] == 1 and window.count(1) >= rules.hot_wins:
        return min(rules.max_lb, weight + rules.penalty_lb)
    if window[-1] > 3:
        return max(0, weight - rules.relief_lb)
    return weight
