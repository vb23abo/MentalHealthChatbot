"""Hands out the one card for this turn.

It does not invent a step, and it does not keep a card per life domain.
"""

from __future__ import annotations

from supportchat.concerns import Understanding
from supportchat.library import SIGNPOST, SUPPORT, Card


class GuidanceAgent:
    def choose(self, understood: Understanding) -> Card | None:
        if understood.kind == "concern":
            return SUPPORT
        if understood.kind == "signpost":
            return SIGNPOST
        return None
