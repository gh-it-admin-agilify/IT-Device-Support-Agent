"""Fake Graph client for tests: no network, no tenant access."""
from __future__ import annotations

from bot.graph import check_allowed


class FakeGraph:
    def __init__(self, responses: dict[str, list[dict]]):
        # key: substring of the path -> list of items returned
        self.responses = responses
        self.calls: list[str] = []

    async def get_all(self, path: str, limit: int = 500) -> list[dict]:
        check_allowed("GET", path)  # tests also prove every call is on the allow-list
        self.calls.append(path)
        for key, value in self.responses.items():
            if key in path:
                return value
        return []

    async def get(self, path: str) -> dict:
        return {"value": await self.get_all(path)}
