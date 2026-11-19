"""One turn of the support chat.

The orchestrator calls safety, then check-in, then the support reply.
A disorder label is never produced.
"""

from __future__ import annotations

from supportchat.agents.orchestrator import Orchestrator
from supportchat.agents.turn import BOUNDARY
from supportchat.session import Session

_orchestrator = Orchestrator()


def handle_turn(session: Session, message: str, writer=None) -> dict:
    return _orchestrator.handle(session, message, writer)
