"""Crisis lines by country.

Numbers are the public national lines. When a country is not listed, the
reply keeps the IASP directory instead of inventing a number.
"""

from __future__ import annotations

IASP = {
    "name": "International Association for Suicide Prevention",
    "contact": "Local helpline directory",
    "url": "https://www.iasp.info/suicidalthoughts/",
}

EMERGENCY = {
    "name": "Emergency services",
    "contact": "Your local emergency number",
    "url": None,
}

COUNTRIES = {
    "US": {
        "name": "United States",
        "crisis": {
            "name": "988 Suicide & Crisis Lifeline (US)",
            "contact": "Call or text 988",
            "url": "https://988lifeline.org",
        },
    },
    "GB": {
        "name": "United Kingdom",
        "crisis": {
            "name": "Samaritans (UK)",
            "contact": "Call 116 123",
            "url": "https://www.samaritans.org",
        },
    },
    "IE": {
        "name": "Ireland",
        "crisis": {
            "name": "Samaritans (Ireland)",
            "contact": "Call 116 123",
            "url": "https://www.samaritans.org/ireland/",
        },
    },
    "CA": {
        "name": "Canada",
        "crisis": {
            "name": "9-8-8 Suicide Crisis Helpline (Canada)",
            "contact": "Call or text 9-8-8",
            "url": "https://988.ca",
        },
    },
    "AU": {
        "name": "Australia",
        "crisis": {
            "name": "Lifeline (Australia)",
            "contact": "Call 13 11 14",
            "url": "https://www.lifeline.org.au",
        },
    },
    "NZ": {
        "name": "New Zealand",
        "crisis": {
            "name": "Need to Talk? (New Zealand)",
            "contact": "Call or text 1737",
            "url": "https://1737.org.nz",
        },
    },
    "IN": {
        "name": "India",
        "crisis": {
            "name": "Tele-MANAS (India)",
            "contact": "Call 14416",
            "url": "https://telemanas.mohfw.gov.in",
        },
    },
}


def normalize_country(country: str | None) -> str:
    if not isinstance(country, str):
        return "US"
    code = country.strip().upper()
    if code in COUNTRIES or code == "OTHER":
        return code
    return "OTHER"


def country_choices() -> list[dict]:
    choices = [{"code": code, "name": item["name"]} for code, item in COUNTRIES.items()]
    choices.append({"code": "OTHER", "name": "Somewhere else"})
    return choices


def crisis_sentence(country: str | None) -> str:
    code = normalize_country(country)
    local = COUNTRIES.get(code, {}).get("crisis")
    if local is None:
        return (
            "A local number is not listed here. Find one in the IASP helpline directory "
            "at https://www.iasp.info/suicidalthoughts/."
        )
    return (
        f"{local['contact']} ({local['name']}). "
        "If that is not your country, use the IASP helpline directory at https://www.iasp.info/suicidalthoughts/."
    )


def crisis_resources(country: str | None) -> tuple[dict, ...]:
    code = normalize_country(country)
    items = []
    local = COUNTRIES.get(code, {}).get("crisis")
    if local is not None:
        items.append(local)
    items.append(IASP)
    items.append(EMERGENCY)
    return tuple(items)


def page_summary(country: str | None) -> str:
    return "Contact local emergency services. " + crisis_sentence(country)
