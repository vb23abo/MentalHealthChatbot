"""Support replies.

Intent rules choose a short, bounded reply. Nothing here names a disorder
as the user's condition or assigns a treatment.
"""

from __future__ import annotations

import re

from supportchat.safety import normalize

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("goodbye", re.compile(r"\b(?:goodbye|bye|good night|that's all|thats all)\b")),
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
    ("next_step", re.compile(r"^(?:what should i do|what do i do)\??$")),
    ("panic", re.compile(r"\bpanic attack\b")),
    ("sleep", re.compile(r"\b(?:can't sleep|cannot sleep|insomnia|not sleeping|no sleep|awake all night)\b")),
    ("leave", re.compile(r"\bleave me alone\b")),
    ("lonely", re.compile(r"\b(?:lonely|alone|no one cares|no friends)\b")),
    ("anger", re.compile(r"\b(?:angry|furious|rage|so mad)\b")),
    ("worry", re.compile(r"\b(?:anxious|anxiety|worried|worry|panic|nervous|overwhelmed|stress(?:ed)?)\b")),
    ("sadness", re.compile(r"\b(?:sad|depress(?:ed|ion)|hopeless|empty|crying|miserable|numb|feeling down)\b")),
    ("greeting", re.compile(r"^(?:hi|hello|hey|good morning|good evening|good afternoon)\b")),
]

_PRIORITY = (
    "diagnosis",
    "treatment",
    "checkin",
    "panic",
    "leave",
    "sleep",
    "next_step",
    "lonely",
    "anger",
    "worry",
    "sadness",
    "goodbye",
    "thanks",
    "greeting",
)

REPLIES: dict[str, tuple[str, ...]] = {
    "greeting": (
        "Hi. I'm here to listen and help you sort through what you're feeling. What's been going on?",
        "Hello. Tell me what the day has been like, in whatever words you have.",
    ),
    "sadness": (
        "That sounds heavy. You don't have to justify feeling this way. "
        "If it helps, name one thing that would make the next hour a little easier, and do only that. "
        "If this has been most days for a couple of weeks, a doctor or counselor can help you sort out next steps.",
        "Low mood can make everything look flat. I can't tell you what condition this is. "
        "Name one thing that would make the next hour a little easier, and do only that.",
    ),
    "worry": (
        "Worry can take over the body as well as the thoughts. "
        "If you want a short reset: breathe in for four counts, hold for four, breathe out for six, and repeat that four times. "
        "If worry is constant or you're losing sleep over it, a clinician is the right person to assess it.",
        "It makes sense that your mind is trying to get ahead of this. "
        "Pick one worry you can act on today and one you are only rehearsing. We can talk through the one you can act on. "
        "For a short reset, breathe out for six counts.",
    ),
    "panic": (
        "If this feels like a panic attack, it often peaks and then eases. "
        "Try longer exhales than inhales, and put both feet on the floor. "
        "I can't tell a panic attack from a medical emergency. If you have chest pain, fainting, or breathing trouble that is severe or new, contact emergency services.",
    ),
    "sleep": (
        "Sleep and mood pull on each other. A steadier cue is a fixed wake-up time, and keeping the bed for sleep rather than for worrying. "
        "If sleep has been badly off for a while, tell a doctor. Several medical reasons can look like insomnia.",
        "If this has already gone on for weeks, tell a doctor when it started and how the days feel. "
        "A fixed wake-up time still matters more than trying to force sleep tonight.",
    ),
    "lonely": (
        "Feeling alone with this is painful. If one person usually feels safe, a short message to them today can matter. "
        "A counselor or a support line is a real option when no one close feels available.",
    ),
    "anger": (
        "Anger is often protecting something underneath, like hurt or fear. If you can, pause before you send the message or make the decision. "
        "If the anger is turning toward hurting yourself or someone else, contact local emergency services.",
    ),
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
    "next_step": (
        "I can't decide that for you. A useful next step is one small thing in the next hour, or telling a doctor or counselor what has been hardest. "
        "If you want, say a bit more about what today looks like.",
    ),
    "thanks": ("You're welcome. I'm here if you want to keep going.",),
    "goodbye": (
        "Take care. If things get worse, or if you might hurt yourself, contact local emergency services or call or text 988 in the US.",
    ),
    "default": (
        "Thank you for telling me. I can listen, sit with one concrete part of this, or walk through a short check-in about the last two weeks. "
        "What would be most useful right now?",
        "I'm with you. Say a little more about what this feels like in your body or in your day, and we'll stay with that.",
    ),
}

SLEEP_AND_WORRY = (
    "Anxiety and broken sleep often pull on each other. "
    "For the racing mind, try longer exhales: in for four counts, out for six, a few times. "
    "A fixed wake-up time helps more than trying to force sleep. "
    "If this has been most nights for a couple of weeks, tell a doctor. I can't tell worry, a sleep problem, and a medical issue apart."
)

SADNESS_AND_WORRY = (
    "Low mood and worry together are a lot to carry, and I won't put a disorder name on that. "
    "What is taking up more of today, the worry or the heaviness? "
    "A short reset is to breathe out for six counts."
)


def matched_intents(message: str) -> list[str]:
    text = normalize(message).strip()
    matched = [name for name, pattern in _PATTERNS if pattern.search(text)]
    if len(matched) > 1 and "greeting" in matched:
        matched.remove("greeting")
    return matched


def detect_intent(message: str) -> str:
    matched = matched_intents(message)
    if not matched:
        return "default"
    for name in _PRIORITY:
        if name in matched:
            return name
    return "default"


_ACK = re.compile(r"^(?:yes|yeah|yep|ok|okay|sure)[.!]?$")


def spoken_snippet(message: str) -> str | None:
    """A short piece of the person's own words, for the reply to echo."""
    text = " ".join(message.strip().split())
    if not text or _ACK.match(text.lower()):
        return None
    snippet = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    if len(snippet) > 90:
        snippet = snippet[:87].rstrip() + "..."
    return snippet


def reflect(message: str, body: str) -> str:
    snippet = spoken_snippet(message)
    if not snippet:
        return body
    return f'You mentioned "{snippet}".\n\n{body}'


def compound_reply(matched: list[str]) -> str | None:
    names = set(matched)
    if names & {"diagnosis", "treatment", "checkin", "leave", "goodbye", "thanks", "next_step"}:
        return None
    if "sleep" in names and ("worry" in names or "panic" in names):
        return SLEEP_AND_WORRY
    if "sadness" in names and "worry" in names:
        return SADNESS_AND_WORRY
    return None
