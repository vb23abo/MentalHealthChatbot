"""A concern is the person's own phrase.

There is no list of life domains. Every ordinary concern gets the same
practical step. A link, a pause, or a return is decided from their words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from supportchat.library import SUPPORT, grounded, present
from supportchat.safety import normalize

_STOP = {
    "about", "again", "also", "am", "and", "are", "because", "been", "being",
    "but", "feel", "feeling", "felt", "for", "from", "have", "into", "just",
    "like", "really", "still", "that", "the", "their", "them", "then", "they",
    "this", "those", "very", "was", "were", "what", "when", "with", "would",
    "you", "your",
}
_IMPROVE_WORDS = {
    "better", "easier", "gotten", "getting", "going", "improved", "improving",
    "results", "showing", "things", "well",
}

_GREETING_ONLY = re.compile(
    r"^(?:hi|hello|hey|good morning|good evening|good afternoon)[.!]?$",
    re.IGNORECASE,
)
_CONTINUE = re.compile(
    r"^(?:it(?:'s| is| has| was)?|still|again|worse|the same|same thing)\b",
    re.IGNORECASE,
)
_LINK = re.compile(r"\b(?:because|that'?s why|led to)\b", re.IGNORECASE)
_BUT = re.compile(r"\bbut\b", re.IGNORECASE)
_EASED = re.compile(
    r"\b(?:improved|improving|gotten better|getting better|going well|showing results|easier|better for now)\b"
    r"|\b(?:is|feels|feeling|been|getting|has been|it(?:'s| is)|this is|things are) better\b",
    re.IGNORECASE,
)
_FINE_ONLY = re.compile(
    r"^(?:i am |i'm |im )?(?:fine|ok|okay|good|alright|all right|not bad|pretty good|doing ok|doing okay)[.!]?$",
    re.IGNORECASE,
)
_YES_ONLY = re.compile(r"^(?:yes|yeah|yep)[.!]?$", re.IGNORECASE)
_NO_ONLY = re.compile(r"^(?:no|nope|that's all|thats all|nothing else)[.!]?$", re.IGNORECASE)
_ELSE = "Is there something else as well?"
_CLOSED = re.compile(
    r"\b(?:don'?t bring (?:this|that|it) up|do not bring (?:this|that|it) up|"
    r"i(?:'m| am) done talking about(?: this)?)\b",
    re.IGNORECASE,
)
_SIGNPOST = re.compile(
    r"^(?:what should i do|what do i do)\??$|\bhow (?:do i|can i|to) talk\b",
    re.IGNORECASE,
)

_LABEL_MAX = 60
_SNIPPET_MAX = 200


@dataclass
class Concern:
    label: str
    status: str = "open"
    snippets: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"label": self.label, "status": self.status, "snippets": list(self.snippets)}

    @staticmethod
    def from_json(data: dict) -> Concern:
        return Concern(
            str(data.get("label") or ""),
            str(data.get("status") or "open"),
            [str(item) for item in (data.get("snippets") or [])][-3:],
        )


@dataclass
class Plan:
    text: str
    use_writer: bool = False
    practical: str | None = None
    must_keep: tuple[str, ...] = ()
    pending: str = ""


@dataclass
class Understanding:
    """What this message is, before any reply is written."""

    kind: str
    label: str | None = None
    quote: str | None = None
    current: str | None = None
    prior: str | None = None
    linked: str | None = None
    ask_else: bool = False
    pending: str = ""


def greeting_only(message: str) -> bool:
    return _GREETING_ONLY.match(message.strip()) is not None


def content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", normalize(text))
    return {word for word in words if len(word) >= 4 and word not in _STOP}


def _snippet(message: str) -> str:
    text = " ".join(message.strip().split())
    if len(text) <= _SNIPPET_MAX:
        return text
    return text[: _SNIPPET_MAX - 3].rstrip() + "..."


def _label(message: str) -> str:
    text = " ".join(message.strip().split())
    sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    if len(sentence) <= _LABEL_MAX:
        return sentence
    return sentence[: _LABEL_MAX - 3].rstrip() + "..."


def _latest_open(concerns: list[Concern]) -> Concern | None:
    for concern in reversed(concerns):
        if concern.status == "open":
            return concern
    return None


def _concern_words(concern: Concern) -> set[str]:
    words = content_words(concern.label)
    for snippet in concern.snippets:
        words |= content_words(snippet)
    return words


def _overlap(message: str, concerns: list[Concern]) -> list[Concern]:
    words = content_words(message)
    if not words:
        return []
    found: list[Concern] = []
    for concern in concerns:
        if words & _concern_words(concern):
            found.append(concern)
    return found


def _remember(concern: Concern, message: str) -> None:
    snippet = _snippet(message)
    if concern.snippets and concern.snippets[-1] == snippet:
        return
    concern.snippets.append(snippet)
    del concern.snippets[:-3]


def _touch(concerns: list[Concern], concern: Concern) -> None:
    if concern in concerns:
        concerns.remove(concern)
    concerns.append(concern)


def support_text(current: str, prior: str | None, linked: str | None) -> str:
    lines: list[str] = []
    if prior and prior != current:
        lines.append(f'You mentioned "{prior}".')
    if linked and linked not in {prior, current}:
        lines.append(f'You mentioned "{linked}".')
    lines.append(f'You mentioned "{current}".')
    body = "\n\n".join(lines)
    return present(SUPPORT, body)


def understand(message: str, concerns: list[Concern], pending: str = "") -> Understanding:
    """Decide the thread. Crisis is handled before this. This does not write the reply."""
    text = message.strip()
    if pending == "today":
        if _FINE_ONLY.match(text):
            current = _latest_open(concerns)
            if current is None:
                return Understanding("open_ask")
            return Understanding("resume", label=current.label)
        pending = ""
    if pending == "else":
        if _YES_ONLY.match(text):
            return Understanding("else_ask", pending="else")
        if _NO_ONLY.match(text):
            return Understanding("stay")
        pending = ""
    if greeting_only(text):
        return Understanding("today", pending="today")
    if _SIGNPOST.search(normalize(text)):
        return Understanding("signpost")

    if _CLOSED.search(text):
        named = _settle(concerns, text, "closed")
        label = named.label if named is not None else "this"
        return Understanding("closed", label=label, quote=_snippet(text))

    if _EASED.search(text) and _BUT.search(text):
        left, right = _BUT.split(text, maxsplit=1)
        if _ease(concerns, left) is not None and right.strip():
            return _concern(right.strip(), concerns)

    if _EASED.search(text):
        named = _ease(concerns, text)
        if named is not None:
            return Understanding("eased", label=named.label, quote=_snippet(text))

    main, reason = _split_link(text)
    return _concern(main, concerns, reason)


def _split_link(message: str) -> tuple[str, str | None]:
    match = _LINK.search(message)
    if match is None:
        return message, None
    main = message[: match.start()].strip(" ,.;")
    reason = message[match.end() :].strip()
    if not main:
        return message, None
    return main, reason or None


def _settle(concerns: list[Concern], message: str, status: str) -> Concern | None:
    matches = _overlap(message, concerns)
    concern = matches[-1] if matches else _latest_open(concerns)
    if concern is None:
        return None
    concern.status = status
    _remember(concern, message)
    return concern


def _named_for_easing(concerns: list[Concern], message: str) -> Concern | None:
    matches = _overlap(message, concerns)
    if matches:
        return matches[-1]
    matter = content_words(message) - _IMPROVE_WORDS
    if matter:
        return None
    return _latest_open(concerns)


def _ease(concerns: list[Concern], message: str) -> Concern | None:
    concern = _named_for_easing(concerns, message)
    if concern is None:
        return None
    concern.status = "eased"
    _remember(concern, message)
    return concern


def _concern(message: str, concerns: list[Concern], reason: str | None = None) -> Understanding:
    current_words = content_words(message)
    matches = _overlap(message, concerns)
    continued = _CONTINUE.match(message.strip()) is not None and _latest_open(concerns) is not None

    if continued:
        concern = _latest_open(concerns)
    elif matches:
        concern = matches[-1]
    elif not current_words and _latest_open(concerns) is not None:
        label = _latest_open(concerns).label
        return Understanding("clarify", label=label)
    else:
        concern = Concern(_label(message))
        concerns.append(concern)

    assert concern is not None
    concern.status = "open"
    prior = concern.snippets[-1] if concern.snippets else None
    _remember(concern, message)
    _touch(concerns, concern)

    linked = _linked_snippet(reason, concerns, concern)
    current = concern.snippets[-1]
    return Understanding(
        "concern",
        label=concern.label,
        current=current,
        prior=prior,
        linked=linked,
        ask_else=continued,
        pending="else" if continued else "",
    )


def _linked_snippet(reason: str | None, concerns: list[Concern], primary: Concern) -> str | None:
    if not reason:
        return None
    others = [item for item in _overlap(reason, concerns) if item is not primary]
    if not others or not others[-1].snippets:
        return None
    return others[-1].snippets[-1]


def accept_draft(plan: Plan, drafted: str) -> str:
    if not isinstance(drafted, str):
        return plan.text
    cleaned = drafted.strip()
    lower = cleaned.lower()
    if plan.practical and plan.practical.lower() not in lower:
        return plan.text
    for bit in plan.must_keep:
        if bit.lower() not in lower:
            return plan.text
    if plan.practical:
        return grounded(SUPPORT, cleaned, plan.text)
    return plan.text
