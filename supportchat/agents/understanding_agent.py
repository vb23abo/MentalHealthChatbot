"""Decides what the new message is about.

Compares it with each stored phrase and that concern's three snippets.
It does not read the transcript, and it does not write the reply.
"""

from __future__ import annotations

from supportchat.concerns import Understanding, understand
from supportchat.session import Session


class UnderstandingAgent:
    def read(self, session: Session, message: str) -> Understanding:
        result = understand(message, session.concerns, session.pending)
        session.pending = result.pending
        self._sync_topic(session)
        return result

    def _sync_topic(self, session: Session) -> None:
        for concern in reversed(session.concerns):
            if concern.status == "open":
                session.last_topic = concern.label
                return
        session.last_topic = None
