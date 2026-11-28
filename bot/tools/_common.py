"""Shared helpers for tools: safe input checks and user lookup."""
from __future__ import annotations

import re

SERIAL_RE = re.compile(r"^[A-Za-z0-9]{5,20}$")
_UPN_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,60}$")

# The two groups in the MDM auto-enrollment scope (Entra > Mobility > Microsoft Intune)
ENROLL_GROUPS = {
    "59d31b64-a3d5-48fd-b0ce-610ecff77c81": "Employees",
    "0d3c5ae7-41dd-4d12-aa5c-95165e1647e3": "IT",
}


def odata(value: str) -> str:
    """Escape a value for use inside '...' in an OData $filter."""
    return value.replace("'", "''")


def clean_serial(serial: str) -> str | None:
    serial = (serial or "").strip().upper()
    return serial if SERIAL_RE.match(serial) else None


async def find_users(graph, who: str) -> list[dict] | dict:
    """Find users by email/UPN (exact) or by display name (starts with).
    Returns a list of users, or {"error": ...} for unusable input."""
    who = (who or "").strip()
    select = "$select=id,displayName,userPrincipalName,accountEnabled,jobTitle"
    if _UPN_RE.match(who):
        users = await graph.get_all(f"v1.0/users?$filter=userPrincipalName eq '{odata(who)}'&{select}")
        if not users:  # maybe a mail alias
            users = await graph.get_all(f"v1.0/users?$filter=mail eq '{odata(who)}'&{select}")
        return users
    if _NAME_RE.match(who):
        return await graph.get_all(
            f"v1.0/users?$filter=startswith(displayName,'{odata(who)}') or startswith(givenName,'{odata(who)}')"
            f"&{select}&$top=10",
            limit=10,
        )
    return {"error": "Give a person's name (e.g. Jennifer Irons) or email address."}


def pick_one(users: list[dict]) -> dict:
    """Shape the result when 0 or many users match."""
    if not users:
        return {"error": "No matching person found. Check the spelling or use their email address."}
    return {
        "error": "More than one person matches; ask which one.",
        "candidates": [{"name": u.get("displayName"), "email": u.get("userPrincipalName")} for u in users],
    }
