"""The two support cards.

Every described concern uses the support card. Asking how to talk with
someone uses the signpost card. There is no card per life domain, and no
card for a disorder, a medication, or a treatment plan.
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


SUPPORT = Card(
    "support",
    "one small thing that would make the next hour a little easier",
    "NHS Every Mind Matters",
)

SIGNPOST = Card(
    "signpost",
    "one small thing that would make the next hour a little easier, and talk to a person",
    "NHS, talking to someone",
)

CARDS = {"support": SUPPORT, "signpost": SIGNPOST}


def card_for(topic: str) -> Card | None:
    return CARDS.get(topic)


def present(card: Card, body: str) -> str:
    """The reply the person sees when the model is off, or when a draft is dropped."""
    text = body.strip()
    if card.practical.lower() not in text.lower():
        text = f"{text} {card.practical[0].upper() + card.practical[1:]}."
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
