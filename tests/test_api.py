import os
import tempfile
import unittest

from supportchat.web import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._dir.name, "test.sqlite")
        self.client = create_app(self.db_path).test_client()
        self.rules = {rule.rule for rule in self.client.application.url_map.iter_rules()}

    def tearDown(self):
        self.client.application.extensions["memory"].close()
        self._dir.cleanup()

    def auth(self, username="ada_lovelace", password="test-pass-1"):
        created = self.client.post("/register", json={"username": username, "password": password})
        self.assertEqual(created.status_code, 201)
        token = created.get_json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_removed_clinical_routes_are_gone(self):
        self.assertNotIn("/diagnose", self.rules)
        self.assertNotIn("/treatment-plan", self.rules)
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json()["role"], "support")

    def test_page_loads(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        html = page.get_data(as_text=True)
        self.assertIn("Support chat", html)
        self.assertIn("988", html)
        self.assertIn("Create account", html)
        self.assertNotIn("Psychotherapy", html)

    def test_conversation_requires_sign_in(self):
        response = self.client.post("/conversation", json={"message": "hello"})
        self.assertEqual(response.status_code, 401)

    def test_rejects_bad_payloads(self):
        headers = self.auth()
        self.assertEqual(
            self.client.post("/conversation", data="nope", content_type="text/plain", headers=headers).status_code,
            400,
        )
        self.assertEqual(self.client.post("/conversation", json={"message": "  "}, headers=headers).status_code, 400)
        self.assertEqual(
            self.client.post("/conversation", json={"message": "x" * 2001}, headers=headers).status_code,
            400,
        )

    def test_wrong_password_and_duplicate_username(self):
        self.auth()
        again = self.client.post("/register", json={"username": "ada_lovelace", "password": "test-pass-1"})
        self.assertEqual(again.status_code, 400)
        bad = self.client.post("/login", json={"username": "ada_lovelace", "password": "wrong-pass"})
        self.assertEqual(bad.status_code, 401)

    def test_return_visit_keeps_topic_and_messages(self):
        headers = self.auth()
        first = self.client.post("/conversation", json={"message": "I can't sleep"}, headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertNotIn("diagnosis", first.get_json())

        later = create_app(self.db_path).test_client()
        try:
            signed_in = later.post("/login", json={"username": "ada_lovelace", "password": "test-pass-1"})
            later_headers = {"Authorization": f"Bearer {signed_in.get_json()['token']}"}
            memory = later.get("/memory", headers=later_headers)
            body = memory.get_json()
            self.assertEqual(body["last_topic"], "sleep")
            self.assertIn("sleep", body["resume"].lower())
            self.assertIn("I can't sleep", [turn["text"] for turn in body["turns"]])
            self.assertNotIn("diagnosis", body)

            follow = later.post("/conversation", json={"message": "It's been weeks"}, headers=later_headers)
            self.assertIn("weeks", follow.get_json()["response"].lower())
            self.assertFalse(follow.get_json()["crisis"])
        finally:
            later.application.extensions["memory"].close()

    def test_crisis_is_remembered_as_a_safety_flag(self):
        headers = self.auth(username="sam_crisis")
        sent = self.client.post("/conversation", json={"message": "I want to die"}, headers=headers)
        self.assertTrue(sent.get_json()["crisis"])
        memory = self.client.get("/memory", headers=headers).get_json()
        self.assertEqual(memory["last_safety"], "self_harm")
        self.assertIn("988", memory["resume"])

    def test_delete_removes_saved_chats(self):
        headers = self.auth(username="delete_me")
        self.client.post("/conversation", json={"message": "I feel sad"}, headers=headers)
        deleted = self.client.post("/memory/delete", headers=headers)
        self.assertTrue(deleted.get_json()["deleted"])
        memory = self.client.get("/memory", headers=headers).get_json()
        self.assertEqual(memory["turns"], [])
        self.assertIsNone(memory["resume"])
        self.assertIsNone(memory["last_topic"])

    def test_recent_turns_are_trimmed(self):
        client = create_app(self.db_path, recent_limit=4).test_client()
        try:
            created = client.post("/register", json={"username": "trimmer", "password": "test-pass-1"})
            headers = {"Authorization": f"Bearer {created.get_json()['token']}"}
            for word in ("hello", "I feel sad", "thanks"):
                client.post("/conversation", json={"message": word}, headers=headers)
            turns = client.get("/memory", headers=headers).get_json()["turns"]
            self.assertEqual(len(turns), 4)
            self.assertNotIn("hello", [turn["text"] for turn in turns])
        finally:
            client.application.extensions["memory"].close()


if __name__ == "__main__":
    unittest.main()
