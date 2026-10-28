# Edge Case Report

How the games were tested, what broke, what was fixed, and what was left for you to decide.

## How it was tested

| Method | Where | What it covers |
|---|---|---|
| Scripted rounds with stacked decks and fixed numbers | `Tests/test_games.py`, `Tests/test_edge_cases.py`, `Tests/test_racing.py` | Every payout path in every game |
| Random soak: about 8,000 rounds with random legal moves | `Tests/test_soak.py` | After every single move: wallet = start - stake; after every round: wallet change = result shown, stats match, database matches memory |
| Shoestring soak: bankrolls of 1x, 2x and 5x the table minimum | `Tests/test_soak.py` | Unaffordable doubles, splits and raises; refused bets |
| Hostile input: 4,000 random malformed requests | `Tests/test_soak.py` | No crash, no status other than 200/400/404/409, no credit created or lost |
| 12 simultaneous all-in bets from one player | `Tests/test_soak.py` | No overdraw |
| Long-run frequencies vs published figures | `Tests/test_soak.py`, `Tests/test_racing.py` | Baccarat drawing rules, roulette coverage, racing odds |
| Real HTTP round trip | `Tests/test_web.py` | Cookies, logout, path traversal, oversized and malformed bodies |
| Client code run in Node against a live server with a stand-in DOM | not in the repo | Every screen and every game, including a full 40-race season |

Result: 159 tests pass. The client was **not** opened in a real browser, so layout and animation are unverified. See "For you to look at" at the bottom.

## Fixed: game rules

| # | Game | Problem | Fix | Test |
|---|---|---|---|---|
| 1 | Blackjack | After splitting Aces, Ace + ten was labelled "Blackjack!" although it is paid as a 21. Any 21 holding an Ace also read "21 (soft)". | Split hands show "21"; a 21 is never called soft. `total_view` in `casino/games/blackjack.py` | `test_two_card_21_after_a_split_is_not_called_blackjack` |
| 2 | Blackjack | Surrendering a 1 cr bet returned half rounded down: nothing. The option cost the whole bet. | Surrender is not offered on bets under 2 cr. | `test_surrender_is_not_offered_when_half_the_bet_is_nothing` |
| 3 | Ultimate Hold'em | A player could put every chip on Ante + Blind, leaving nothing for a Play bet. Every raise was unaffordable and the only move at the river was Fold: a guaranteed loss. | Dealing in needs Ante x3 in the rack (Ante, Blind, 1x Play). Table buy-in is now 3x the minimum. | `test_cannot_deal_in_without_chips_left_for_a_play_bet`, `test_buy_in_covers_ante_blind_and_play` |
| 4 | Roulette | Betting the same selection twice merged the bets without re-checking the table maximum, so 3 x 5,000 on one number was accepted. | Merged stakes are checked against the maximum (`add_stake` in `casino/engine/bets.py`, also used by racing). | `test_repeat_bets_on_one_selection_cannot_beat_the_table_maximum` |

## Fixed: problems that only exist once the casino is a multi-user web app

