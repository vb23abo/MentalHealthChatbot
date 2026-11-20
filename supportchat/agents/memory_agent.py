"""Keeps the account and the short saved chat.

It stores recent turns, the last topic, the safety flag, and a clinician note.
It does not decide whether a new message is a crisis.
"""

from __future__ import annotations

from supportchat.memory import MemoryStore


class MemoryAgent:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def close(self) -> None:
        self.store.close()

    def user_id_for_token(self, token: str) -> int | None:
        return self.store.user_id_for_token(token)

    def register(self, username: str, password: str) -> str:
        return self.store.register(username, password)

    def login(self, username: str, password: str) -> str:
        return self.store.login(username, password)

    def snapshot(self, user_id: int, before_id: int | None = None) -> dict:
        return self.store.snapshot(user_id, before_id)

    def clear(self, user_id: int) -> None:
        self.store.clear(user_id)

    def load_session(self, user_id: int):
        return self.store.load_session(user_id)

    def save_exchange(self, user_id: int, session, user_text: str, assistant_text: str, safety: str) -> None:
        self.store.save_exchange(user_id, session, user_text, assistant_text, safety)

    def set_country(self, user_id: int, country: str) -> str:
        return self.store.set_country(user_id, country)
