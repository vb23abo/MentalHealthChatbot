"""In-memory sessions.

Stores check-in progress and a turn count. Message text is not kept.
There are no accounts. State disappears when the process stops.
"""

from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator
from uuid import uuid4


MAX_SESSIONS = 500
MAX_MESSAGE_CHARS = 2000
_USER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class InvalidUserId(ValueError):
    """The client sent a user id this demo cannot store."""


@dataclass
class Session:
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_turns: int = 0
    checkin_step: int | None = None
    checkin_answers: list[int] = field(default_factory=list)
    last_checkin: dict | None = None
    last_topic: str | None = None
    concerns: list = field(default_factory=list)
    pending: str = ""
    user_lines: list[str] = field(default_factory=list)
    visit_note: str | None = None
    country: str = "US"

    def clear_checkin(self) -> None:
        self.checkin_step = None
        self.checkin_answers = []


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def _validate(self, user_id: str | None) -> str:
        if user_id is None or user_id == "":
            return str(uuid4())
        if not isinstance(user_id, str) or not _USER_ID.match(user_id):
            raise InvalidUserId("user_id must be 1–64 characters: letters, numbers, _ or -.")
        return user_id

    def _evict_if_needed(self) -> None:
        if len(self._sessions) < MAX_SESSIONS:
            return
        oldest = min(self._sessions.values(), key=lambda session: session.created_at)
        self._sessions.pop(oldest.user_id, None)

    @contextmanager
    def acquire(self, user_id: str | None) -> Iterator[Session]:
        with self._lock:
            resolved = self._validate(user_id)
            session = self._sessions.get(resolved)
            if session is None:
                self._evict_if_needed()
                session = Session(user_id=resolved)
                self._sessions[resolved] = session
            yield session

    def end(self, user_id: str) -> dict | None:
        with self._lock:
            resolved = self._validate(user_id)
            session = self._sessions.pop(resolved, None)
            if session is None:
                return None
            return {
                "user_id": session.user_id,
                "user_messages": session.user_turns,
                "checkin": session.last_checkin,
                "deleted": True,
                "note": "Session state was removed from server memory. Message text was never stored.",
            }
