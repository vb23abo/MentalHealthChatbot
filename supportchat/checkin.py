"""Four-question distress check-in.

The wording is original. This is a conversation aid, not a clinical scale
and not a diagnosis.
"""

from __future__ import annotations

import re

from supportchat.helplines import crisis_sentence
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
        "If you might hurt yourself, contact the crisis line for your country or local emergency services.",
    )


_MOOD = (
    "Not at all down, hopeless, or close to tears over the past two weeks.",
    "Down, hopeless, or close to tears on several days.",
    "Down, hopeless, or close to tears on more than half the days.",
    "Down, hopeless, or close to tears nearly every day.",
)

_FUNCTION = (
    "On the check-in, these feelings did not make work, school, or relationships harder.",
    "On the check-in, these feelings made work, school, or relationships harder on several days.",
    "On the check-in, these feelings made work, school, or relationships harder on more than half the days.",
    "On the check-in, these feelings made work, school, or relationships harder nearly every day.",
)

_SLEEP = re.compile(r"\b(?:sleep|asleep|awake|insomnia)\b")
_DURATION = re.compile(r"\b(?:days|weeks|months|nights|years)\b")
_HARDEST = re.compile(r"\b(?:hardest|worst|toughest)\b")
_SKIP_LINE = re.compile(r"^(?:check-?in|[0-3]|zero|one|two|three|not at all|several days|nearly every day)[.!]?$")


def _chat_lines(lines: list[str]) -> list[str]:
    kept: list[str] = []
    for line in lines:
        cleaned = normalize(line).strip(" \t\n.!?")
        if not cleaned or _SKIP_LINE.match(cleaned):
            continue
        kept.append(" ".join(line.split()))
    return kept


def _first_match(lines: list[str], pattern: re.Pattern[str]) -> str | None:
    for line in lines:
        if pattern.search(normalize(line)):
            if len(line) > 90:
                return line[:87].rstrip() + "..."
            return line
    return None


def clinician_note(score: int, band: str, answers: list[int], lines: list[str]) -> str:
    """A copyable summary of this chat. It is not a diagnosis."""
    chat = _chat_lines(lines)
    mood = _MOOD[answers[0]] if answers else "Not recorded."
    sleep = _first_match(chat, _SLEEP)
    duration = _first_match(chat, _DURATION)
    hardest = _first_match(chat, _HARDEST)
    sleep_line = f'They said "{sleep}".' if sleep else "Not mentioned in this chat."
    duration_line = (
        f'They said "{duration}".'
        if duration
        else "The check-in covers the past two weeks. They did not add another duration."
    )
    if hardest:
        hard_line = f'They said "{hardest}".'
    elif len(answers) > 3:
        hard_line = _FUNCTION[answers[3]]
    else:
        hard_line = "Not mentioned in this chat."
    return (
        "Notes for a clinician\n"
        f"Check-in: {score} out of 12. Band: {band}.\n"
        f"Mood: {mood}\n"
        f"Sleep: {sleep_line}\n"
        f"How long: {duration_line}\n"
        f"What was hardest: {hard_line}\n"
        "This note is not a diagnosis."
    )


def completion_message(
    score: int,
    answers: list[int] | None = None,
    lines: list[str] | None = None,
    country: str = "US",
) -> tuple[str, str | None]:
    band, detail = interpret(score)
    if band == "high":
        detail = detail + " " + crisis_sentence(country)
    body = (
        f"Check-in total: {score} out of 12. Band: {band}. {detail} "
        "This check-in is not a diagnosis. "
        "A clinician is the person who can put this in context with the rest of your life."
    )
    note = None
    if band == "high" and answers is not None:
        note = clinician_note(score, band, answers, lines or [])
        body = body + "\n\n" + note
    return body, note
