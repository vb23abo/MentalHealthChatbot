"""Shared shape of one chat turn."""

from __future__ import annotations

from supportchat.checkin import QUESTIONS
from supportchat.safety import SafetyResult
from supportchat.session import Session

BOUNDARY = (
    "I'm a support tool, not a clinician. I can't diagnose, prescribe, or replace emergency care."
)


def checkin_state(session: Session, status: str, score: int | None = None, band: str | None = None) -> dict:
    question = None
    if status == "in_progress" and session.checkin_step is not None:
        question = session.checkin_step + 1
    return {
        "status": status,
        "question": question,
        "total": len(QUESTIONS),
        "score": score,
        "band": band,
    }


def envelope(session: Session, body: str, safety: SafetyResult, checkin: dict) -> dict:
    return {
        "user_id": session.user_id,
        "response": body.rstrip() + "\n\n" + BOUNDARY,
        "disclaimer": BOUNDARY,
        "safety": safety.level,
        "urgent": safety.urgent,
        "crisis": safety.level == "self_harm",
        "resources": [dict(item) for item in safety.resources],
        "checkin": checkin,
        "visit_note": session.visit_note,
    }
