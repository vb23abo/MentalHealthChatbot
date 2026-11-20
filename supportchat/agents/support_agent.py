"""Writes the listening reply from Understanding and, when needed, a card.

A local model may rephrase the card. Diagnosis, medication, and a named
disorder are rejected and the card is sent.
"""

from __future__ import annotations

from supportchat.agents.turn import checkin_state, envelope
from supportchat.concerns import Plan, Understanding, accept_draft, support_text
from supportchat.dialogue import REPLIES, detect_intent
from supportchat.helplines import crisis_sentence
from supportchat.library import Card, present
from supportchat.model import usable_support_text
from supportchat.safety import SafetyResult
from supportchat.session import Session

_ELSE = "Is there something else as well?"


class SupportAgent:
    def boundary(self, session: Session, message: str, safety: SafetyResult) -> dict | None:
        intent = detect_intent(message)
        if intent not in {"diagnosis", "treatment", "thanks", "goodbye", "leave"}:
            return None
        template = REPLIES[intent][(session.user_turns - 1) % len(REPLIES[intent])]
        if intent == "goodbye" and session.country != "US":
            template = (
                "Take care. If things get worse, or if you might hurt yourself, contact local emergency services. "
                + crisis_sentence(session.country)
            )
        return envelope(session, template, safety, checkin_state(session, "inactive"))

    def write(
        self,
        session: Session,
        message: str,
        safety: SafetyResult,
        understood: Understanding,
        card: Card | None,
        writer=None,
    ) -> dict:
        text, plan = self._compose(understood, card)
        if plan is not None and plan.use_writer and writer is not None:
            text = accept_draft(plan, self._draft(message, plan.text, writer))
        return envelope(session, text, safety, checkin_state(session, "inactive"))

    def _compose(self, understood: Understanding, card: Card | None) -> tuple[str, Plan | None]:
        kind = understood.kind
        label = understood.label or "this"
        if kind == "today":
            return "How are you today?", None
        if kind == "resume":
            return (
                f'Last time you were talking about "{label}". '
                "Do you want to stay with that, or is something else on your mind?"
            ), None
        if kind == "open_ask":
            return "What's been going on?", None
        if kind == "else_ask":
            return "What else is going on?", None
        if kind == "stay":
            return "Okay. We can stay with this.", None
        if kind == "eased":
            return (
                f'You said "{understood.quote}". I\'ll leave "{label}" here until you bring it up.'
            ), None
        if kind == "closed":
            return (
                f'You said "{understood.quote}". I won\'t bring up "{label}" unless you do.'
            ), None
        if kind == "clarify":
            return (
                f'Is this still about "{label}", or is something else on your mind?'
            ), None
        if kind == "signpost" and card is not None:
            return present(card, "I can't decide that for you."), None
        if kind == "concern" and card is not None and understood.current:
            text = support_text(understood.current, understood.prior, understood.linked)
            must = [card.practical]
            if understood.prior and understood.prior != understood.current:
                must.append(understood.prior)
            if understood.linked:
                must.append(understood.linked)
            if understood.ask_else:
                text = f"{text}\n\n{_ELSE}"
                must.append(_ELSE)
            plan = Plan(
                text,
                use_writer=True,
                practical=card.practical,
                must_keep=tuple(must),
                pending=understood.pending,
            )
            return text, plan
        return "I'm here to listen.", None

    def _draft(self, message: str, template: str, writer) -> str:
        try:
            drafted = writer.write(message=message, topic="support", template=template)
        except Exception:
            return template
        if not isinstance(drafted, str) or not usable_support_text(drafted):
            return template
        return drafted
