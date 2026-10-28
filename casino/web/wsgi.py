"""WSGI entry point, so the casino can be mounted inside another web app (for example under /games/casino)."""
from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any, Callable, Iterable

from casino.config import ACHIEVEMENTS_PATH, DB_PATH, TABLES_DIR
from casino.engine.db import Database
from casino.games import load_games
from casino.web.floor import ApiError
from casino.web.server import (COMMON_HEADERS, JSON_HEADERS, JSON_TYPE, MAX_BODY_BYTES, STATIC_HEADERS, CasinoApp,
                               login_cookie, login_token, parse_json_body, static_file)


class CasinoWSGI:
    def __init__(self, app: CasinoApp):
        self.app = app

    def __call__(self, environ: dict[str, Any], start_response: Callable) -> Iterable[bytes]:
        method, path = environ["REQUEST_METHOD"], environ.get("PATH_INFO", "")
        if method not in ("GET", "POST"):
            return self._send(start_response, 501, "text/plain; charset=utf-8", b"Unsupported method")
        if not path:
            # The client uses relative URLs, so the page only works with a trailing slash.
            return self._send(start_response, 308, "text/plain; charset=utf-8", b"",
                              {"Location": environ.get("SCRIPT_NAME", "") + "/"})
        if path.startswith("/api/"):
            return self._api(environ, start_response, method, path[len("/api/"):])
        found = static_file(path) if method == "GET" else None
        if found is None:
            return self._send(start_response, 404, "text/plain; charset=utf-8", b"Not found")
        return self._send(start_response, 200, *found, STATIC_HEADERS)

    def _api(self, environ: dict[str, Any], start_response: Callable, method: str, path: str) -> Iterable[bytes]:
        data: Any = {}
        if method == "POST":
            try:
                length = int(environ.get("CONTENT_LENGTH") or "")
            except ValueError:
                return self._json(start_response, {"error": "Content-Length required."}, 411)
            if not 0 <= length <= MAX_BODY_BYTES:
                return self._json(start_response, {"error": "Request too large."}, 413)
            try:
                data = parse_json_body(environ.get("CONTENT_TYPE", ""), environ["wsgi.input"].read(length))
            except ApiError as error:
                return self._json(start_response, {"error": error.message}, error.status)
        reply = self.app.answer(method, path, data, login_token(environ.get("HTTP_COOKIE", "")))
        cookie = {} if reply.token is None else {"Set-Cookie": login_cookie(reply.token)}
        return self._json(start_response, reply.body, reply.status, cookie)

    def _json(self, start_response: Callable, body: dict[str, Any], status: int,
              headers: dict[str, str] | None = None) -> Iterable[bytes]:
        return self._send(start_response, status, JSON_TYPE, json.dumps(body).encode("utf-8"),
                          {**JSON_HEADERS, **(headers or {})})

    @staticmethod
    def _send(start_response: Callable, status: int, content_type: str, payload: bytes,
              headers: dict[str, str] | None = None) -> Iterable[bytes]:
        start_response(f"{status} {HTTPStatus(status).phrase}",
                       [("Content-Type", content_type), ("Content-Length", str(len(payload))),
                        *{**COMMON_HEADERS, **(headers or {})}.items()])
        return [payload]


def create_app() -> CasinoWSGI:
    db = Database(DB_PATH)
    db.initialize(ACHIEVEMENTS_PATH)
    return CasinoWSGI(CasinoApp(db, load_games(TABLES_DIR)))
