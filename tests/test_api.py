import hashlib
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from supportchat.web import BIND_HOST, create_app


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
        self.assertIn("This chat is for adults", html)
        self.assertIn("under 18", html)
        self.assertIn("United Kingdom", html)
        self.assertLess(html.find('aria-label="Crisis resources"'), html.find("Your account"))
        gate, chat = html.split('id="chat-panel"', 1)
        self.assertIn("This chat is for adults", gate)
        self.assertIn("This chat is for adults", chat)
        self.assertIn("Create account", html)
        self.assertIn("Copy notes for a clinician", html)
        self.assertIn('maxlength="2000"', html)
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
        too_long = self.client.post("/conversation", json={"message": "x" * 2001}, headers=headers)
        self.assertEqual(too_long.status_code, 400)
        self.assertIn("2000", too_long.get_json()["error"])

    def test_wrong_password_and_duplicate_username(self):
        self.auth()
        again = self.client.post("/register", json={"username": "ada_lovelace", "password": "test-pass-1"})
        self.assertEqual(again.status_code, 400)
        bad = self.client.post("/login", json={"username": "ada_lovelace", "password": "wrong-pass"})
        self.assertEqual(bad.status_code, 401)

    def test_old_token_is_refused_and_sign_in_still_works(self):
        headers = self.auth(username="old_token")
        token = headers["Authorization"].split(" ", 1)[1]
        store = self.client.application.extensions["memory"].store

        def age(days: int) -> None:
            created = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            store._conn.execute(
                "UPDATE tokens SET created_at = ? WHERE token_hash = ?",
                (created, hashlib.sha256(token.encode("utf-8")).hexdigest()),
            )
            store._conn.commit()

        age(6)
        self.assertEqual(self.client.get("/memory", headers=headers).status_code, 200)
        age(8)
        refused = self.client.get("/memory", headers=headers)
        self.assertEqual(refused.status_code, 401)
        signed_in = self.client.post("/login", json={"username": "old_token", "password": "test-pass-1"})
        self.assertEqual(signed_in.status_code, 200)
        fresh = {"Authorization": "Bearer " + signed_in.get_json()["token"]}
        self.assertEqual(self.client.get("/memory", headers=fresh).status_code, 200)

    def test_burst_of_bad_passwords_is_refused(self):
        self.auth(username="burst_user")
        limited = create_app(self.db_path, login_limit=3).test_client()
        try:
            for _ in range(3):
                bad = limited.post("/login", json={"username": "burst_user", "password": "wrong-pass-1"})
                self.assertEqual(bad.status_code, 401)
            blocked = limited.post("/login", json={"username": "burst_user", "password": "test-pass-1"})
            self.assertEqual(blocked.status_code, 429)
            self.assertNotIn("test-pass-1", blocked.get_json()["error"])
        finally:
            limited.application.extensions["memory"].close()

    def test_message_text_stays_out_of_the_log(self):
        headers = self.auth(username="quiet_log")
        secret = "zephyr-private-note"
        with self.assertLogs("supportchat.web", level="INFO") as caught:
            sent = self.client.post("/conversation", json={"message": secret}, headers=headers)
        self.assertEqual(sent.status_code, 200)
        logged = "\n".join(caught.output)
        self.assertIn("POST /conversation 200", logged)
        self.assertNotIn(secret, logged)

    def test_server_stays_on_this_computer(self):
        self.assertEqual(BIND_HOST, "127.0.0.1")

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
            self.assertEqual(body["last_topic"], "I can't sleep")
            self.assertEqual(body["resume"], "How are you today?")
            self.assertIn("I can't sleep", [turn["text"] for turn in body["turns"]])
            self.assertNotIn("diagnosis", body)

            fine = later.post("/conversation", json={"message": "I'm fine"}, headers=later_headers)
            fine_text = fine.get_json()["response"].lower()
            self.assertIn("i can't sleep", fine_text)
            self.assertNotIn("one small thing", fine_text)

            follow = later.post("/conversation", json={"message": "It's been weeks"}, headers=later_headers)
            follow_text = follow.get_json()["response"].lower()
            self.assertIn("weeks", follow_text)
            self.assertIn("i can't sleep", follow_text)
            self.assertFalse(follow.get_json()["crisis"])

            free = later.post("/conversation", json={"message": "My neighbour's dog barks all night"}, headers=later_headers)
            reply = free.get_json()["response"].lower()
            self.assertIn("dog", reply)
            self.assertNotIn("i can't sleep", reply)
            self.assertIn("dog", later.get("/memory", headers=later_headers).get_json()["last_topic"].lower())
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

    def test_high_checkin_note_is_there_on_return(self):
        headers = self.auth(username="note_visit")
        for message in (
            "I can't sleep",
            "It's been weeks",
            "Work has been the hardest part",
            "check-in",
            "3",
            "3",
            "3",
            "3",
        ):
            sent = self.client.post("/conversation", json={"message": message}, headers=headers)
            self.assertEqual(sent.status_code, 200)
        finished = sent.get_json()
        note = finished["visit_note"]
        self.assertIn("I can't sleep", note)
        self.assertIn("It's been weeks", note)
        self.assertIn("hardest part", note)
        self.assertIn("not a diagnosis", note)
        self.assertNotIn("depression", note.lower())

        later = create_app(self.db_path).test_client()
        try:
            signed_in = later.post("/login", json={"username": "note_visit", "password": "test-pass-1"})
            later_headers = {"Authorization": f"Bearer {signed_in.get_json()['token']}"}
            memory = later.get("/memory", headers=later_headers).get_json()
            self.assertEqual(memory["visit_note"], note)
            deleted = later.post("/memory/delete", headers=later_headers)
            self.assertTrue(deleted.get_json()["deleted"])
            cleared = later.get("/memory", headers=later_headers).get_json()
            self.assertIsNone(cleared["visit_note"])
        finally:
            later.application.extensions["memory"].close()

    def test_country_changes_the_crisis_number(self):
        listed = self.client.get("/resources?country=GB").get_json()
        self.assertIn("116 123", listed["summary"])
        self.assertIn("iasp.info", listed["summary"])
        self.assertNotIn("988", listed["summary"])
        somewhere = self.client.get("/resources?country=ZZ").get_json()
        self.assertEqual(somewhere["country"], "OTHER")
        self.assertIn("not listed", somewhere["summary"])
        self.assertTrue(any("iasp.info" in (item.get("url") or "") for item in somewhere["crisis"]))

        headers = self.auth(username="uk_visit")
        saved = self.client.post("/country", json={"country": "GB"}, headers=headers)
        self.assertEqual(saved.status_code, 200)
        crisis = self.client.post(
            "/conversation",
            json={"message": "I want to die", "country": "GB"},
            headers=headers,
        )
        body = crisis.get_json()
        self.assertTrue(body["crisis"])
        self.assertIn("116 123", body["response"])
        self.assertNotIn("988", body["response"])
        self.assertIn("Call 116 123", [item["contact"] for item in body["resources"]])
        memory = self.client.get("/memory", headers=headers).get_json()
        self.assertEqual(memory["country"], "GB")
        self.assertIn("116 123", memory["resume"])

    def test_low_checkin_has_no_crisis_resources(self):
        headers = self.auth(username="low_visit")
        finished = None
        for message in ("check-in", "0", "0", "0", "0"):
            finished = self.client.post("/conversation", json={"message": message}, headers=headers)
        body = finished.get_json()
        self.assertEqual(body["checkin"]["band"], "low")
        self.assertEqual(body["resources"], [])
        self.assertIsNone(body["visit_note"])
        self.assertNotIn("988", body["response"])

    def test_return_past_40_messages_still_replies(self):
        headers = self.auth(username="long_visit")
        self.client.post("/conversation", json={"message": "I can't sleep"}, headers=headers)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE profiles SET user_turns = 40")
        follow = self.client.post("/conversation", json={"message": "I lie awake until 4"}, headers=headers)
        self.assertEqual(follow.status_code, 200)
        reply = follow.get_json()["response"].lower()
        self.assertIn("lie awake", reply)
        self.assertIn("one small thing that would make the next hour a little easier", reply)
        self.assertNotIn("gone on for a while", reply)

    def test_page_opens_on_a_window_and_keeps_earlier_turns(self):
        client = create_app(self.db_path, recent_limit=4).test_client()
        try:
            created = client.post("/register", json={"username": "trimmer", "password": "test-pass-1"})
            headers = {"Authorization": f"Bearer {created.get_json()['token']}"}
            for word in ("hello", "I feel sad", "thanks"):
                client.post("/conversation", json={"message": word}, headers=headers)
            page = client.get("/memory", headers=headers).get_json()
            self.assertEqual(len(page["turns"]), 4)
            self.assertGreater(page["earlier"], 0)
            self.assertNotIn("hello", [turn["text"] for turn in page["turns"]])
            older = client.get("/memory?before=" + str(page["turns"][0]["id"]), headers=headers).get_json()
            self.assertIn("hello", [turn["text"] for turn in older["turns"]])
        finally:
            client.application.extensions["memory"].close()


if __name__ == "__main__":
    unittest.main()
