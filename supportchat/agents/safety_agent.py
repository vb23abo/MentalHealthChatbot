"""Decides whether this message needs a crisis or emergency reply.

The phrase list runs first, on the raw message. A second local check may add
the crisis line. It cannot remove a match the phrase list already made.
It does not call the support model.
"""

from __future__ import annotations

from supportchat.safety import SafetyResult, assess, escalate, second_look


class SafetyAgent:
    def __init__(self, second=None) -> None:
        self.second = second or second_look

    def run(self, message: str, country: str) -> SafetyResult:
        listed = assess(message, country)
        if listed.urgent:
            return listed
        verdict = self.second(message)
        if verdict in {"raise", "unsure"}:
            return escalate(country)
        return listed
