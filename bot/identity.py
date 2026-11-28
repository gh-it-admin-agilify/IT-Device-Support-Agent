"""Who is messaging the bot? Decided ONLY by the sender's Entra object ID that
Teams verifies (activity.from_property.aad_object_id) and their group membership.
What someone types about who they are is never trusted."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from .graph import GraphClient


class Mode(str, Enum):
    APPROVER = "APPROVER"
    SUPPORT = "SUPPORT"
    UNKNOWN = "UNKNOWN"


@dataclass
class _Cached:
    mode: Mode
    at: float


class IdentityResolver:
    def __init__(self, graph: GraphClient, admins_group_id: str, support_group_id: str, ttl_seconds: int = 600):
        self._graph = graph
        self._admins = admins_group_id.lower()
        self._support = support_group_id.lower()
        self._ttl = ttl_seconds
        self._cache: dict[str, _Cached] = {}

    async def mode_for(self, aad_object_id: str | None) -> Mode:
        if not aad_object_id:
            return Mode.UNKNOWN
        key = aad_object_id.lower()
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit.at < self._ttl:
            return hit.mode
        groups = await self._graph.get_all(
            f"v1.0/users/{key}/transitiveMemberOf/microsoft.graph.group?$select=id&$top=999"
        )
        ids = {g.get("id", "").lower() for g in groups}
        mode = Mode.APPROVER if self._admins in ids else Mode.SUPPORT if self._support in ids else Mode.UNKNOWN
        self._cache[key] = _Cached(mode, time.monotonic())
        return mode
