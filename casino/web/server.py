"""HTTP front door: JSON API under /api, the single-page client under /."""
from __future__ import annotations

import json
import logging
import secrets
import socket
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from flask import Flask, Response, g, redirect, request
from ronovo_portfolio_auth import portfolio_sso
from ronovo_portfolio_auth.security_questions import QUESTIONS
from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler
from werkzeug.serving import make_server as make_wsgi_server

from casino import APP_NAME, APP_VERSION
from casino.accounts import LOGIN_LIFETIME, PORTFOLIO_CHOICE_SECONDS, AccountError, Accounts
from casino.config import ACHIEVEMENTS_PATH, DB_PATH, SECURE_COOKIES, TABLES_DIR, load_starting_chips, DIFFICULTIES
from casino.engine.chips import CHIP_VALUES
from casino.engine.db import Character, Database, User
from casino.engine.game import Game
from casino.games import load_games
from casino.web.floor import ApiError, Floor, Seat

STATIC_DIR = Path(__file__).resolve().parent / "static"
MIME_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
              ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".ico": "image/x-icon"}
COOKIE_NAME = "casino_login"
SSO_STATE_COOKIE = "casino_sso_state"
SSO_STATE_SECONDS = 600
PORTFOLIO_PENDING_COOKIE = "casino_portfolio_pending"
MAX_BODY_BYTES = 64 * 1024
MAX_DRAIN_BYTES = 1024 * 1024
JSON_TYPE = "application/json; charset=utf-8"
COMMON_HEADERS = {"X-Content-Type-Options": "nosniff"}
JSON_HEADERS = {"Cache-Control": "no-store"}
STATIC_HEADERS = {"Cache-Control": "no-cache"}


@dataclass
class Reply:
    body: dict[str, Any]
    status: int = 200
    # A new login token to store in the cookie, or "" to clear it. None leaves the cookie alone.
    token: str | None = None
    # The same for the code of a portfolio login waiting for the player to choose an account.
    pending: str | None = None


