"""Four-question distress check-in.

The wording is original. This is a conversation aid, not a clinical scale
and not a diagnosis.
"""

from __future__ import annotations

import re

from supportchat.safety import normalize

QUESTIONS = (
    "Over the past two weeks, how often have you felt down, hopeless, or close to tears?",
    "Over the past two weeks, how often have you had little interest in things you usually care about?",
    "Over the past two weeks, how often has worry been hard to stop or control?",
    "Over the past two weeks, how often have these feelings made work, school, or relationships harder?",
)

SCALE = "0 = not at all, 1 = several days, 2 = more than half the days, 3 = nearly every day."

INTRO = (
    "We can do a four-question check-in about the last two weeks. "
    "It is not a diagnosis and it is not a medical assessment. "
    "Answer each one with 0, 1, 2, or 3. Type stop if you want to leave it."
)

_ANSWERS = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "not at all": 0,
    "several days": 1,
    "more than half the days": 2,
    "more than half": 2,
    "nearly every day": 3,
    "nearly every": 3,
}

_LEADING_SCORE = re.compile(r"^([0-3])\b")
_CANCEL = re.compile(r"^(?:stop|cancel|quit|never mind|nevermind|exit)[.!]?$")


def is_cancel(text: str) -> bool:
    return bool(_CANCEL.match(normalize(text).strip()))


def parse_answer(text: str) -> int | None:
    cleaned = normalize(text).strip(" \t\n.!?")
    if cleaned in _ANSWERS:
        return _ANSWERS[cleaned]
    match = _LEADING_SCORE.match(cleaned)
    if match:
        return int(match.group(1))
    return None


def format_question(step: int) -> str:
    return f"Question {step + 1} of {len(QUESTIONS)}: {QUESTIONS[step]}\n{SCALE}"


def interpret(score: int) -> tuple[str, str]:
    """Map a 0–12 total to a band and a non-diagnostic explanation."""
    if score <= 3:
        return (
            "low",
            "These answers suggest the feelings have been less frequent lately. "
            "That can still be worth mentioning to a doctor or counselor if you are worried.",
        )
    if score <= 7:
        return (
            "moderate",
            "These answers suggest distress has been getting in the way on a lot of days. "
            "A doctor, counselor, or campus or workplace health service can help you decide on next steps.",
        )
    return (
        "high",
        "These answers suggest distress has been frequent and disruptive. "
        "Please consider contacting a doctor or counselor soon. "
        "If you might hurt yourself, call or text 988 in the US, or use your local emergency number.",
    )


def completion_message(score: int) -> str:
    band, detail = interpret(score)
    return (
        f"Check-in total: {score} out of 12. Band: {band}. {detail} "
        "This check-in is not a diagnosis. "
        "A clinician is the person who can put this in context with the rest of your life."
    )
