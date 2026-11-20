"""Calls the task agents in a fixed order for one message."""

from __future__ import annotations

from supportchat.agents.checkin_agent import CheckInAgent
from supportchat.agents.guidance_agent import GuidanceAgent
from supportchat.agents.safety_agent import SafetyAgent
from supportchat.agents.support_agent import SupportAgent
from supportchat.agents.turn import checkin_state, envelope
from supportchat.agents.understanding_agent import UnderstandingAgent
from supportchat.dialogue import detect_intent
from supportchat.session import Session


class Orchestrator:
    def __init__(
        self,
        safety: SafetyAgent | None = None,
        checkin: CheckInAgent | None = None,
        understanding: UnderstandingAgent | None = None,
        guidance: GuidanceAgent | None = None,
        support: SupportAgent | None = None,
    ) -> None:
        self.safety = safety or SafetyAgent()
        self.checkin = checkin or CheckInAgent()
        self.understanding = understanding or UnderstandingAgent()
        self.guidance = guidance or GuidanceAgent()
        self.support = support or SupportAgent()

    def handle(self, session: Session, message: str, writer=None) -> dict:
        session.user_lines.append(message.strip())
        safety = self.safety.run(message, session.country)
        session.user_turns += 1

        if safety.urgent and safety.message:
            pause = self.checkin.pause(session)
            return envelope(session, safety.message + pause, safety, checkin_state(session, "inactive"))

        if self.checkin.in_progress(session):
            return self.checkin.advance(session, message, safety)

        started = self.checkin.maybe_start(session, message, safety, detect_intent(message))
        if started is not None:
            return started

        held = self.support.boundary(session, message, safety)
        if held is not None:
            return held

        understood = self.understanding.read(session, message)
        card = self.guidance.choose(understood)
        return self.support.write(session, message, safety, understood, card, writer)
