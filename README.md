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
- Install Python 3.10 or newer
- Install the requirements once: `pip install -r requirements.txt` (the casino needs them to start)
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
- Each player creates an account (username and password) on the login page, and picks a security question.
  Passwords and answers are stored as salted PBKDF2 hashes, and a login lasts 30 days per browser.
- **Forgot password?** resets the password with the security answer and logs the account out everywhere. Five
  wrong answers lock resets for 15 minutes. A question can't be changed once it is set. Five wrong passwords in a row lock a username's logins for a
  minute.
- With `PORTFOLIO_SSO_URL` (the portfolio's address) and `PORTFOLIO_SSO_PUBLIC_KEY`
  (printed by the portfolio's `python sso.py`) set, the login page offers to log in with a portfolio account. It
  reads **Log in as** and the portfolio username when this browser is logged in to the portfolio. The first
  portfolio login here asks whether to link a casino account the player already has, by logging in to it once,
  or to make a new one named after the portfolio username, with a number added if that name is taken. Every later
  portfolio login from any device opens the linked account. A new account has no password of its own, so the
  portfolio is the only way into it. Without those two settings the app runs on its own.
- An account holds up to 8 characters. Each character has its own chips, record, achievements and racing season.
- Usernames are public: registering says when one is taken, and **Forgot password?** says when there is no such
  account. At most 20 accounts can be made in any 10 minutes.
- The server uses plain HTTP, which is fine on a home network. To open it to the internet, put it behind an
  HTTPS reverse proxy; the portfolio login callback address and the login cookie are still built for plain HTTP.

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
The tests need the requirements installed. Game rules are pure functions (`casino/rules`). Full rounds are played
through each game's `start`/`act` interface with stacked decks (`Tests/test_games.py`), and thousands of random
rounds check that no credit is ever created or lost (`Tests/test_soak.py`). The longest of those soak tests take
about 100 seconds, so they only run with `CASINO_SOAK=1` set.

## Project Layout
```
main.py                 entry point: starts the web server
casino/
  config.py             paths, difficulties, starting chips
  accounts.py           sign-up, password hashing, login tokens, character ownership
  cashier.py            chip exchange maths (break / color up)
  engine/               shared engine used by every game
    chips.py            chip values, Chips type, change-making
    cards.py            Card and Shoe
    bets.py             Bet, Outcome, stake validation, settle(): the one place winnings are paid
    wallet.py           a character's chip rack (saved on every change)
    game.py             Game and Round base classes + TableConfig
    session.py          database, character, wallet, randomness and achievements for one sitting
    db.py               SQLite schema, accounts, stats, achievements, saved per-table state
  rules/                pure rules per game (no input/output, no database)
  games/                games wired from rules + engine; registry in __init__.py
  web/
    floor.py            every request a seated player can make, as plain functions returning JSON
    server.py           Flask app: routing, cookies, static files
    static/             the browser client: index.html, css/, js/ (one module per game in js/games/)
Data/
  Tables/*.json         one file per table (scenario)
  horses.json           the racing stable
  achievements.json     achievement definitions (edits reach existing saves)
  Money/chips.json      starting chips per difficulty
Tests/
docker/git-sync.sh      updates the container from GitHub on start
Dockerfile
requirements.txt        PyJWT and ronovo-portfolio-auth (portfolio login, security questions, login lock)
```

## Adding a Table (new scenario, no code)
Copy a file in `Data/Tables`, change `key`, `title`, `order`, limits, `settings` and `paytable`.
It appears on the casino floor the next time the server starts.

## Adding a Game
1. Put the rules as pure functions in `casino/rules/<game>.py` and unit test them.
2. In `casino/games/<game>.py`, subclass `Round` (what happens after the bets are down: `actions`, `perform`
   and `table_view`) and `Game` (`rules_pages`, `paytable`, and `start`, which validates the bets with
   `read_stake` and returns the round, built with the total stake). Take later bets with `take`, pay out with
   `settle` and end the round with `finish`.
3. Register the class in `casino/games/__init__.py` and add a table JSON with `"game": "<game_key>"`.
4. Add `casino/web/static/js/games/<game>.js` exporting `render(ctx, mount)` and list it in `GAMES` in
   `js/app.js`.

## Saves
Progress lives in `casino.db` next to `main.py` (set the `CASINO_DB` environment variable to use another file).

## Docker
The image serves on port 8000 and keeps the database at `/app/data/casino.db` (`CASINO_DB`), so mount a volume
at `/app/data` to keep it.

On every start the container runs `docker/git-sync.sh` before the server. It fetches the latest commit on GitHub
`main`, so a pushed commit goes live on the next restart without rebuilding the image. When that commit hasn't
been built yet it reinstalls `requirements.txt` first, and a failed install is tried again on the next start. If
GitHub can't be reached the server starts on the code it already has.

| Variable | What it does | Default in the image |
|---|---|---|
| `REPO_URL` | The repo to pull. Set it empty to run exactly what is in the image. | This repo on GitHub |
| `REPO_BRANCH` | Branch to pull | `main` |
| `SYNC_DIR` | Folder the code is pulled into | The app folder |
| `BUILD_CMD` | Runs after pulling a commit that hasn't been built yet | `pip install --no-cache-dir --user -q -r requirements.txt` |

## License

BSD 2-Clause. See [LICENSE](LICENSE).
