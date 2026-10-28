"""HTTP front door: JSON API under /api, the single-page client under /."""
from __future__ import annotations

import json
import secrets
import socket
import traceback
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs

from casino import APP_NAME, APP_VERSION, ronovo_sso
from casino.security_questions import QUESTIONS
from casino.accounts import LOGIN_LIFETIME, AccountError, Accounts
from casino.config import DIFFICULTIES
from casino.engine.chips import CHIP_VALUES
from casino.engine.db import Character, Database, User
from casino.engine.game import Game
from casino.web.floor import ApiError, Floor, Seat

STATIC_DIR = Path(__file__).resolve().parent / "static"
MIME_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
              ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".ico": "image/x-icon"}
COOKIE_NAME = "casino_login"
SSO_STATE_COOKIE = "casino_sso_state"
SSO_STATE_SECONDS = 600
MAX_BODY_BYTES = 64 * 1024
MAX_DRAIN_BYTES = 1024 * 1024
CONTENT_SECURITY_POLICY = "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
JSON_TYPE = "application/json; charset=utf-8"
COMMON_HEADERS = {"X-Content-Type-Options": "nosniff"}
JSON_HEADERS = {"Cache-Control": "no-store"}
STATIC_HEADERS = {"Cache-Control": "no-cache", "Content-Security-Policy": CONTENT_SECURITY_POLICY}


@dataclass
class Reply:
    body: dict[str, Any]
    status: int = 200
    # A new login token to store in the cookie, or "" to clear it. None leaves the cookie alone.
    token: str | None = None