class CasinoApp:
    """Routes API requests to accounts and the floor. Knows nothing about sockets."""

    def __init__(self, db: Database, games: list[Game], floor: Floor | None = None):
        self.db = db
        self.accounts = Accounts(db)
        self.floor = floor or Floor(db, games)
        self._seated: dict[tuple[str, str], Callable[[Seat, Any], dict[str, Any]]] = {
            ("GET", "lobby"): lambda seat, data: self.floor.lobby(seat),
            ("GET", "profile"): lambda seat, data: self.floor.profile(seat),
            ("GET", "cashier"): lambda seat, data: self.floor.snapshot(seat),
            ("POST", "start-over"): lambda seat, data: self.floor.start_over(seat),
            ("POST", "cashier"): self.floor.exchange,
        }

    def dispatch(self, method: str, path: str, data: Any, token: str | None, pending: str | None = None) -> Reply:
        try:
            return self._route(method, [part for part in path.split("/") if part], data, token, pending)
        except ApiError as error:
            return Reply({"error": error.message}, error.status)
        except AccountError as error:
            return Reply({"error": str(error)}, 400)

    def _route(self, method: str, parts: list[str], data: Any, token: str | None, pending: str | None) -> Reply:
        if not isinstance(data, dict):
            raise ApiError(400, "Requests must be JSON objects.")
        login = self.accounts.resolve(token)
        route = (method, "/".join(parts))

        if route == ("GET", "session"):
            view = self._session_view(*login) if login else self._session_view(None, None)
            held = self.accounts.held_portfolio_login(pending)
            view["portfolio_pending"] = held[1] if held else None
            return Reply(view)
        if route == ("POST", "register"):
            return self._logged_in(self.accounts.register(data.get("username"), data.get("password"),
                                                          data.get("question"), data.get("answer")), token)
        if route == ("POST", "login"):
            return self._logged_in(self.accounts.authenticate(data.get("username"), data.get("password")), token)
        if route in (("POST", "portfolio/link"), ("POST", "portfolio/new")):
            held = self.accounts.held_portfolio_login(pending)
            if held is None:
                raise ApiError(400, "Log in with your portfolio account again.")
            sub, name = held
            if route[1] == "portfolio/link":
                user = self.accounts.authenticate(data.get("username"), data.get("password"))
                self.accounts.link_portfolio(user, sub)
            else:
                user = self.accounts.portfolio_user(sub, name)
            self.accounts.drop_portfolio_login(pending)
            return self._logged_in(user, token, pending="")
        if route == ("POST", "reset-question"):
            return Reply({"question": self.accounts.security_question(data.get("username"))})
        if route == ("POST", "reset-password"):
            self.accounts.reset_password(data.get("username"), data.get("answer"), data.get("password"))
            return Reply({"reset": True})
        if route == ("POST", "logout"):
            if token:
                self.accounts.logout(token)
            self.accounts.drop_portfolio_login(pending)
            return Reply(self._session_view(None, None), token="", pending="")

        if login is None:
            raise ApiError(401, "Log in to play.")
        user, character = login
        if route == ("POST", "characters"):
            created = self.accounts.create_character(user, data.get("name"), data.get("difficulty"))
            self.accounts.select_character(token, user, created.id)
            return Reply(self._session_view(user, created))
        if route == ("POST", "characters/select"):
            return Reply(self._session_view(user, self.accounts.select_character(token, user, data.get("id"))))

        if character is None:
            raise ApiError(409, "Choose a character first.")
        seat = self.floor.seat(character)
        with seat.lock:
            if route in self._seated:
                return Reply(self._seated[route](seat, data))
            if parts[:1] == ["tables"] and len(parts) in (2, 3):
                key, verb = parts[1], parts[2] if len(parts) == 3 else None
                if method == "GET" and verb is None:
                    return Reply(self.floor.table(seat, key))
                if method == "POST" and verb == "start":
                    return Reply(self.floor.start(seat, key, data.get("bets")))
                if method == "POST" and verb == "act":
                    return Reply(self.floor.act(seat, key, data.get("action")))
                if method == "POST" and verb == "leave":
                    return Reply(self.floor.leave(seat, key))
        raise ApiError(404, "Not found.")

    def answer(self, method: str, path: str, data: Any, token: str | None, pending: str | None = None) -> Reply:
        """`dispatch`, with any unexpected error logged and turned into a 500 reply."""
        try:
            return self.dispatch(method, path, data, token, pending)
        except Exception:
            traceback.print_exc()
            return Reply({"error": "Something went wrong at the table."}, 500)

    def _logged_in(self, user: User, old_token: str | None, pending: str | None = None) -> Reply:
        """A new login for the browser, which ends the one it had."""
        if old_token:
            self.accounts.logout(old_token)
        return Reply(self._session_view(user, None), token=self.accounts.issue_token(user), pending=pending)

    # ------------------------------------------------------------------ portfolio login
    def portfolio_authorize_url(self, base_url: str) -> tuple[str, str]:
        """Where to send the browser to log in with a portfolio account, and the state to hold in its cookie
        meanwhile. base_url is this app's address, ending in a slash."""
        if not portfolio_sso.enabled():
            raise ApiError(404, "Not found.")
        state = portfolio_sso.new_state()
        return portfolio_sso.authorize_url("casino", f"{base_url}{portfolio_sso.CALLBACK_PATH}", state), state

    def portfolio_callback(self, form: dict[str, str], expected_state: str | None, old_token: str | None = None) -> Reply:
        """Logs in to the casino account linked to the portfolio account, or holds the login until the player
        chooses one. Raises ApiError for a bad callback."""
        state = form.get("state", "")
        if not expected_state or not secrets.compare_digest(expected_state.encode(), state.encode()):
            raise ApiError(400, "Invalid portfolio login.")
        account = portfolio_sso.verify(form.get("token", ""), "casino")
        if account is None:
            raise ApiError(400, "Invalid portfolio login.")
        user = self.db.get_portfolio_user(account["sub"])
        if user is None:
            return Reply({}, pending=self.accounts.hold_portfolio_login(account["sub"], account["username"]))
        return self._logged_in(user, old_token)

    def _session_view(self, user: User | None, character: Character | None) -> dict[str, Any]:
        view: dict[str, Any] = {"app": APP_NAME, "user": None, "characters": [],
                                "portfolio": portfolio_sso.enabled(),
                                "portfolio_url": portfolio_sso.portfolio_url() if portfolio_sso.enabled() else None,
                                "questions": QUESTIONS,
                                "character": None, "chip_values": CHIP_VALUES,
                                "difficulties": [{"key": key, "label": f"{key} - {load_starting_chips(key).total:,} credits"}
                                                 for key in DIFFICULTIES]}
        if user:
            view["user"] = user.username
            credits = self.db.character_credits(user.id)
            view["characters"] = [{"id": c.id, "name": c.name, "difficulty": c.difficulty, "credits": credits[c.id]}
                                  for c in self.db.list_characters(user.id)]
            view["character"] = character.id if character else None
        return view


