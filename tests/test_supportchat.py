import unittest

from eval.scenarios import SCENARIOS
from eval.run_eval import run_scenario
from supportchat.safety import assess


class SafetyTests(unittest.TestCase):
    def test_self_harm_includes_abuse_resources_when_both_match(self):
        result = assess("He hits me and I want to kill myself")
        self.assertEqual(result.level, "self_harm")
        names = {item["name"] for item in result.resources}
        self.assertIn("988 Suicide & Crisis Lifeline (US)", names)
        self.assertIn("National Domestic Violence Hotline (US)", names)

    def test_negated_violence_is_not_urgent(self):
        self.assertEqual(assess("I don't want to hurt him").level, "none")

    def test_song_lyric_is_not_abuse(self):
        self.assertEqual(assess("This song hits me hard").level, "none")

    def test_negated_self_harm_still_gets_resources(self):
        self.assertEqual(assess("I will not kill myself").level, "self_harm")


class ScenarioTests(unittest.TestCase):
    def test_every_scenario(self):
        failures = []
        for scenario in SCENARIOS:
            ok, detail = run_scenario(scenario)
            if not ok:
                failures.append(f"{scenario['name']}: {detail}")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
