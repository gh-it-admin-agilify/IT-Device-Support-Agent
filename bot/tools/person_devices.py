"""Tool: which laptops does a person have? (read-only)
Intune devices where they are the primary user + Autopilot records assigned to them."""
from __future__ import annotations

from ._common import find_users, pick_one

SPEC = {
    "name": "person_devices",
    "description": (
        "List the laptops linked to one person: Intune devices where they are the primary "
        "user, and Windows Autopilot records assigned to them. Accepts a name (e.g. "
        "'Jennifer Irons' or 'Jennifer') or an email address. Read-only."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"person": {"type": "string", "description": "Name or email address"}},
        "required": ["person"],
    },
}


async def run(graph, person: str) -> dict:
    users = await find_users(graph, person)
    if isinstance(users, dict):
        return users
    if len(users) != 1:
        return pick_one(users)
    u = users[0]
    upn = (u.get("userPrincipalName") or "").lower()

    md = await graph.get_all(
        f"v1.0/users/{u['id']}/managedDevices?$select=deviceName,serialNumber,model,complianceState,"
        "isEncrypted,lastSyncDateTime,osVersion"
    )
    ap_all = await graph.get_all("beta/deviceManagement/windowsAutopilotDeviceIdentities")
    ap = [a for a in ap_all if (a.get("userPrincipalName") or "").lower() == upn]

    return {
        "person": {"name": u.get("displayName"), "email": u.get("userPrincipalName"),
                   "account_enabled": u.get("accountEnabled"), "job_title": u.get("jobTitle")},
        "intune_devices": [
            {"device_name": m.get("deviceName"), "serial": m.get("serialNumber"), "model": m.get("model"),
             "compliance": m.get("complianceState"), "encrypted": m.get("isEncrypted"),
             "last_check_in": m.get("lastSyncDateTime"), "os_version": m.get("osVersion")}
            for m in md
        ],
        "autopilot_assigned": [
            {"serial": a.get("serialNumber"), "model": a.get("model"),
             "enrollment_state": a.get("enrollmentState"), "last_contact": a.get("lastContactedDateTime")}
            for a in ap
        ],
    }
