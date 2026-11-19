"""Local HTTP API and chat page.

Run from the project root:

    python -m supportchat.web
"""

from __future__ import annotations

import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from supportchat.agents.memory_agent import MemoryAgent
from supportchat.helplines import country_choices, crisis_resources, normalize_country, page_summary
from supportchat.memory import AuthError, MemoryStore
from supportchat.model import writer_from_environment
from supportchat.safety import ABUSE_RESOURCES, MEDICAL_RESOURCES
from supportchat.service import BOUNDARY, handle_turn
from supportchat.session import MAX_MESSAGE_CHARS

_STATIC = Path(__file__).resolve().parent.parent / "static"
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "support.sqlite"
BIND_HOST = "127.0.0.1"
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_WINDOW_SECONDS = 15 * 60


def create_app(
    db_path: str | None = None,
    recent_limit: int = 30,
    writer=None,
    login_limit: int = LOGIN_ATTEMPT_LIMIT,
    login_window_seconds: int = LOGIN_WINDOW_SECONDS,
) -> Flask:
    app = Flask(__name__)
    memory = MemoryAgent(MemoryStore(db_path or str(_DEFAULT_DB), recent_limit=recent_limit))
    app.extensions["memory"] = memory
    app.extensions["writer"] = writer
    login_failures: dict[str, list[float]] = {}
    app.extensions["login_failures"] = login_failures

    def client_address() -> str:
        return request.remote_addr or "unknown"

    def login_blocked(address: str) -> bool:
        now = time.monotonic()
        recent = [stamp for stamp in login_failures.get(address, []) if now - stamp < login_window_seconds]
        login_failures[address] = recent
        return len(recent) >= login_limit

    def note_login_failure(address: str) -> None:
        login_failures.setdefault(address, []).append(time.monotonic())

    def current_user_id() -> int | None:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        return memory.user_id_for_token(header.removeprefix("Bearer ").strip())

    def require_user():
        user_id = current_user_id()
        if user_id is None:
            return None, (jsonify(error="Sign in is required."), 401)
        return user_id, None

    @app.get("/")
    def index():
        return send_from_directory(_STATIC, "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok", role="support", disclaimer=BOUNDARY)

    @app.get("/resources")
    def resources():
        country = normalize_country(request.args.get("country"))
        return jsonify(
            country=country,
            countries=country_choices(),
            summary=page_summary(country),
            crisis=[dict(item) for item in crisis_resources(country)],
            abuse=[dict(item) for item in ABUSE_RESOURCES] if country == "US" else [],
            medical=[dict(item) for item in MEDICAL_RESOURCES],
        )

    @app.post("/country")
    def choose_country():
        user_id, error = require_user()
        if error:
            return error
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Send a country."), 400
        code = memory.set_country(user_id, str(payload.get("country", "")))
        return jsonify(country=code, summary=page_summary(code))

    @app.post("/register")
    def register():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Send a username and password."), 400
        try:
            token = memory.register(payload.get("username", ""), payload.get("password", ""))
        except AuthError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(token=token), 201

    @app.post("/login")
    def login():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Send a username and password."), 400
        address = client_address()
        if login_blocked(address):
            return jsonify(error="Too many sign-in attempts. Wait and try again."), 429
        try:
            token = memory.login(payload.get("username", ""), payload.get("password", ""))
        except AuthError as exc:
            if "wrong" in str(exc):
                note_login_failure(address)
                return jsonify(error=str(exc)), 401
            return jsonify(error=str(exc)), 400
        login_failures.pop(address, None)
        return jsonify(token=token)

    @app.after_request
    def access_log(response):
        app.logger.info("%s %s %s", request.method, request.path, response.status_code)
        return response

    @app.get("/memory")
    def read_memory():
        user_id, error = require_user()
        if error:
            return error
        snapshot = memory.snapshot(user_id)
        snapshot["disclaimer"] = BOUNDARY
        return jsonify(snapshot)

    @app.post("/memory/delete")
    def delete_memory():
        user_id, error = require_user()
        if error:
            return error
        memory.clear(user_id)
        return jsonify(deleted=True)

    @app.post("/conversation")
    def conversation():
        user_id, error = require_user()
        if error:
            return error
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Send a JSON object with a message."), 400
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return jsonify(error="A message is required."), 400
        message = message.strip()
        if len(message) > MAX_MESSAGE_CHARS:
            return jsonify(error=f"Message is too long. The limit is {MAX_MESSAGE_CHARS} characters."), 400
        session = memory.load_session(user_id)
        chosen = payload.get("country")
        if isinstance(chosen, str) and chosen.strip():
            session.country = memory.set_country(user_id, chosen)
        result = handle_turn(session, message, writer)
        memory.save_exchange(user_id, session, message, result["response"], result["safety"])
        return jsonify(result)

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        return jsonify(error=exc.description), exc.code

    @app.errorhandler(Exception)
    def unexpected(_exc: Exception):
        return jsonify(error="Something went wrong. Please try again."), 500

    return app


def main() -> None:
    create_app(writer=writer_from_environment()).run(host=BIND_HOST, port=5050, debug=False)


if __name__ == "__main__":
    main()
