"""First step for every message.

Matches help-seeking and danger language and returns resources. It does not
assess a disorder and it does not describe methods.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from supportchat.helplines import crisis_resources, crisis_sentence, normalize_country


def normalize(text: str) -> str:
    return text.lower().replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")


def _compile(patterns: list[str]) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{pattern})" for pattern in patterns), re.IGNORECASE)


_SELF_HARM = _compile(
    [
        r"\bsuicid(?:e|al)\b",
        r"\bkill(?:ing)? myself\b",
        r"\b(?:want|wanna|wish) to die\b",
        r"\bwish i (?:was|were) dead\b",
        r"\bwant(?:ed)? to be dead\b",
        r"\bbetter off dead\b",
        r"\bbetter off without me\b",
        r"\bno reason to live\b",
        r"\bno point (?:in living|in going on)\b",
        r"\bend my life\b",
        r"\btake my (?:own )?life\b",
        r"\b(?:don't|do not) want to (?:live|be alive|be here)\b",
        r"\bself[-\s]?harm(?:ing)?\b",
        r"\b(?:hurt|hurting|harm|harming) myself\b",
        r"\bcut(?:ting)? myself\b",
        r"\bunalive myself\b",
        r"\bi don'?t think i(?:'ll| will) be here tomorrow\b",
        r"\bi (?:might|may) not make it through the night\b",
        r"\bi(?:'m| am) thinking of ending it all\b",
        r"\bi want to end it all\b",
        r"\bi don'?t see a way out\b(?!\s+of\b)",
        r"\bbetter if i (?:wasn'?t|was not|weren'?t|were not) (?:around|here)\b(?!\s+[a-z])",
        r"\bi wish i wouldn'?t wake up\b(?!\s+(?:so|this|early|late|at|before|after)\b)",
    ]
)

_VIOLENCE = _compile(
    [
        r"\b(?:kill|hurt|harm) (?:him|her|them|someone)\b",
        r"\bwant to (?:kill|hurt|harm) (?:him|her|them|someone|people)\b",
        r"\bfeel like hurting (?:someone|him|her|them|people)\b(?!'s)",
    ]
)

_MEDICAL = _compile(
    [
        r"\bchest pain\b",
        r"\bheart attack\b",
        r"\bcan'?t breathe\b",
        r"\bcannot breathe\b",
        r"\btrouble breathing\b",
        r"\bmy chest hurts\b",
        r"\b(?:can'?t|cannot) catch my breath\b(?!\s+after\b)",
    ]
)

_ABUSE = _compile(
    [
        r"\b(?:he|she|they|partner|husband|wife|boyfriend|girlfriend|dad|mom|father|mother|parent) (?:hits|beats|chokes|hurts) me\b",
        r"\bdomestic violence\b",
        r"\b(?:being|physically) abused\b",
        r"\babusive (?:partner|husband|wife|boyfriend|girlfriend|parent|dad|mom)\b",
        r"\b(?:was|been) raped\b",
        r"\braped me\b",
        r"\bsexually assaulted\b",
        r"\bafraid to go home\b",
        r"\bdon'?t feel safe at home\b",
        r"\bscared of my (?:boyfriend|girlfriend|husband|wife|partner|dad|mom|father|mother)\b(?!'s)(?!\s+\w)",
    ]
)

_NEGATED = re.compile(
    r"(?:don't|do not|never|not going to|won't|will not)\b[^.]{0,40}$"
)

# Wording the phrase list above does not cover. The second check may add the
# crisis line from these. It is never used to remove a phrase-list match.
_SECOND_RAISE = _compile(
    [
        r"\bi have nothing left to live for\b(?!\s+in\b)",
    ]
)

# A shorter stem, with the ordinary continuations left out. Unsure fails closed.
_SECOND_UNSURE = _compile(
    [
        r"\bnothing left to live\b(?!\s+(?:for\s+in|on)\b)",
    ]
)

CRISIS_RESOURCES = crisis_resources("US")

ABUSE_RESOURCES = (
    {
        "name": "National Domestic Violence Hotline (US)",
        "contact": "1-800-799-7233",
        "url": "https://www.thehotline.org",
    },
    {
        "name": "RAINN sexual assault support (US)",
        "contact": "1-800-656-4673",
        "url": "https://www.rainn.org",
    },
)

MEDICAL_RESOURCES = (
    {
        "name": "Emergency services",
        "contact": "Your local emergency number",
        "url": None,
    },
)

PUBLIC_RESOURCES = {
    "crisis": list(CRISIS_RESOURCES),
    "abuse": list(ABUSE_RESOURCES),
    "medical": list(MEDICAL_RESOURCES),
}

_LEAD = {
    "self_harm": (
        "I'm glad you said this. I can't keep you safe in an emergency, and I'm not a crisis counselor. "
        "If you might act on thoughts of suicide or of hurting yourself, contact local emergency services now. "
        "In the US, call or text 988 (Suicide & Crisis Lifeline), any time. "
        "In other countries, find a local line at https://www.iasp.info/suicidalthoughts/. "
        "If you can, tell someone near you what is going on."
    ),
    "violence": (
        "I can't help with hurting someone. If you feel you might act on that, move away from them and contact local emergency services now. "
        "If you are also in danger, say that when you call."
    ),
    "medical": (
        "I can't tell whether this is a medical emergency. If you have chest pain, trouble breathing, fainting, or symptoms that feel severe or new, contact local emergency services now."
    ),
    "abuse": (
        "You deserve to be safe. If you are being hurt or threatened, local emergency services can help right now. "
        "In the US, the National Domestic Violence Hotline is 1-800-799-7233 or https://www.thehotline.org. "
        "RAINN supports people affected by sexual violence at 1-800-656-4673 or https://www.rainn.org."
    ),
}


def _has_match(pattern: re.Pattern[str], text: str, *, skip_negation: bool = False) -> bool:
    for match in pattern.finditer(text):
        if skip_negation:
            prefix = text[max(0, match.start() - 50) : match.start()]
            if _NEGATED.search(prefix):
                continue
        return True
    return False


def _dedupe(items: list[dict]) -> tuple[dict, ...]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        if item["name"] in seen:
            continue
        seen.add(item["name"])
        unique.append(item)
    return tuple(unique)


def _self_harm_message(country: str) -> str:
    return (
        "I'm glad you said this. I can't keep you safe in an emergency, and I'm not a crisis counselor. "
        "If you might act on thoughts of suicide or of hurting yourself, contact local emergency services now. "
        f"{crisis_sentence(country)} "
        "If you can, tell someone near you what is going on."
    )


def _abuse_message(country: str) -> str:
    if normalize_country(country) != "US":
        return (
            "You deserve to be safe. If you are being hurt or threatened, contact local emergency services now. "
            "A local helpline is in the IASP directory at https://www.iasp.info/suicidalthoughts/."
        )
    return _LEAD["abuse"]


@dataclass(frozen=True)
class SafetyResult:
    level: str
    resources: tuple[dict, ...]
    text: str | None = None

    @property
    def urgent(self) -> bool:
        return self.level != "none"

    @property
    def message(self) -> str | None:
        if self.text is not None:
            return self.text
        return _LEAD.get(self.level)


def assess(text: str, country: str = "US") -> SafetyResult:
    """Return the highest-priority safety match and every relevant resource."""
    normalized = normalize(text)
    self_harm = _has_match(_SELF_HARM, normalized)
    violence = _has_match(_VIOLENCE, normalized, skip_negation=True)
    medical = _has_match(_MEDICAL, normalized)
    abuse = _has_match(_ABUSE, normalized)

    resources: list[dict] = []
    message = None
    if self_harm:
        level = "self_harm"
        resources.extend(crisis_resources(country))
        message = _self_harm_message(country)
    elif violence:
        level = "violence"
        resources.extend(MEDICAL_RESOURCES)
    elif medical:
        level = "medical"
        resources.extend(MEDICAL_RESOURCES)
    elif abuse:
        level = "abuse"
        if normalize_country(country) == "US":
            resources.extend(ABUSE_RESOURCES)
        resources.extend(MEDICAL_RESOURCES)
        message = _abuse_message(country)
    else:
        level = "none"

    if (self_harm or violence) and abuse and normalize_country(country) == "US":
        resources.extend(ABUSE_RESOURCES)

    return SafetyResult(level=level, resources=_dedupe(resources), text=message)


def second_look(text: str) -> str:
    """A local check for wording the phrase list missed.

    Returns "raise", "unsure", or "clear". "clear" means this check found
    nothing to add. It does not mean a phrase-list match should be dropped.
    """
    normalized = normalize(text)
    if _has_match(_SECOND_RAISE, normalized):
        return "raise"
    if _has_match(_SECOND_UNSURE, normalized):
        return "unsure"
    return "clear"


def escalate(country: str = "US") -> SafetyResult:
    """The crisis result the second check is allowed to add."""
    return SafetyResult(
        level="self_harm",
        resources=tuple(crisis_resources(country)),
        text=_self_harm_message(country),
    )
