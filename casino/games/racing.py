"""Horse racing: bet on as many horses as you like, then watch a race in a season-long championship."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from casino.config import HORSES_PATH
from casino.engine.bets import Bet, BetError, Outcome, add_stake, format_ratio, settle
from casino.engine.game import Game, Round, TableConfig, pay_section
from casino.engine.session import Session
from casino.rules import racing as rules
from casino.rules.racing import Conditions, HandicapRules, Horse, Model

BET_NAMES = {"win": "Win", "place": "Place", "show": "Show"}
LONGSHOT_ODDS = 15
FORM_LENGTH = 10


def new_season(number: int, horses: list[Horse], conditions: Conditions, champion: str | None) -> dict[str, Any]:
    return {"season": number, "race": 0, "champion": champion,
            "conditions": {"distance": conditions.distance, "going": conditions.going},
            "horses": {horse.key: {"starts": 0, "firsts": 0, "seconds": 0, "thirds": 0, "points": 0, "weight": 0,
                                   "recent": []} for horse in horses}}


class RaceRound(Round):
    def __init__(self, game: "HorseRacingGame", session: Session, bets: list[tuple[str, str, Bet, float]]):
        super().__init__(game, session)
        self.bets = bets
        season = game.season(session)
        horses, records = game.horses, season["horses"]
        conditions = Conditions(**season["conditions"])
        weights = [records[horse.key]["weight"] for horse in horses]
        strengths = [rules.strength(horse, conditions, weight, game.model)
                     for horse, weight in zip(horses, weights)]
        scores = rules.run_race(strengths, game.model.spread, session.rng)
        order = rules.finishing_order(scores)
        position = {horses[index].key: place for place, index in enumerate(order, 1)}
        times, behind = rules.race_times(scores, conditions), rules.lengths_behind(scores)

        settlements = []
        for key, kind, bet, odds in bets:
            won = position[key] <= rules.BET_PLACES[kind]
            settlements.append(settle(session.wallet, bet, Outcome.WIN if won else Outcome.LOSE, odds))
            if won:
                session.unlock("Racing_Win")
                if kind == "win" and odds >= LONGSHOT_ODDS:
                    session.unlock("Racing_Longshot")
        paid = {(key, kind) for (key, kind, _, _), s in zip(bets, settlements) if s.outcome is Outcome.WIN}
        if any({(key, kind) for kind in BET_NAMES} <= paid for key, _ in paid):
            session.unlock("Racing_Across")

        winner, second = horses[order[0]], order[1]
        notes = [f"{winner.name} wins by {max(behind[second], 0.1):.1f} lengths."]
        self.race = {"season": season["season"], "number": season["race"] + 1, **season["conditions"]}
        changes = game.record_result(season, position)
        notes += [f"Stewards: {name} goes from +{old} lb to +{new} lb." for name, old, new in changes]
        self.runners = [{"key": horse.key, "name": horse.name, "silks": horse.silks, "style": horse.style,
                         "weight": weights[index], "position": position[horse.key], "time": times[index],
                         "lengths": round(behind[index], 1)}
                        for index, horse in enumerate(horses)]
        self.standings = game.standings(season)
        self.season_over = None
        if season["race"] >= game.season_length:
            champion = self.standings[0]["name"]
            self.season_over = {"season": season["season"], "champion": champion}
            notes.append(f"Season {season['season']} is over. {champion} is the champion!")
            session.unlock("Racing_Season")
            season = new_season(season["season"] + 1, horses, game.draw_conditions(session), champion)
        else:
            conditions = game.draw_conditions(session)
            season["conditions"] = {"distance": conditions.distance, "going": conditions.going}
        session.db.save_game_state(session.character.id, game.game_key, season)
        self.finish(settlements, notes)

    @property
    def staked(self) -> int:
        return sum(bet.amount for _, _, bet, _ in self.bets)

    def table_view(self) -> dict[str, Any]:
        return {"race": self.race, "runners": self.runners, "standings": self.standings,
                "season_over": self.season_over}


class HorseRacingGame(Game):
    game_key = "racing"
    display_name = "Horse Racing"

    def __init__(self, table: TableConfig, horses_path: str | Path = HORSES_PATH):
        super().__init__(table)
        with open(horses_path, encoding="utf-8") as f:
            self.horses = [Horse(**item) for item in json.load(f)]
        if len(self.horses) < 4 or len({horse.key for horse in self.horses}) != len(self.horses):
            raise ValueError("horses.json needs at least four horses with unique keys")
        self.model = Model(**self.setting("model", {}))
        self.handicap = HandicapRules(**self.setting("handicap", {}))
        self.season_length = int(self.setting("season_length", 40))
        self.margin = float(self.setting("margin", 0.15))
        self.points = tuple(self.setting("points", (10, 5, 3, 1)))

    # ------------------------------------------------------------------ season
    def draw_conditions(self, session: Session) -> Conditions:
        return Conditions(session.rng.choice(list(rules.DISTANCES)), session.rng.choice(list(rules.GOING)))

    def season(self, session: Session) -> dict[str, Any]:
        """The character's saved season, started fresh if there is none or the stable has changed."""
        season = session.db.load_game_state(session.character.id, self.game_key)
        if season is None or set(season["horses"]) != {horse.key for horse in self.horses}:
            season = new_season(1, self.horses, self.draw_conditions(session), None)
            session.db.save_game_state(session.character.id, self.game_key, season)
        return season

    def record_result(self, season: dict[str, Any], position: Mapping[str, int]) -> list[tuple[str, int, int]]:
        """Add a race to the season's records and let the stewards re-handicap. Returns the weight changes."""
        changes = []
        for horse in self.horses:
            record, place = season["horses"][horse.key], position[horse.key]
            record["starts"] += 1
            if place <= 3:
                record[("firsts", "seconds", "thirds")[place - 1]] += 1
            if place <= len(self.points):
                record["points"] += self.points[place - 1]
            record["recent"] = [*record["recent"], place][-FORM_LENGTH:]
            weight = rules.review_weight(record["weight"], record["recent"], self.handicap)
            if weight != record["weight"]:
                changes.append((horse.name, record["weight"], weight))
                record["weight"] = weight
        season["race"] += 1
        return changes

    def standings(self, season: dict[str, Any]) -> list[dict[str, Any]]:
        rows = [{"key": horse.key, "name": horse.name, "silks": horse.silks, **season["horses"][horse.key]}
                for horse in self.horses]
        rows.sort(key=lambda row: (-row["points"], -row["firsts"], -row["seconds"], row["name"]))
        return rows

    def odds(self, season: dict[str, Any]) -> list[dict[str, float | None]]:
        """The price on offer for each horse and bet in the season's next race."""
        conditions = Conditions(**season["conditions"])
        strengths = [rules.strength(horse, conditions, season["horses"][horse.key]["weight"], self.model)
                     for horse in self.horses]
        return [{kind: rules.offered_odds(chance, self.margin) for kind, chance in chances.items()}
                for chances in rules.finish_probabilities(strengths, self.model.spread)]

    # ------------------------------------------------------------------ info
    def rules_pages(self) -> list[list[str]]:
        hc = self.handicap
        places = ("1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th")
        points = ", ".join(f"{value} for {place}" for value, place in zip(self.points, places))
        return [
            [f"{len(self.horses)} horses race a {self.season_length}-race season for the stadium championship.",
             "Before each race, bet on as many horses as you like, in as many ways as you like:",
             "Win: your horse finishes first.",
             "Place: your horse finishes first or second.",
             "Show: your horse finishes in the first three.",
             "The odds on the board are fixed when you bet. A bet marked '-' is too likely to be worth a price."],
            ["Every horse has a base rating, a preferred trip (sprinter or stayer) and a preferred surface "
             "(firm ground or mud). Each race draws a distance and a going, so the favorite changes.",
             "On the day, each horse runs to its rating plus or minus some luck. The better horse usually wins, "
             "but not always, and the odds are worked out from exactly that mix.",
             "Running style only changes how the race unfolds: front-runners lead early, closers finish fast."],
            [f"Points: {points}.",
             f"The points leader after race {self.season_length} is champion, and a new season begins.",
             f"Handicapping: after every race the stewards look at each horse's last {hc.window} runs. A horse "
             f"that wins with {hc.hot_wins} or more wins in that span is winning too much and carries "
             f"{hc.penalty_lb} lb more, up to {hc.max_lb} lb. A weighted horse sheds {hc.relief_lb} lb each time "
             "it finishes outside the first three.",
             f"Every pound costs {self.model.weight_cost:g} rating points, so champions get reeled in."],
        ]

    def paytable(self) -> list[dict[str, Any]]:
        return [pay_section("Bets", [["Win", "1st"], ["Place", "1st or 2nd"], ["Show", "1st, 2nd or 3rd"]]),
                pay_section("Odds", [["Set from each horse's real chance", f"less {self.margin:.0%} for the house"],
                                     ["Longest price", format_ratio(rules.ODDS_LADDER[-1])],
                                     ["Shortest price", format_ratio(rules.ODDS_LADDER[0])]])]

    def layout(self) -> dict[str, Any]:
        return {"bets": [{"key": key, "label": label} for key, label in BET_NAMES.items()],
                "season_length": self.season_length}

    def betting_view(self, session: Session) -> dict[str, Any]:
        season = self.season(session)
        runners = []
        for horse, prices in zip(self.horses, self.odds(season)):
            record = season["horses"][horse.key]
            runners.append({"key": horse.key, "name": horse.name, "silks": horse.silks, "style": horse.style,
                            "weight": record["weight"], "recent": record["recent"],
                            "odds": {kind: price and format_ratio(price) for kind, price in prices.items()}})
        return {"season": season["season"], "race": season["race"] + 1, "champion": season["champion"],
                "conditions": season["conditions"], "runners": runners, "standings": self.standings(season)}

    # ------------------------------------------------------------------ round
    def start(self, session: Session, data: Mapping[str, Any]) -> RaceRound:
        raw_bets = data.get("bets")
        if not isinstance(raw_bets, list) or not raw_bets:
            raise BetError("Place at least one bet first.")
        prices = dict(zip((horse.key for horse in self.horses), self.odds(self.season(session))))
        names = {horse.key: horse.name for horse in self.horses}
        slip: dict[tuple[str, str], Bet] = {}
        for item in raw_bets:
            if not isinstance(item, Mapping):
                raise BetError("That bet isn't on the board.")
            key, kind = item.get("horse"), item.get("kind")
            if not isinstance(key, str) or not isinstance(kind, str) or key not in names or kind not in BET_NAMES:
                raise BetError("That bet isn't on the board.")
            if prices[key][kind] is None:
                raise BetError(f"There is no {BET_NAMES[kind]} price on {names[key]} for this race.")
            bet = slip.setdefault((key, kind), Bet(BET_NAMES[kind], 0, names[key]))
            add_stake(bet, item.get("amount"), self.table.min_bet, self.table.max_bet)
        self.take_stakes(session, sum(bet.amount for bet in slip.values()))
        return RaceRound(self, session, [(key, kind, bet, prices[key][kind]) for (key, kind), bet in slip.items()])
