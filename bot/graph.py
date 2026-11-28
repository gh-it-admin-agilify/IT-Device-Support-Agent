"""Microsoft Graph client with a built-in allow-list.

Every request is checked IN CODE before it is sent:
- GET is allowed only on the read paths the bot needs (devices, Autopilot,
  users, group membership, BitLocker key *metadata*).
- BitLocker key VALUES are never requested (the path is blocked even though
  the permission isn't granted either).
- Any other method (POST/PATCH/PUT/DELETE) is refused. The single future
  exception - writing the inventory workbook on the Device Support site -
  will be added in step 5e with its own narrow rule.
"""
from __future__ import annotations

import re
from typing import Any, Protocol

import httpx

GRAPH = "https://graph.microsoft.com"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Paths are matched against "<version>/<path>" without the query string.
_READ_ALLOW = [
    r"^(v1\.0|beta)/deviceManagement/managedDevices(/[^/]+)?$",
    r"^(v1\.0|beta)/deviceManagement/managedDevices/[^/]+/deviceCompliancePolicyStates(/[^/]+/settingStates)?$",
    r"^(v1\.0|beta)/deviceManagement/windowsAutopilotDeviceIdentities(/[^/]+)?$",
    r"^v1\.0/devices(/[^/]+)?$",
    r"^v1\.0/devices/[^/]+/registeredUsers$",
    r"^v1\.0/users/[^/]+$",
    r"^v1\.0/users/[^/]+/(licenseDetails|managedDevices)$",
    r"^v1\.0/users/[^/]+/transitiveMemberOf(/microsoft\.graph\.group)?$",
    r"^v1\.0/informationProtection/bitlocker/recoveryKeys$",
]
_BLOCK = [
    r"recoveryKeys/[^/]+",          # a single key object could expose the value via $select=key
    r"\$select=[^&]*\bkey\b",
]


class TokenSource(Protocol):
    def get_token(self, *scopes: str) -> Any: ...


class GraphRefused(Exception):
    """Raised when a request is outside the allow-list. Never sent to Graph."""


def check_allowed(method: str, path: str) -> None:
    method = method.upper()
    bare, _, query = path.lstrip("/").partition("?")
    full = path.lstrip("/")
    if method != "GET":
        raise GraphRefused(f"{method} not allowed: the bot is read-only ({bare})")
    for pattern in _BLOCK:
        if re.search(pattern, full):
            raise GraphRefused(f"blocked path: {bare}")
    if not any(re.match(p, bare) for p in _READ_ALLOW):
        raise GraphRefused(f"path not on the allow-list: {bare}")


class GraphClient:
    def __init__(self, credential: TokenSource, http: httpx.AsyncClient | None = None):
        self._credential = credential
        self._http = http or httpx.AsyncClient(timeout=30)

    def _token(self) -> str:
        return self._credential.get_token(GRAPH_SCOPE).token

    async def get(self, path: str) -> dict:
        check_allowed("GET", path)
        resp = await self._http.get(
            f"{GRAPH}/{path.lstrip('/')}",
            headers={
                "Authorization": f"Bearer {self._token()}",
                "ConsistencyLevel": "eventual",
                "ocp-client-name": "Agilify-IT-Bot",
                "ocp-client-version": "1.0",
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def get_all(self, path: str, limit: int = 500) -> list[dict]:
        items: list[dict] = []
        page = await self.get(path)
        items.extend(page.get("value", []))
        while page.get("@odata.nextLink") and len(items) < limit:
            nxt = page["@odata.nextLink"].removeprefix(GRAPH + "/")
            page = await self.get(nxt)
            items.extend(page.get("value", []))
        return items[:limit]
