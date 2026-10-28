"""Ronovo's Casino. Run with: python main.py"""
import argparse
import sys

from casino.accounts import AccountError, Accounts
from casino.config import ACHIEVEMENTS_PATH, DB_PATH, TABLES_DIR
from casino.engine.db import Database
from casino.games import load_games
from casino.web.server import CasinoApp, serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the casino web server.")
    parser.add_argument("--host", default="0.0.0.0",
                        help="address to listen on; 127.0.0.1 keeps the casino private to this computer")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--verbose", action="store_true", help="log every request")
    parser.add_argument("--claim", nargs=2, metavar=("CHARACTER", "USERNAME"),
                        help="give a character saved before accounts existed to a registered user, then exit")
    args = parser.parse_args()

    db = Database(DB_PATH)
    db.initialize(ACHIEVEMENTS_PATH)
    if args.claim:
        try:
            character = Accounts(db).claim_character(*args.claim)
        except AccountError as error:
            sys.exit(f"ERROR: {error}")
        print(f"'{character.name}' now belongs to {args.claim[1]}.")
        return
    serve(CasinoApp(db, load_games(TABLES_DIR)), args.host, args.port, args.verbose)


if __name__ == "__main__":
    main()
