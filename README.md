# Ronovo's Casino
A repo for learning how to program casino games, played in the browser. One person runs the server; anyone on
the network can log in and play.

## Games Featured
Each table is a JSON file in `Data/Tables`. Several tables can share one game engine.

| Table | Game | Highlights |
|---|---|---|
| Blackjack: Ronovo Classic | Blackjack | Any winning 21 pays 2:1, natural with a black Jack pays 3:1, double, split, surrender |
| Blackjack: High Roller | Blackjack | 6 decks, dealer hits soft 17, blackjack 3:2, 100 cr minimum |
| Ultimate Texas Hold'em (+ High Roller) | Poker | Ante/Blind/Play, Trips and Pairs Bonus side bets, full kicker comparison |
| EZ Baccarat | Baccarat | Commission-free, Dragon 7 and Panda 8 bonus bets |
| Guess the Number | Guess the Number | Easy to Impossible, five bet types |
| Roulette: European / American | Roulette | Straight up, red/black, odd/even, low/high, dozens, columns |
| Ronovo Downs: Horse Racing | Horse Racing | Win/Place/Show on any number of horses, 40-race season, standings, handicapping |

Also included: accounts, achievements, per-game win/loss records, a chip exchange, and a fresh start for broke
characters.

## Future Ideas
- Day Trading, Big 6 Wheel
- Day/Night cycle (a certain number of games a day)

## How To Run
- Install Python 3.10 or newer (no extra packages needed)
- From a terminal: `python main.py`
- Open the address it prints. `http://localhost:8000` on your own computer; other players use the
  "For other players" address (your computer's address on the local network). Windows may ask once to allow
  Python through the firewall.

```
python main.py --port 8080          # a different port
python main.py --host 127.0.0.1     # private: only this computer can connect
python main.py --verbose            # log every request
```

## Accounts and Characters
- Each player creates an account (username and password) on the login page. Passwords are stored as salted
  PBKDF2 hashes, and a login lasts 30 days per browser.
- An account holds up to 8 characters. Each character has its own chips, record, achievements and racing season.
- Characters saved before accounts existed belong to nobody. Register an account, then hand one over:
  `python main.py --claim "Ronovo Ronove" your_username`
- The server uses plain HTTP, which is fine on a home network. To open it to the internet, put it behind an
  HTTPS reverse proxy.

## Horse Racing
- Every horse in `Data/horses.json` has a rating, a preferred trip (sprinter or stayer), a preferred surface
  (firm or mud) and a running style. Each race draws a distance and a going.
- A horse runs to its strength on the day plus random luck. The luck is Gumbel-distributed, which makes the
  chance of every finishing order exactly calculable, so the prices on the board come from real probabilities
  less the house margin (`margin` in the table file).
- A season is 40 races. Points are 10/5/3/1 for the first four; the standings are shown before and after
  every race, and the leader after race 40 is champion.
- Handicapping: a horse that wins with 2 or more wins in its last 8 runs carries 6 lb more (up to 30 lb), and
  each pound costs half a rating point. A weighted horse sheds 1 lb for every finish outside the first three.
  All of these numbers are in `Data/Tables/09_horse_racing.json`.

## Tests
```
python -m unittest discover -s Tests -t .
```
Game rules are pure functions (`casino/rules`). Full rounds are played through each game's `start`/`act`
interface with stacked decks (`Tests/test_games.py`), thousands of random rounds check that no credit is ever
created or lost (`Tests/test_soak.py`), and `EDGE_CASES.md` lists what that turned up.

## Project Layout
```
main.py                 entry point: starts the web server
casino/
  accounts.py           sign-up, password hashing, login tokens, character ownership
  cashier.py            chip exchange maths (break / color up)
  transfer.py           character JSON export/import
  engine/               shared engine used by every game
    chips.py            chip values, Chips type, change-making
    cards.py            Card and Shoe
    bets.py             Bet, Outcome, stake validation, settle(): the one place winnings are paid
    wallet.py           a character's chip rack (saved on every change)
    game.py             Game and Round base classes + TableConfig
    session.py          database, character, wallet, randomness and achievements for one sitting
    db.py               SQLite schema, migrations, accounts, stats, achievements, saved seasons
  rules/                pure rules per game (no input/output, no database)
  games/                games wired from rules + engine; registry in __init__.py
  web/
    floor.py            every request a seated player can make, as plain functions returning JSON
    server.py           HTTP server, routing, cookies, static files
    static/             the browser client: index.html, css/, js/ (one module per game in js/games/)
Data/
  Tables/*.json         one file per table (scenario)
  horses.json           the racing stable
  achievements.json     achievement definitions (edits reach existing saves)
  Money/chips.json      starting chips per difficulty
CharacterTool/          export/import scripts
Tests/
```

## Adding a Table (new scenario, no code)
Copy a file in `Data/Tables`, change `key`, `title`, `order`, limits, `settings` and `paytable`.
It appears on the casino floor the next time the server starts.

## Adding a Game
1. Put the rules as pure functions in `casino/rules/<game>.py` and unit test them.
2. In `casino/games/<game>.py`, subclass `Round` (what happens after the bets are down: `actions`, `perform`,
   `table_view`, `staked`) and `Game` (`rules_pages`, `paytable`, and `start`, which validates the bets with
   `read_stake`, takes them with `take_stakes` and returns the round). Pay out with `settle` and end the round
   with `finish`.
3. Register the class in `casino/games/__init__.py` and add a table JSON with `"game": "<game_key>"`.
4. Add `casino/web/static/js/games/<game>.js` exporting `render(ctx, mount)` and list it in `GAMES` in
   `js/app.js`.

## Character Tool
```
python CharacterTool/export_character.py "Ronovo Ronove"
python CharacterTool/import_character.py "CharacterTool/Character/Ronovo Ronove.json" [--name "New Name"]
```
Exports from before version 2.0 still import (chips, blackjack/poker records and achievements). An imported
character has no owner until it is claimed with `python main.py --claim`.

## Saves
Progress lives in `casino.db` next to `main.py` (set the `CASINO_DB` environment variable to use another file).
Older databases upgrade automatically on launch: characters, chips and achievements are kept.
