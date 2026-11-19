"""SQLite memory for returning users.

Stores an account, a short profile, and recent messages. Older messages
expire. The profile has no disorder label.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from supportchat.session import Session

RECENT_LIMIT = 30
RETENTION_DAYS = 30

TOPIC_PHRASES = {
    "sleep": "sleep",
    "worry": "worry",
    "panic": "panic",
    "sadness": "low mood",
    "lonely": "feeling alone",
    "anger": "anger",
    "checkin": "a check-in",
}

_USERNAME = re.compile(r"^[A-Za-z0-9_]{3,32}$")


class AuthError(ValueError):
    """The username or password cannot be accepted."""


def resume_line(topic: str | None, safety: str) -> str | None:
    if safety == "self_harm":
        return (
            "You're back. If you might hurt yourself, call or text 988 in the US, "
            "or use your local emergency number. If you want to talk, I'm here."
        )
    phrase = TOPIC_PHRASES.get(topic or "")
    if not phrase:
        return None
    return f"Last time you were talking about {phrase}. Want to pick that up?"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _clean_username(username: str) -> str:
    if not isinstance(username, str) or not _USERNAME.match(username):
        raise AuthError("Username must be 3–32 characters: letters, numbers, or _.")
    return username


def _check_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")


class MemoryStore:
    def __init__(self, path: str, recent_limit: int = RECENT_LIMIT, retention_days: int = RETENTION_DAYS) -> None:
        self.recent_limit = recent_limit
        self.retention_days = retention_days
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                last_topic TEXT,
                topic_turns INTEGER NOT NULL DEFAULT 0,
                user_turns INTEGER NOT NULL DEFAULT 0,
                checkin_step INTEGER,
                checkin_answers TEXT NOT NULL DEFAULT '[]',
                last_checkin TEXT,
                last_safety TEXT NOT NULL DEFAULT 'none',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                safety TEXT NOT NULL DEFAULT 'none',
                created_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def register(self, username: str, password: str) -> str:
        username = _clean_username(username)
        _check_password(password)
        now = _now()
        with self._lock:
            try:
                cursor = self._conn.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), now),
                )
            except sqlite3.IntegrityError as exc:
                raise AuthError("That username is already taken.") from exc
            user_id = int(cursor.lastrowid)
            self._conn.execute(
                "INSERT INTO profiles (user_id, updated_at) VALUES (?, ?)",
                (user_id, now),
            )
            token = self._issue_token(user_id, now)
            self._conn.commit()
            return token

    def login(self, username: str, password: str) -> str:
        username = _clean_username(username)
        _check_password(password)
        with self._lock:
            row = self._conn.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None or not check_password_hash(row["password_hash"], password):
                raise AuthError("Username or password is wrong.")
            token = self._issue_token(int(row["id"]), _now())
            self._conn.commit()
            return token

    def user_id_for_token(self, token: str) -> int | None:
        if not token:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT user_id FROM tokens WHERE token_hash = ?",
                (_hash_token(token),),
            ).fetchone()
        return None if row is None else int(row["user_id"])

    def load_session(self, user_id: int) -> Session:
        with self._lock:
            self._purge_old(user_id)
            profile = self._profile(user_id)
            self._conn.commit()
        answers = json.loads(profile["checkin_answers"] or "[]")
        last_checkin = json.loads(profile["last_checkin"]) if profile["last_checkin"] else None
        return Session(
            user_id=str(user_id),
            user_turns=profile["user_turns"],
            checkin_step=profile["checkin_step"],
            checkin_answers=answers,
            last_checkin=last_checkin,
            last_topic=profile["last_topic"],
            topic_turns=profile["topic_turns"],
        )

    def save_exchange(self, user_id: int, session: Session, user_text: str, assistant_text: str, safety: str) -> None:
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO turns (user_id, role, text, safety, created_at) VALUES (?, 'user', ?, 'none', ?)",
                (user_id, user_text, now),
            )
            self._conn.execute(
                "INSERT INTO turns (user_id, role, text, safety, created_at) VALUES (?, 'assistant', ?, ?, ?)",
                (user_id, assistant_text, safety, now),
            )
            self._conn.execute(
                """
                UPDATE profiles SET
                    last_topic = ?, topic_turns = ?, user_turns = ?,
                    checkin_step = ?, checkin_answers = ?, last_checkin = ?,
                    last_safety = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (
                    session.last_topic,
                    session.topic_turns,
                    session.user_turns,
                    session.checkin_step,
                    json.dumps(session.checkin_answers),
                    json.dumps(session.last_checkin) if session.last_checkin else None,
                    safety,
                    now,
                    user_id,
                ),
            )
            self._trim(user_id)
            self._conn.commit()

    def snapshot(self, user_id: int) -> dict:
        with self._lock:
            self._purge_old(user_id)
            profile = self._profile(user_id)
            user = self._conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
            turns = self._conn.execute(
                "SELECT role, text, safety FROM turns WHERE user_id = ? ORDER BY id ASC",
                (user_id,),
            ).fetchall()
            self._conn.commit()
        return {
            "username": user["username"],
            "resume": resume_line(profile["last_topic"], profile["last_safety"]),
            "last_topic": profile["last_topic"],
            "last_safety": profile["last_safety"],
            "turns": [
                {"role": row["role"], "text": row["text"], "safety": row["safety"]}
                for row in turns
            ],
        }

    def clear(self, user_id: int) -> None:
        now = _now()
        with self._lock:
            self._conn.execute("DELETE FROM turns WHERE user_id = ?", (user_id,))
            self._conn.execute(
                """
                UPDATE profiles SET
                    last_topic = NULL, topic_turns = 0, user_turns = 0,
                    checkin_step = NULL, checkin_answers = '[]', last_checkin = NULL,
                    last_safety = 'none', updated_at = ?
                WHERE user_id = ?
                """,
                (now, user_id),
            )
            self._conn.commit()

    def _issue_token(self, user_id: int, now: str) -> str:
        token = secrets.token_urlsafe(32)
        self._conn.execute(
            "INSERT INTO tokens (token_hash, user_id, created_at) VALUES (?, ?, ?)",
            (_hash_token(token), user_id, now),
        )
        return token

    def _profile(self, user_id: int) -> sqlite3.Row:
        row = self._conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            raise AuthError("Account not found.")
        return row

    def _purge_old(self, user_id: int) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        self._conn.execute(
            "DELETE FROM turns WHERE user_id = ? AND created_at < ?",
            (user_id, cutoff),
        )

    def _trim(self, user_id: int) -> None:
        self._purge_old(user_id)
        extra = self._conn.execute(
            """
            SELECT id FROM turns WHERE user_id = ?
            ORDER BY id DESC LIMIT -1 OFFSET ?
            """,
            (user_id, self.recent_limit),
        ).fetchall()
        if not extra:
            return
        ids = [row["id"] for row in extra]
        placeholders = ",".join("?" for _ in ids)
        self._conn.execute(f"DELETE FROM turns WHERE id IN ({placeholders})", ids)

    def close(self) -> None:
        with self._lock:
            self._conn.close()
