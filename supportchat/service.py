"""One turn of the support chat.

Order is fixed: safety, then an in-progress check-in, then a support reply.
A disorder label is never produced.
"""

from __future__ import annotations

import re

from supportchat.checkin import (
    INTRO,
    QUESTIONS,
    completion_message,
    format_question,
    interpret,
    is_cancel,
    parse_answer,
)
from supportchat.dialogue import REPLIES, compound_reply, detect_intent, matched_intents
from supportchat.safety import CRISIS_RESOURCES, SafetyResult, assess, normalize
from supportchat.session import MAX_USER_TURNS, Session

BOUNDARY = (
    "I'm a support tool, not a clinician. I can't diagnose, prescribe, or replace emergency care."
)

_DECLINED_CHECKIN = re.compile(r"\b(?:don't|do not|dont) (?:want|need)\b")
_FOLLOW_UP = re.compile(
    r"^(?:yes|yeah|yep|ok|okay|sure|it has|it's been|its been|for weeks|every night|"
    r"most days|i don't know|not really|a lot|all the time)\b"
)
_FEELINGS = {"sleep", "worry", "panic", "sadness", "lonely", "anger"}


def _checkin_state(session: Session, status: str, score: int | None = None, band: str | None = None) -> dict:
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


def _envelope(session: Session, body: str, safety: SafetyResult, checkin: dict) -> dict:
    return {
        "user_id": session.user_id,
        "response": body.rstrip() + "\n\n" + BOUNDARY,
        "disclaimer": BOUNDARY,
        "safety": safety.level,
        "urgent": safety.urgent,
        "crisis": safety.level == "self_harm",
        "resources": [dict(item) for item in safety.resources],
        "checkin": checkin,
    }


def _advance_checkin(session: Session, message: str, safety: SafetyResult) -> dict:
    if is_cancel(message):
        session.clear_checkin()
        return _envelope(
            session,
            "Okay, we'll leave the check-in. What's on your mind?",
            safety,
            _checkin_state(session, "inactive"),
        )

    score = parse_answer(message)
    if score is None:
        assert session.checkin_step is not None
        return _envelope(
            session,
            "I need a 0, 1, 2, or 3 so the check-in stays consistent.\n\n" + format_question(session.checkin_step),
            safety,
            _checkin_state(session, "in_progress"),
        )

    session.checkin_answers.append(score)
    assert session.checkin_step is not None
    session.checkin_step += 1
    if session.checkin_step < len(QUESTIONS):
        return _envelope(
            session,
            format_question(session.checkin_step),
            safety,
            _checkin_state(session, "in_progress"),
        )

    total = sum(session.checkin_answers)
    band, _detail = interpret(total)
    session.last_checkin = {"score": total, "band": band, "out_of": 12, "is_diagnosis": False}
    session.clear_checkin()

    resources = safety.resources
    if band == "high":
        names = {item["name"] for item in resources}
        resources = resources + tuple(item for item in CRISIS_RESOURCES if item["name"] not in names)
        safety = SafetyResult(level=safety.level, resources=resources)

    return _envelope(
        session,
        completion_message(total),
        safety,
        _checkin_state(session, "complete", score=total, band=band),
    )


def handle_turn(session: Session, message: str) -> dict:
    safety = assess(message)
    session.user_turns += 1
    inactive = _checkin_state(session, "inactive")

    if safety.urgent and safety.message:
        pause = ""
        if session.checkin_step is not None:
            pause = " We'll pause the check-in. Your safety comes first."
            session.clear_checkin()
        return _envelope(session, safety.message + pause, safety, inactive)

    if session.user_turns > MAX_USER_TURNS and session.checkin_step is None:
        return _envelope(
            session,
            "This session has gone on for a while. End it and start a new one so we keep only a small amount of state. "
            "If you might be in danger, use the crisis resources on this page.",
            safety,
            inactive,
        )

    if session.checkin_step is not None:
        return _advance_checkin(session, message, safety)

    intent = detect_intent(message)
    declined = bool(_DECLINED_CHECKIN.search(normalize(message)))
    if intent == "checkin" and not declined:
        session.checkin_step = 0
        session.checkin_answers = []
        session.last_topic = "checkin"
        session.topic_turns = 1
        return _envelope(
            session,
            INTRO + "\n\n" + format_question(0),
            safety,
            _checkin_state(session, "in_progress"),
        )
    if intent == "checkin":
        intent = "default"

    matched = matched_intents(message)
    combined = compound_reply(matched)
    if combined and intent in _FEELINGS | {"default"}:
        session.last_topic = "sleep" if "sleep" in matched else intent
        session.topic_turns = 1
        return _envelope(session, combined, safety, inactive)

    if (
        intent == "default"
        and session.last_topic in _FEELINGS
        and _FOLLOW_UP.search(normalize(message).strip())
    ):
        intent = session.last_topic

    if intent in _FEELINGS:
        if session.last_topic == intent:
            session.topic_turns += 1
        else:
            session.last_topic = intent
            session.topic_turns = 1
        replies = REPLIES[intent]
        body = replies[(session.topic_turns - 1) % len(replies)]
        return _envelope(session, body, safety, inactive)

    replies = REPLIES[intent]
    body = replies[(session.user_turns - 1) % len(replies)]
    return _envelope(session, body, safety, inactive)