| # | Problem | Fix | Test |
|---|---|---|---|
| 5 | "Start over with fresh chips" checks for an empty wallet. With every chip on the table mid-hand the wallet is empty, so a player could collect fresh chips and then win the hand as well. | Starting over is refused while any round is in progress. | `test_start_over_only_when_broke_with_nothing_in_play` |
| 6 | Rounds live in memory. If the server stopped mid-hand, the stake was already out of the wallet and was lost. | Stakes on unfinished rounds are recorded (`OpenStakes` table) and handed back, with a notice, the next time that character sits down. | `test_stake_is_refunded_when_the_server_restarts_mid_round` |
| 7 | The games used Python's default generator, which can be reconstructed from enough observed results. Guess the Number on Impossible shows 27 bits per round and pays 50,000,000:1 for an exact pick. | Live tables draw from the operating system's secure generator. Tests still use seeded ones. | `test_live_tables_do_not_use_a_predictable_generator` |
| 8 | Two requests from the same player at the same moment could both read the same wallet. | Requests for one character run one at a time. | `test_simultaneous_all_in_bets_cannot_overdraw` |
| 9 | Malformed bets (strings, lists, negative, fractional, NaN, 10^30, nested objects) could reach game code. | All input is validated before any chip moves; bad input is a 400 with a readable message. | `test_garbage_never_crashes_the_server_or_moves_credits`, `ReadStakeTests` |
| 10 | The dealer's hole card and unseen board cards must never reach the browser. | Face-down cards are sent as `null`. | `test_views_never_leak_face_down_cards` |
| 11 | Optional parts of a screen printed the word "false" (the browser's `append` prints non-elements). | All screens build through one helper that skips them (`add` in `js/dom.js`). | Found by the Node client run |
| 12 | Every round re-sent 5 to 10 achievement unlocks to the database, each a separate write. | Unlocks already earned are remembered per session. | Deep-bankroll soak run fell from 159 s to 72 s |
| 13 | Result panels are held back until the cards or wheel finish, but were invisible and still clickable. | Hidden panels ignore clicks. | Not automatically tested |
| 14 | A request refused for its size or content type was answered without reading its body. On Windows that resets the connection, so the browser saw a network error instead of the message. It showed up as a test that failed about one run in three. | The body is read (oversized ones are drained up to 1 MB) before the refusal is sent. | `test_malformed_requests`, 20 clean runs in a row |

## Fixed: found while building horse racing

| # | Problem | Fix | Test |
|---|---|---|---|
| 15 | First handicap rule added weight to any horse with 3 wins in its last 8 on *every* review, so a horse kept gaining weight for five races after a streak, while losing. A full-season run showed a horse at +24 lb finishing 8th, 8th, 8th. | Weight now goes on only when a horse with 2 or more wins in its last 8 wins again (+6 lb), and comes off 1 lb per finish outside the first three. | `HandicapRuleTests`, `test_handicapping_reins_in_the_best_horse_without_making_ability_irrelevant` |
| 16 | Rounding a price up, or pricing a near-certainty, would hand the player an edge. | Prices are rounded down a fixed ladder, and anything too likely to price is not offered. | `test_no_price_ever_favors_the_player`, `test_the_house_keeps_an_edge_on_every_kind_of_bet` |

Effect of handicapping over 400 simulated seasons:

| | Best horse's wins per season | Best horse wins the title | Most wins by any horse (avg / max) |
|---|---|---|---|
| No handicapping | 13.1 of 40 | 93% | 13.5 / 23 |
| With handicapping | 8.0 of 40 | 67% | 8.4 / 12 |

## Checked and found correct

- Money is conserved in every game across all soak rounds, including splits, doubles, raises, folds and surrender.
- Baccarat over 60,000 coups: Banker 45.9%, Player 44.6%, Tie 9.5%, Dragon 7 2.25%, Panda 8 3.45%, all within 0.6 points of the published figures.
- Roulette: every outside bet covers exactly 18 or 12 pockets on both wheels; zeros pay only straight-up.
- Racing: win, place and show frequencies over 40,000 simulated races match the calculated probabilities to within 0.8 points for every horse.
- Chip change-making (`Chips.split_off`) never loses or creates a credit.

## Left as is: your call

These work as coded. They are balance or policy choices, so I did not change them.

| | What | Numbers | If you want to change it |
|---|---|---|---|
| A | **Guess the Number, "Pick a Number" favors the player.** Exact plus the "close" payout add up to more than the losing chance. | Player edge +20% on Easy, +11% Medium, +10% Hard | `"close": 1` in `Data/Tables/06_guess_the_number.json` gives 0%, -9%, -10% |
| B | **Blackjack: Ronovo Classic favors the player.** Naturals pay 2:1 and any winning 21 pays 2:1. The table description calls these the original house rules, so I took it as intended. | +8.1% to the player over 30,000 hands with a crude hit-to-17 strategy. High Roller: -4.8% with the same strategy | `natural` and `twenty_one` in `Data/Tables/01_blackjack_classic.json` |
| C | Guess the Number High/Low and Even/Odd pay 1:1 on a 50% chance: no house edge. | 0% | Paytable |
| D | Blackjack pairs are matched by rank, so 10 + King cannot be split. | | `can_split` in `casino/rules/blackjack.py` |
| E | Surrender on an odd bet returns half rounded down (5 cr returns 2). | | |
| F | Racing: a 1 cr bet at 1:20 wins 0 because winnings round down. | | |
| G | The server speaks plain HTTP. On a home network that is normal; over the internet, passwords would travel unencrypted. | | Put it behind an HTTPS reverse proxy |
| H | Five wrong passwords lock an account for 60 seconds, which also lets someone lock *your* account for 60 seconds by guessing. | | `MAX_FAILURES`, `LOCKOUT_SECONDS` in `casino/accounts.py` |
| I | Characters saved before accounts existed (your "Ronovo") belong to nobody until claimed. | | Register in the app, then `python main.py --claim "Ronovo" <username>` |

## For you to look at in a browser

I could not look at the pages. Worth a glance:

1. Card deal and flip animations on blackjack, hold'em and baccarat.
2. Roulette: the wheel should stop with the winning number under the white pointer, and the hub should show that number.
3. Racing: horses run left to right and cross the checkered line in the finishing order; place badges appear as each horse gets home.
4. Chip stacks on betting spots, and the layout on a narrow window.
