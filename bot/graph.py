"""Microsoft Graph client with a built-in allow-list.

Every request is checked IN CODE before it is sent:
- GET is allowed only on the read paths the bot needs (devices, Autopilot,
  users, group membership, BitLocker key *metadata*).
- BitLocker key VALUES are never requested (the path is blocked even though
  the permission isn't granted either).
- The ONLY write: PUT file content on the Device Support site's document
  library (the inventory workbook). inventory.py adds further checks before
  every upload (folder "Device Inventory", .xlsx only).
- Everything else (POST/PATCH/DELETE, other sites, other paths) is refused.
"""
from __future__ import annotations

import re
from typing import Any, Protocol

import httpx

GRAPH = "https://graph.microsoft.com"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Agilify IT > Device Support (private channel) site: the ONLY site the bot can
# use (Sites.Selected "write" grant, recorded in m365-terraform privileged/README.md).
INVENTORY_SITE_ID = (
    "agilifyus.sharepoint.com,efee8780-9e83-4647-95df-afcf3d9fb11c,7fb1ad21-141a-49e1-b692-2ab54a0e1e3f"
)
_S = re.escape(INVENTORY_SITE_ID)

# Paths are matched against "<version>/<path>" without the query string.
_READ_ALLOW = [
    r"^(v1\.0|beta)/deviceManagement/managedDevices(/[^/]+)?$",
    r"^(v1\.0|beta)/deviceManagement/managedDevices/[^/]+/deviceCompliancePolicyStates(/[^/]+/settingStates)?$",
    r"^(v1\.0|beta)/deviceManagement/windowsAutopilotDeviceIdentities(/[^/]+)?$",
    r"^v1\.0/devices(/[^/]+)?$",
    r"^v1\.0/devices/[^/]+/(registeredUsers|memberOf)$",
    r"^v1\.0/users$",
    r"^v1\.0/users/[^/]+$",
    r"^v1\.0/users/[^/]+/(licenseDetails|managedDevices)$",
    r"^v1\.0/users/[^/]+/transitiveMemberOf(/microsoft\.graph\.group)?$",
    r"^v1\.0/informationProtection/bitlocker/recoveryKeys$",
    # Enrollment readiness (same reads as scripts/readonly/Check-EnrollmentReadiness.ps1)
    r"^beta/policies/mobileDeviceManagementPolicies(/[^/]+/includedGroups)?$",
    r"^beta/deviceManagement/deviceEnrollmentConfigurations$",
    # Inventory workbook on the Device Support site only
    rf"^v1\.0/sites/{_S}/drive/root/(children|search\(q='[^']*'\))$",
    rf"^v1\.0/sites/{_S}/drive/items/[^/:]+(/content|/versions|/children)?$",
]
_WRITE_ALLOW = {
    "PUT": [
        rf"^v1\.0/sites/{_S}/drive/items/[^/:]+/content$",                 # replace an existing file
        rf"^v1\.0/sites/{_S}/drive/items/[^/:]+:/[^/:]+\.xlsx:/content$",  # new .xlsx in a folder
    ],
}
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
        if query or not any(re.match(p, bare) for p in _WRITE_ALLOW.get(method, [])):
            raise GraphRefused(f"{method} not allowed: the bot is read-only ({bare})")
        return
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

    def _headers(self, **extra: str) -> dict:
        return {
            "Authorization": f"Bearer {self._token()}",
            "ConsistencyLevel": "eventual",
            "ocp-client-name": "Agilify-IT-Bot",
            "ocp-client-version": "1.0",
            **extra,
        }

    async def get(self, path: str) -> dict:
        check_allowed("GET", path)
        resp = await self._http.get(f"{GRAPH}/{path.lstrip('/')}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def get_bytes(self, path: str) -> bytes:
        """Download file content. Graph answers with a redirect to a pre-signed URL;
        httpx drops the Authorization header when the redirect leaves graph.microsoft.com."""
        check_allowed("GET", path)
        resp = await self._http.get(f"{GRAPH}/{path.lstrip('/')}", headers=self._headers(),
                                    follow_redirects=True, timeout=120)
        resp.raise_for_status()
        return resp.content

    async def put_bytes(self, path: str, data: bytes, if_match: str | None = None) -> tuple[int, dict]:
        """Upload file content (max 250 MB for this API). Returns (status, body) without raising,
        so callers can handle 412 (changed meanwhile) and 423 (locked) themselves."""
        check_allowed("PUT", path)
        extra = {"Content-Type": "application/octet-stream"}
        if if_match:
            extra["If-Match"] = if_match
        resp = await self._http.put(f"{GRAPH}/{path.lstrip('/')}", headers=self._headers(**extra),
                                    content=data, timeout=120)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body

    async def get_all(self, path: str, limit: int = 500) -> list[dict]:
        items: list[dict] = []
        page = await self.get(path)
        items.extend(page.get("value", []))
        while page.get("@odata.nextLink") and len(items) < limit:
            nxt = page["@odata.nextLink"].removeprefix(GRAPH + "/")
            page = await self.get(nxt)
            items.extend(page.get("value", []))
        return items[:limit]
