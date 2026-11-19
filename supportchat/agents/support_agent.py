"""Writes the listening reply for one concern.

A local model may write the practical sentence. Diagnosis, medication, and
a named disorder are rejected and the template is used instead.
"""

from __future__ import annotations

from supportchat.agents.turn import checkin_state, envelope
from supportchat.dialogue import REPLIES, compound_reply, detect_intent, matched_intents, reflect
from supportchat.helplines import crisis_sentence
from supportchat.library import card_for, grounded, present
from supportchat.model import usable_support_text
from supportchat.safety import SafetyResult
from supportchat.session import Session

_FEELINGS = {"sleep", "worry", "panic", "sadness", "lonely", "anger"}


class SupportAgent:
    def reply(self, session: Session, message: str, safety: SafetyResult, writer=None) -> dict:
        inactive = checkin_state(session, "inactive")
        intent = detect_intent(message)
        if intent == "checkin":
            intent = "default"

        matched = matched_intents(message)
        combined = compound_reply(matched)
        if combined and intent in _FEELINGS | {"default"}:
            session.last_topic = "sleep" if "sleep" in matched else intent
            session.topic_turns = 1
            return self._from_card(session, message, safety, inactive, session.last_topic, combined, writer)

        if intent == "default" and session.last_topic in _FEELINGS:
            intent = session.last_topic

        if intent in _FEELINGS:
            if session.last_topic == intent:
                session.topic_turns += 1
            else:
                session.last_topic = intent
                session.topic_turns = 1
            replies = REPLIES[intent]
            template = replies[(session.topic_turns - 1) % len(replies)]
            return self._from_card(session, message, safety, inactive, intent, template, writer)

        replies = REPLIES[intent]
        template = replies[(session.user_turns - 1) % len(replies)]
        if intent == "goodbye" and session.country != "US":
            template = (
                "Take care. If things get worse, or if you might hurt yourself, contact local emergency services. "
                + crisis_sentence(session.country)
            )
        if intent == "next_step":
            template = present(card_for("clinician"), template)
            return envelope(session, template, safety, inactive)
        if intent == "default":
            template = reflect(message, template)
        return envelope(session, template, safety, inactive)

    def _from_card(
        self,
        session: Session,
        message: str,
        safety: SafetyResult,
        inactive: dict,
        topic: str,
        body: str,
        writer,
    ) -> dict:
        card = card_for(topic)
        template = present(card, body) if card is not None else body
        drafted = self._practical(message, topic, template, writer, None if card is None else card.practical)
        if card is not None:
            drafted = grounded(card, drafted, template)
        return envelope(session, reflect(message, drafted), safety, inactive)

    def _practical(self, message: str, topic: str, template: str, writer, practical: str | None) -> str:
        if writer is None:
            return template
        try:
            drafted = writer.write(message=message, topic=topic, template=template)
        except Exception:
            return template
        if not isinstance(drafted, str) or not usable_support_text(drafted):
            return template
        cleaned = drafted.strip()
        if practical is not None and practical.lower() not in cleaned.lower():
            return template
        return cleaned
