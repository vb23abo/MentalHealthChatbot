"""Runs the four-question check-in when the person asks for it.

The result is a band and, when the band is high, a note for a clinician.
It is not a diagnosis.
"""

from __future__ import annotations

import re

from supportchat.agents.turn import checkin_state, envelope
from supportchat.checkin import (
    INTRO,
    QUESTIONS,
    completion_message,
    format_question,
    interpret,
    is_cancel,
    parse_answer,
)
from supportchat.helplines import crisis_resources
from supportchat.safety import SafetyResult, normalize
from supportchat.session import Session

_DECLINED = re.compile(r"\b(?:don't|do not|dont) (?:want|need)\b")


class CheckInAgent:
    def in_progress(self, session: Session) -> bool:
        return session.checkin_step is not None

    def pause(self, session: Session) -> str:
        if session.checkin_step is None:
            return ""
        session.clear_checkin()
        return " We'll pause the check-in. Your safety comes first."

    def advance(self, session: Session, message: str, safety: SafetyResult) -> dict:
        if is_cancel(message):
            session.clear_checkin()
            return envelope(
                session,
                "Okay, we'll leave the check-in. What's on your mind?",
                safety,
                checkin_state(session, "inactive"),
            )

        score = parse_answer(message)
        if score is None:
            assert session.checkin_step is not None
            return envelope(
                session,
                "I need a 0, 1, 2, or 3 so the check-in stays consistent.\n\n" + format_question(session.checkin_step),
                safety,
                checkin_state(session, "in_progress"),
            )

        session.checkin_answers.append(score)
        assert session.checkin_step is not None
        session.checkin_step += 1
        if session.checkin_step < len(QUESTIONS):
            return envelope(
                session,
                format_question(session.checkin_step),
                safety,
                checkin_state(session, "in_progress"),
            )

        total = sum(session.checkin_answers)
        band, _detail = interpret(total)
        answers = list(session.checkin_answers)
        session.last_checkin = {"score": total, "band": band, "out_of": 12, "is_diagnosis": False}
        session.clear_checkin()

        resources = safety.resources
        body, note = completion_message(total, answers, session.user_lines, session.country)
        if band == "high":
            names = {item["name"] for item in resources}
            resources = resources + tuple(
                item for item in crisis_resources(session.country) if item["name"] not in names
            )
            safety = SafetyResult(level=safety.level, resources=resources)
            session.visit_note = note
        else:
            session.visit_note = None

        return envelope(
            session,
            body,
            safety,
            checkin_state(session, "complete", score=total, band=band),
        )

    def maybe_start(self, session: Session, message: str, safety: SafetyResult, intent: str) -> dict | None:
        if intent != "checkin":
            return None
        if _DECLINED.search(normalize(message)):
            return None
        session.checkin_step = 0
        session.checkin_answers = []
        session.last_topic = "checkin"
        session.topic_turns = 1
        return envelope(
            session,
            INTRO + "\n\n" + format_question(0),
            safety,
            checkin_state(session, "in_progress"),
        )

