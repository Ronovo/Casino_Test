# Ronovo's Casino
A repo for learning how to program casino games, played in the browser. One person runs the server; anyone on
the network can log in and play.

## Games Featured
Each game has one table, a JSON file in `Data/Tables`, played by Vegas rules.

| Table | Game | Highlights |
|---|---|---|
| Blackjack | Blackjack | Vegas rules: 6 decks, dealer hits soft 17, blackjack 3:2, double, split up to 4 hands including any two ten-value cards, surrender, insurance |
| Ultimate Texas Hold'em | Poker | Ante/Blind/Play, Trips and Pairs Bonus side bets, full kicker comparison |
| EZ Baccarat | Baccarat | Commission-free, Dragon 7 and Panda 8 bonus bets |
| Guess the Number | Guess the Number | Easy to Impossible, five bet types |
| Roulette | Roulette | American double-zero wheel: straight up, red/black, odd/even, low/high, dozens, columns |
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
  wrong answers lock resets for 15 minutes. A question can't be changed once it is set. Five wrong passwords in a
  row lock a username's logins for a minute.
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
  HTTPS reverse proxy and set `SECURE_COOKIES=1`, so the login cookies are only sent over HTTPS. The portfolio login
  callback address uses the scheme the request came in with. In the Docker image, gunicorn takes that from the
  proxy's `X-Forwarded-Proto` when `FORWARDED_ALLOW_IPS` trusts the proxy; `python main.py` always sees plain HTTP.

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

### Coverage
Python, after `pip install -r requirements-dev.txt` once:
```
python -m coverage run -m unittest discover -s Tests -t .
python -m coverage report
python -m coverage html
```
The browser client's tests (`Tests/js`) run on Node.js, after `npm install` once:
```
npm test
npm run coverage
```
Both cover every line and branch, and the coverage commands fail if that ever drops below 100%. The HTML reports,
which mark each line the tests run or miss, go to `coverage/python` and `coverage/js`.

The Docker image builds both reports and serves them at `/coverage/`, under a landing page that shows each
report's total and lists every measured file in one table: filter by name, sort by any column, or show only the
files with gaps, and click a file for its line-by-line page.

The page, its stylesheets and the tool that counts functions for the Python report live in `coverage-index/`, the
`ronovos-coverage-index` repository as a git submodule, the same in every project. This repo's own file is
`coverage-reports.json`, which names the project and its two reports. `coverage-index/README.md` has the recipe
for setting up another project.

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
Tests/                  Python tests; js/ holds the browser client's tests
coverage-index/         the coverage landing page, its stylesheets and the function-count tool, the same in any repo
                        (the ronovos-coverage-index repository, as a submodule)
coverage-reports.json   this repo's entry for that page: the project name and its two reports
Dockerfile
requirements.txt        Flask, PyJWT and ronovo-portfolio-auth (portfolio login, security questions, login lock)
requirements-dev.txt    the requirements plus coverage, for measuring the tests
package.json            the browser client's test tools (Vitest, jsdom)
```

## Adding a Table (new scenario, no code)
Copy a file in `Data/Tables`, change `key`, `title`, `order`, limits, `settings` and `paytable`.
It appears on the casino floor the next time the server starts. What each game reads:

| Game | `settings` | `paytable` |
|---|---|---|
| `blackjack` | `decks`, `dealer_stands_on`, `dealer_hits_soft_17`, `allow_double`, `double_after_split`, `allow_split`, `allow_surrender` | `win`, `natural` |
| `poker` | none | `blind` and `trips` by hand name, `pairs` by rank (`2-9` for the low pairs) |
| `baccarat` | `decks` | `player`, `banker`, `tie`, `dragon7`, `panda8` |
| `gtn` | `difficulties`, each a `name` and `max_number` | `exact`, `close`, `high_low`, `even_odd`, `range`, `lucky_1`, `lucky_2` |
| `roulette` | none | `straight`, `red_black`, `odd_even`, `low_high`, `dozen`, `column` |
| `racing` | `season_length`, `margin`, `points`, `model`, `handicap` | none |

## Adding a Game
1. Put the rules as pure functions in `casino/rules/<game>.py` and unit test them.
2. In `casino/games/<game>.py`, subclass `Round` (what happens after the bets are down: `actions`, `perform`
   and `table_view`) and `Game` (`rules_pages`, `paytable`, and `start`, which validates the bets with
   `read_stake` and returns the round, built with the total stake). Take later bets with `take`, pay out with
   `settle` and end the round with `finish`.
   `Game` also has optional hooks: `layout` (fixed details the client needs to draw the betting area),
   `betting_view` (details that change between rounds), `leave` (the player got up without betting) and
   `min_buy_in` (the least a player needs to sit down).
3. Register the class in `casino/games/__init__.py` and add a table JSON with `"game": "<game_key>"`.
4. Add `casino/web/static/js/games/<game>.js` exporting `render(ctx, mount)` and list it in `GAMES` in
   `js/app.js`.

## API
The browser client talks to the server in JSON under `/api/`. Every POST body must be sent as `application/json`.

| Route | What it does |
|---|---|
| `GET session` | The account, its characters and the login options |
| `POST register`, `POST login`, `POST logout` | Make an account, log in, log out |
| `POST reset-question`, `POST reset-password` | Look up an account's security question, then reset its password |
| `POST portfolio/link`, `POST portfolio/new` | After a first portfolio login: link an existing account, or make a new one |
| `POST characters`, `POST characters/select` | Make a character, or sit down as one (`"id": null` stands up) |
| `GET lobby`, `GET profile` | The tables, or the character's record and achievements |
| `GET cashier`, `POST cashier` | The chip rack, or break chips and color up |
| `POST start-over` | Fresh starting chips for a character who can't afford any table |
| `GET tables/<key>` | A table's rules, payouts, betting details and any round in progress |
| `POST tables/<key>/start`, `POST tables/<key>/act`, `POST tables/<key>/leave` | Place bets, make a move, get up from the table |

Logging in with a portfolio account goes through `GET /sso/login` and `POST /sso/callback`. The test coverage
reports are under `GET /coverage/`.

## Saves
Progress lives in `casino.db` next to `main.py` (set the `CASINO_DB` environment variable to use another file).

## Docker
The image runs the casino with gunicorn on port 8000, with one worker (seated players and their locks live in its
memory) and 8 threads. It keeps the database at `/app/data/casino.db`, so mount a volume at `/app/data` to keep it.
The app runs as its own user, which can write only to `/app/data`. A health check asks `/api/session` every 30
seconds, and `docker ps` shows the result.

Building the image runs both test suites to make the coverage reports at `/coverage/`. The tests and their tools
stay out of the final image, and failing tests or coverage under 100% don't stop the build: the reports show
what is missing.

| Variable | What it does |
|---|---|
| `CASINO_DB` | The database file. The image sets `/app/data/casino.db` |
| `SECURE_COOKIES` | `1` marks the login cookies Secure, for when the casino is served over HTTPS |
| `FORWARDED_ALLOW_IPS` | gunicorn's list of proxy addresses whose `X-Forwarded-Proto` it trusts (`*` when only the proxy can reach it) |
| `PORTFOLIO_SSO_URL` | The portfolio's address, for logging in with a portfolio account |
| `PORTFOLIO_SSO_PUBLIC_KEY` | The key that checks portfolio logins, printed by the portfolio's `python sso.py` |

## License

BSD 2-Clause. See [LICENSE](LICENSE).
