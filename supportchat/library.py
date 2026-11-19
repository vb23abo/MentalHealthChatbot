"""Local support cards.

Each card is one concern, one practical step, and a public source.
There is no card for a disorder, a medication, or a treatment plan.
"""

from __future__ import annotations

from dataclasses import dataclass

_SUPPORT_LINE = "This is support, not a diagnosis."


@dataclass(frozen=True)
class Card:
    topic: str
    practical: str
    source: str
    support_line: str = _SUPPORT_LINE


CARDS: dict[str, Card] = {
    "sleep": Card(
        "sleep",
        "fixed wake-up time",
        "NHS Every Mind Matters, sleep",
    ),
    "worry": Card(
        "worry",
        "breathe out for six",
        "NHS Every Mind Matters, worry",
    ),
    "panic": Card(
        "panic",
        "both feet on the floor",
        "NHS, panic attacks",
    ),
    "sadness": Card(
        "sadness",
        "one thing that would make the next hour a little easier",
        "NHS Every Mind Matters, low mood",
    ),
    "lonely": Card(
        "lonely",
        "short message",
        "NHS, loneliness",
    ),
    "anger": Card(
        "anger",
        "pause before you send",
        "NHS, anger",
    ),
    "clinician": Card(
        "clinician",
        "one small thing in the next hour",
        "NHS, talking to a GP",
    ),
}


def card_for(topic: str) -> Card | None:
    return CARDS.get(topic)


def present(card: Card, body: str) -> str:
    """The reply the person sees when the model is off, or when a draft is dropped."""
    text = body.strip()
    if card.practical.lower() not in text.lower():
        text = f"{text} {card.practical}."
    return _with_source(card, text)


def grounded(card: Card, drafted: str, fallback: str) -> str:
    """Keep a draft only when it still contains the card's practical step."""
    cleaned = drafted.strip()
    if card.practical.lower() not in cleaned.lower():
        return fallback
    return _with_source(card, cleaned)


def _with_source(card: Card, text: str) -> str:
    lower = text.lower()
    extra: list[str] = []
    source_line = f"Source: {card.source}."
    if source_line.lower() not in lower:
        extra.append(source_line)
    if card.support_line.lower() not in lower:
        extra.append(card.support_line)
    if not extra:
        return text
    return text.rstrip() + "\n\n" + " ".join(extra)
