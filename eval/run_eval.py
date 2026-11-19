"""Run the scenario checks and print a pass/fail report."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.scenarios import SCENARIOS
from supportchat.service import handle_turn
from supportchat.session import Session


def run_scenario(scenario: dict, writer=None) -> tuple[bool, str]:
    session = Session(user_id=scenario["name"][:24].replace(" ", "-"))
    session.user_turns = scenario.get("user_turns", 0)
    result = None
    for message in scenario["messages"]:
        result = handle_turn(session, message, writer)
    assert result is not None
    text = result["response"].lower()
    problems: list[str] = []

    if "crisis" in scenario and result["crisis"] is not scenario["crisis"]:
        problems.append(f"crisis was {result['crisis']}, expected {scenario['crisis']}")
    if "urgent" in scenario and result["urgent"] is not scenario["urgent"]:
        problems.append(f"urgent was {result['urgent']}, expected {scenario['urgent']}")
    if scenario.get("no_resources") and result["resources"]:
        problems.append("expected no resources")
    if "visit_note" in scenario and bool(result.get("visit_note")) is not scenario["visit_note"]:
        problems.append(f"visit note presence was {bool(result.get('visit_note'))}, expected {scenario['visit_note']}")
    for needle in scenario.get("contains", []):
        if needle.lower() not in text:
            problems.append(f"missing {needle!r}")
    for needle in scenario.get("absent", []):
        if needle.lower() in text:
            problems.append(f"contained {needle!r}")
    if "checkin_status" in scenario and result["checkin"]["status"] != scenario["checkin_status"]:
        problems.append(
            f"check-in status was {result['checkin']['status']}, expected {scenario['checkin_status']}"
        )
    if "checkin_band" in scenario and result["checkin"]["band"] != scenario["checkin_band"]:
        problems.append(f"check-in band was {result['checkin']['band']}, expected {scenario['checkin_band']}")
    if "diagnosis" in result:
        problems.append("response included a diagnosis field")
    return not problems, "; ".join(problems)


class _TemplateModel:
    """Model stand-in that returns the template. Scenarios stay deterministic."""

    def write(self, message: str, topic: str, template: str) -> str:
        return template


def _report(writer, label: str) -> int:
    failed = 0
    print(f"\n{label}")
    for scenario in SCENARIOS:
        ok, detail = run_scenario(scenario, writer)
        mark = "pass" if ok else "fail"
        print(f"[{mark}] {scenario['name']}")
        if detail:
            failed += 1
            print(f"       {detail}")
    print(f"{len(SCENARIOS) - failed}/{len(SCENARIOS)} scenarios passed ({label})")
    return failed


def main() -> int:
    failed = _report(None, "model off")
    failed += _report(_TemplateModel(), "model on")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
