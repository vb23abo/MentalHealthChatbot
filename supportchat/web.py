"""Local HTTP API and chat page.

Run from the project root:

    python -m supportchat.web
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from supportchat.memory import AuthError, MemoryStore
from supportchat.safety import PUBLIC_RESOURCES
from supportchat.service import BOUNDARY, handle_turn
from supportchat.session import MAX_MESSAGE_CHARS

_STATIC = Path(__file__).resolve().parent.parent / "static"
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "support.sqlite"


def create_app(db_path: str | None = None, recent_limit: int = 30) -> Flask:
    app = Flask(__name__)
    memory = MemoryStore(db_path or str(_DEFAULT_DB), recent_limit=recent_limit)
    app.extensions["memory"] = memory

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
        return jsonify(PUBLIC_RESOURCES)

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
        try:
            token = memory.login(payload.get("username", ""), payload.get("password", ""))
        except AuthError as exc:
            status = 401 if "wrong" in str(exc) else 400
            return jsonify(error=str(exc)), status
        return jsonify(token=token)

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
        result = handle_turn(session, message)
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
    create_app().run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
