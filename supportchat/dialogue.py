"""Short replies for the fixed exits.

A concern is handled elsewhere. These patterns only catch a check-in request,
a goodbye, thanks, a wish to stop, and a request for a diagnosis or a treatment.
"""

from __future__ import annotations

import re

from supportchat.safety import normalize

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("goodbye", re.compile(r"\b(?:goodbye|bye|good night)\b")),
    ("thanks", re.compile(r"\b(?:thank you|thanks)\b")),
    ("checkin", re.compile(r"\b(?:check[- ]?in|screen me|screening|questionnaire)\b")),
    (
        "diagnosis",
        re.compile(
            r"\b(?:do i have|diagnos(?:e|is|ing)|what's wrong with me|whats wrong with me|"
            r"am i (?:depressed|bipolar|anxious)|"
            r"bipolar|ptsd|ocd|adhd)\b"
        ),
    ),
    (
        "treatment",
        re.compile(
            r"\b(?:treatment plan|medicat(?:e|ion|ions)|prescribe|antidepressant|"
            r"what treatment|\bcbt\b|\bemdr\b|\berp\b)\b"
        ),
    ),
    ("leave", re.compile(r"\bleave me alone\b")),
    ("greeting", re.compile(r"^(?:hi|hello|hey|good morning|good evening|good afternoon)\b")),
]

_PRIORITY = (
    "diagnosis",
    "treatment",
    "checkin",
    "leave",
    "goodbye",
    "thanks",
    "greeting",
)

REPLIES: dict[str, tuple[str, ...]] = {
    "leave": (
        "I'll keep this short. I'm here if you want to talk later. If you're in danger, use the crisis resources on this page.",
    ),
    "diagnosis": (
        "I can't diagnose anxiety, depression, bipolar disorder, PTSD, OCD, ADHD, or anything else. "
        "Only a licensed clinician can do that, and not from a chat like this. "
        "I can stay with what you're feeling, or we can do the four-question check-in about the last two weeks. Say check-in if you want that.",
    ),
    "treatment": (
        "I can't assign a therapy, a medication, or a treatment plan. A licensed clinician can discuss options with you after they meet you. "
        "What I can do is help you list what you want to bring to that visit: sleep, mood, and what has been hardest.",
    ),
    "thanks": ("You're welcome. I'm here if you want to keep going.",),
    "goodbye": (
        "Take care. If things get worse, or if you might hurt yourself, contact local emergency services or call or text 988 in the US.",
    ),
}


def detect_intent(message: str) -> str:
    text = normalize(message).strip()
    matched = [name for name, pattern in _PATTERNS if pattern.search(text)]
    if len(matched) > 1 and "greeting" in matched:
        matched.remove("greeting")
    for name in _PRIORITY:
        if name in matched:
            return name
    return "default"