class CasinoApp:
    """Routes API requests to accounts and the floor. Knows nothing about sockets."""

    def __init__(self, db: Database, games: list[Game], floor: Floor | None = None):
        self.db = db
        self.accounts = Accounts(db)
        self.floor = floor or Floor(db, games)
        self._seated: dict[tuple[str, str], Callable[[Seat, Any], dict[str, Any]]] = {
            ("GET", "lobby"): lambda seat, data: self.floor.lobby(seat),
            ("GET", "profile"): lambda seat, data: self.floor.profile(seat),
            ("POST", "start-over"): lambda seat, data: self.floor.start_over(seat),
            ("POST", "cashier"): self.floor.exchange,
        }

    def dispatch(self, method: str, path: str, data: Any, token: str | None) -> Reply:
        try:
            return self._route(method, [part for part in path.split("/") if part], data, token)
        except ApiError as error:
            return Reply({"error": error.message}, error.status)
        except AccountError as error:
            return Reply({"error": str(error)}, 400)

    def _route(self, method: str, parts: list[str], data: Any, token: str | None) -> Reply:
        if not isinstance(data, dict):
            raise ApiError(400, "Requests must be JSON objects.")
        login = self.accounts.resolve(token)
        route = (method, "/".join(parts))

        if route == ("GET", "session"):
            return Reply(self._session_view(*login) if login else self._session_view(None, None))
        if route in (("POST", "register"), ("POST", "login")):
            if route[1] == "register":
                self.accounts.register(data.get("username"), data.get("password"), data.get("question"),
                                       data.get("answer"))
            new_token = self.accounts.login(data.get("username"), data.get("password"))
            user, character = self.accounts.resolve(new_token)
            view = self._session_view(user, character)
            # Accounts made before security questions are asked to set one straight after logging in.
            view["needs_security_question"] = not self.accounts.has_security_question(user)
            return Reply(view, token=new_token)
        if route == ("POST", "reset-question"):
            return Reply({"question": self.accounts.security_question(data.get("username"))})
        if route == ("POST", "reset-password"):
            self.accounts.reset_password(data.get("username"), data.get("answer"), data.get("password"))
            return Reply({"reset": True})
        if route == ("POST", "logout"):
            if token:
                self.accounts.logout(token)
            return Reply(self._session_view(None, None), token="")

        if login is None:
            raise ApiError(401, "Log in to play.")
        user, character = login
        if route == ("POST", "security-question"):
            self.accounts.set_security_question(user, data.get("question"), data.get("answer"))
            return Reply(self._session_view(user, character))
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

    def answer(self, method: str, path: str, data: Any, token: str | None) -> Reply:
        """`dispatch`, with any unexpected error logged and turned into a 500 reply."""
        try:
            return self.dispatch(method, path, data, token)
        except Exception:
            traceback.print_exc()
            return Reply({"error": "Something went wrong at the table."}, 500)

    # ------------------------------------------------------------------ Ronovo login
    def ronovo_authorize_url(self, host: str) -> tuple[str, str]:
        """Where to send the browser to log in with Ronovo, and the state to hold in its cookie meanwhile."""
        if not ronovo_sso.enabled():
            raise ApiError(404, "Not found.")
        state = ronovo_sso.new_state()
        return ronovo_sso.authorize_url("casino", f"http://{host}/sso/callback", state), state

    def ronovo_callback(self, form: dict[str, str], expected_state: str | None) -> str:
        """A login token for the casino account tied to the Ronovo account. Raises ApiError for a bad callback."""
        state = form.get("state", "")
        if not expected_state or not secrets.compare_digest(expected_state, state):
            raise ApiError(400, "Invalid Ronovo login.")
        account = ronovo_sso.verify(form.get("token", ""), "casino")
        if account is None:
            raise ApiError(400, "Invalid Ronovo login.")
        return self.accounts.issue_token(self.accounts.ronovo_user(account["sub"], account["username"]))

    def _session_view(self, user: User | None, character: Character | None) -> dict[str, Any]:
        view: dict[str, Any] = {"app": APP_NAME, "version": APP_VERSION, "user": None, "characters": [],
                                "ronovo": ronovo_sso.enabled(), "questions": QUESTIONS,
                                "character": None, "chip_values": CHIP_VALUES,
                                "difficulties": [{"key": key, "label": label}
                                                 for key, (label, _) in DIFFICULTIES.items()]}
        if user:
            view["user"] = user.username
            view["characters"] = [{"id": c.id, "name": c.name, "difficulty": c.difficulty,
                                   "credits": self.db.load_chips(c.id).total}
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


def read_cookie(cookie_header: str, name: str) -> str | None:
    try:
        cookie = SimpleCookie(cookie_header)
    except CookieError:
        return None
    return cookie[name].value if name in cookie else None


def login_cookie(token: str) -> str:
    """Set-Cookie value storing a login token, or clearing it when `token` is ""."""
    age = LOGIN_LIFETIME if token else 0
    return f"{COOKIE_NAME}={token}; Path=/; Max-Age={age}; HttpOnly; SameSite=Strict"


def state_cookie(state: str) -> str:
    """Set-Cookie value holding a Ronovo login's state until its callback, or clearing it when `state` is ""."""
    age = SSO_STATE_SECONDS if state else 0
    return f"{SSO_STATE_COOKIE}={state}; Path=/sso; Max-Age={age}; HttpOnly; SameSite=Lax"


class CasinoHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "RonovoCasino"
    app: CasinoApp

    def do_GET(self) -> None:
        if self.path.split("?")[0].startswith("/api/"):
            self._api({})
        elif self.path.split("?")[0] == "/sso/login":
            self._sso_login()
        else:
            self._static()

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._json({"error": "Content-Length required."}, 411, close=True)
        if not 0 <= length <= MAX_BODY_BYTES:
            self._drain(length)
            return self._json({"error": "Request too large."}, 413, close=True)
        # The body is read even for requests about to be refused: closing a socket with unread data resets
        # the connection, and the client would see that instead of the error message.
        body = self.rfile.read(length)
        if self.path == "/sso/callback":
            return self._sso_callback(body)
        if not self.path.startswith("/api/"):
            return self._json({"error": "Not found."}, 404)
        try:
            data = parse_json_body(self.headers.get("Content-Type", ""), body)
        except ApiError as error:
            return self._json({"error": error.message}, error.status)
        self._api(data)

    def _drain(self, length: int) -> None:
        """Read and throw away an oversized body, up to a limit, so the refusal can be delivered."""
        remaining = min(max(length, 0), MAX_DRAIN_BYTES)
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 64 * 1024))
            if not chunk:
                break
            remaining -= len(chunk)

    def _api(self, data: Any) -> None:
        path = self.path.split("?")[0][len("/api/"):]
        reply = self.app.answer(self.command, path, data, read_cookie(self.headers.get("Cookie", ""), COOKIE_NAME))
        self._json(reply.body, reply.status, None if reply.token is None else login_cookie(reply.token))

    def _sso_login(self) -> None:
        try:
            location, state = self.app.ronovo_authorize_url(self.headers.get("Host", ""))
        except ApiError as error:
            return self._json({"error": error.message}, error.status)
        self._redirect(location, [state_cookie(state)])

    def _sso_callback(self, body: bytes) -> None:
        form = {key: values[0] for key, values in parse_qs(body.decode("utf-8", "replace")).items()}
        expected = read_cookie(self.headers.get("Cookie", ""), SSO_STATE_COOKIE)
        try:
            token = self.app.ronovo_callback(form, expected)
        except ApiError as error:
            return self._json({"error": error.message}, error.status)
        self._redirect("/", [state_cookie(""), login_cookie(token)])

    def _redirect(self, location: str, cookies: list[str]) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        for name, value in COMMON_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()

    def _json(self, body: dict[str, Any], status: int = 200, cookie: str | None = None, close: bool = False) -> None:
        headers = dict(JSON_HEADERS)
        if cookie:
            headers["Set-Cookie"] = cookie
        if close:
            headers["Connection"] = "close"
            self.close_connection = True
        self._send(status, JSON_TYPE, json.dumps(body).encode("utf-8"), headers)

    def _static(self) -> None:
        found = static_file(self.path.split("?")[0])
        if found is None:
            return self._send(404, "text/plain; charset=utf-8", b"Not found")
        self._send(200, *found, STATIC_HEADERS)

    def _send(self, status: int, content_type: str, payload: bytes, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        for name, value in {**COMMON_HEADERS, **(headers or {})}.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        if self.server.verbose:
            super().log_message(format, *args)


class CasinoServer(ThreadingHTTPServer):
    daemon_threads = True
    verbose = False


def make_server(app: CasinoApp, host: str, port: int, verbose: bool = False) -> CasinoServer:
    handler = type("BoundCasinoHandler", (CasinoHandler,), {"app": app})
    server = CasinoServer((host, port), handler)
    server.verbose = verbose
    return server


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