def static_file(url_path: str) -> tuple[str, bytes] | None:
    """Content type and bytes of a client file, or None if the path is outside the static folder or not served."""
    path = (STATIC_DIR / (url_path.lstrip("/") or "index.html")).resolve()
    if STATIC_DIR not in path.parents or not path.is_file() or path.suffix not in MIME_TYPES:
        return None
    return MIME_TYPES[path.suffix], path.read_bytes()


def parse_json_body(content_type: str, body: bytes) -> Any:
    # Browsers can't send JSON cross-site without a preflight, so this also blocks forged form posts.
    if content_type.split(";")[0].strip().lower() != "application/json":
        raise ApiError(415, "Send JSON.")
    try:
        return json.loads(body or b"{}")
    except (ValueError, RecursionError):
        raise ApiError(400, "Malformed JSON.") from None


def content_security_policy() -> str:
    """The page may also ask the portfolio which portfolio account the browser is logged in to."""
    connect = "'self'"
    if portfolio_sso.enabled():
        portfolio = urlsplit(portfolio_sso.portfolio_url())
        connect += f" {portfolio.scheme}://{portfolio.netloc}"
    return f"default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src {connect}; frame-ancestors 'none'"


def set_cookie(response: Response, name: str, value: str, max_age: int, path: str = "/",
               same_site: str = "Strict") -> None:
    """An empty value clears the cookie."""
    response.set_cookie(name, value, max_age=max_age if value else 0, path=path, httponly=True, samesite=same_site,
                        secure=SECURE_COOKIES)


def set_reply_cookies(response: Response, reply: Reply) -> Response:
    if reply.token is not None:
        set_cookie(response, COOKIE_NAME, reply.token, LOGIN_LIFETIME)
    if reply.pending is not None:
        set_cookie(response, PORTFOLIO_PENDING_COOKIE, reply.pending, PORTFOLIO_CHOICE_SECONDS)
    return response


def set_state_cookie(response: Response, state: str) -> Response:
    """Holds a portfolio login's state until its callback."""
    set_cookie(response, SSO_STATE_COOKIE, state, SSO_STATE_SECONDS, "/sso", "Lax")
    return response


def json_response(body: dict[str, Any], status: int = 200, close: bool = False) -> Response:
    headers = dict(JSON_HEADERS)
    if close:
        headers["Connection"] = "close"
    return Response(json.dumps(body), status, headers, content_type=JSON_TYPE)


def drain(length: int) -> None:
    """Read and throw away an oversized body, up to a limit, so the refusal can be delivered."""
    remaining = min(length, MAX_DRAIN_BYTES)
    while remaining > 0:
        chunk = request.stream.read(min(remaining, 64 * 1024))
        if not chunk:
            break
        remaining -= len(chunk)


def open_casino() -> CasinoApp:
    """The casino in the configured database, with every table loaded."""
    db = Database(DB_PATH)
    db.initialize(ACHIEVEMENTS_PATH)
    return CasinoApp(db, load_games(TABLES_DIR))


def create_app(casino: CasinoApp | None = None) -> Flask:
    """The web app around a casino. With no casino it opens the one in the configured database."""
    if casino is None:
        casino = open_casino()
    app = Flask(__name__, static_folder=None)

    @app.before_request
    def read_body() -> Response | None:
        if request.method != "POST":
            return None
        length = request.content_length
        if length is None:
            return json_response({"error": "Content-Length required."}, 411, close=True)
        if length > MAX_BODY_BYTES:
            drain(length)
            return json_response({"error": "Request too large."}, 413, close=True)
        # The body is read even for requests about to be refused: closing a socket with unread data resets
        # the connection, and the client would see that instead of the error message.
        g.body = request.get_data(cache=False)
        return None

    @app.after_request
    def common_headers(response: Response) -> Response:
        response.headers.update(COMMON_HEADERS)
        return response

    @app.route("/api/", defaults={"path": ""}, methods=["GET", "POST"])
    @app.route("/api/<path:path>", methods=["GET", "POST"])
    def api(path: str) -> Response:
        data: Any = {}
        if request.method == "POST":
            try:
                data = parse_json_body(request.headers.get("Content-Type", ""), g.body)
            except ApiError as error:
                return json_response({"error": error.message}, error.status)
        reply = casino.answer(request.method, path, data, request.cookies.get(COOKIE_NAME),
                              request.cookies.get(PORTFOLIO_PENDING_COOKIE))
        return set_reply_cookies(json_response(reply.body, reply.status), reply)

    @app.get("/sso/login")
    def sso_login() -> Response:
        try:
            location, state = casino.portfolio_authorize_url(request.host_url)
        except ApiError as error:
            return json_response({"error": error.message}, error.status)
        return set_state_cookie(redirect(location, 303), state)

    @app.post("/sso/callback")
    def sso_callback() -> Response:
        form = {key: values[0] for key, values in parse_qs(g.body.decode("utf-8", "replace")).items()}
        try:
            reply = casino.portfolio_callback(form, request.cookies.get(SSO_STATE_COOKIE),
                                              request.cookies.get(COOKIE_NAME))
        except ApiError as error:
            return json_response({"error": error.message}, error.status)
        return set_reply_cookies(set_state_cookie(redirect("/", 303), ""), reply)

    @app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
    @app.route("/<path:path>", methods=["GET", "POST"])
    def client(path: str) -> Response:
        if request.method == "POST":
            return json_response({"error": "Not found."}, 404)
        found = static_file(path)
        if found is None:
            return Response(b"Not found", 404, content_type="text/plain; charset=utf-8")
        content_type, payload = found
        return Response(payload, headers={**STATIC_HEADERS, "Content-Security-Policy": content_security_policy()},
                        content_type=content_type)

    return app


class RequestHandler(WSGIRequestHandler):
    # A client that stops sending mid-request frees its thread after this many seconds.
    timeout = 30


def make_server(casino: CasinoApp, host: str, port: int, verbose: bool = False) -> BaseWSGIServer:
    if not verbose:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
    return make_wsgi_server(host, port, create_app(casino), threaded=True, request_handler=RequestHandler)


def lan_address() -> str | None:
    """This machine's address on the local network, for telling other players where to connect."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            # Connecting a UDP socket sends nothing; it only makes the OS pick the outgoing interface.
            probe.connect(("10.255.255.255", 1))
            return probe.getsockname()[0]
    except OSError:
        return None


def serve(app: CasinoApp, host: str, port: int, verbose: bool = False) -> None:
    server = make_server(app, host, port, verbose)
    print(f"{APP_NAME} v{APP_VERSION} is open.")
    print(f"  On this computer:    http://localhost:{port}")
    if host in ("0.0.0.0", "::"):
        address = lan_address()
        if address:
            print(f"  For other players:   http://{address}:{port}")
    print("Press Ctrl+C to close the casino.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("\nThanks for playing!")
