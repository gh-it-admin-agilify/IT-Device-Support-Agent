"""Tool: laptop status by Dell service tag / serial (read-only).
Same facts as scripts/readonly/Check-LostLaptop.ps1: Autopilot, Intune, Entra,
BitLocker key count (labels only)."""
from __future__ import annotations

import re

from ..graph import GraphClient

SPEC = {
    "name": "laptop_status",
    "description": (
        "Look up one laptop by its serial number (Dell service tag, e.g. CQ38514). "
        "Returns its Autopilot record, Intune status (user, compliance, encryption, "
        "last check-in), Entra device record and how many BitLocker keys are stored "
        "(labels only, never key values). Read-only."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "serial": {"type": "string", "description": "Laptop serial / service tag, letters and digits only"}
        },
        "required": ["serial"],
    },
}

_SERIAL = re.compile(r"^[A-Za-z0-9]{5,20}$")


def device_name(serial: str) -> str:
    s = serial.upper()
    return "AGY-U-" + (s[-9:] if len(s) > 9 else s)


async def run(graph: GraphClient, serial: str) -> dict:
    serial = (serial or "").strip()
    if not _SERIAL.match(serial):
        return {"error": "Serial must be 5-20 letters/digits, e.g. CQ38514."}
    serial = serial.upper()
    name = device_name(serial)
    out: dict = {"serial": serial, "device_name": name}

    ap = await graph.get_all(
        f"beta/deviceManagement/windowsAutopilotDeviceIdentities?$filter=contains(serialNumber,'{serial}')"
    )
    out["autopilot"] = [
        {
            "model": a.get("model"),
            "assigned_user": a.get("userPrincipalName") or None,
            "enrollment_state": a.get("enrollmentState"),
            "last_contact": a.get("lastContactedDateTime"),
        }
        for a in ap
    ] or "not found"

    md = await graph.get_all(f"v1.0/deviceManagement/managedDevices?$filter=serialNumber eq '{serial}'")
    out["intune"] = [
        {
            "device_name": m.get("deviceName"),
            "primary_user": m.get("userPrincipalName") or None,
            "compliance": m.get("complianceState"),
            "encrypted": m.get("isEncrypted"),
            "last_check_in": m.get("lastSyncDateTime"),
            "os_version": m.get("osVersion"),
        }
        for m in md
    ] or "not found"

    select = "&$select=id,deviceId,displayName,accountEnabled,isManaged,trustType,approximateLastSignInDateTime"
    # Prefer the exact Entra device ID Intune reports; fall back to the naming convention.
    entra_ids = [m.get("azureADDeviceId") for m in md if m.get("azureADDeviceId")]
    ed: list[dict] = []
    for dev_id in entra_ids:
        if not re.match(r"^[0-9A-Za-z-]{1,64}$", dev_id):
            continue
        ed += await graph.get_all(f"v1.0/devices?$filter=deviceId eq '{dev_id}'{select}")
    if not ed:
        ed = await graph.get_all(f"v1.0/devices?$filter=displayName eq '{name}'{select}")
    entra = []
    for e in ed:
        keys = await graph.get_all(
            f"v1.0/informationProtection/bitlocker/recoveryKeys?$filter=deviceId eq '{e.get('deviceId')}'"
        )
        entra.append(
            {
                "enabled": e.get("accountEnabled"),
                "is_managed": e.get("isManaged"),
                "join_type": e.get("trustType"),
                "last_sign_in": e.get("approximateLastSignInDateTime"),
                "bitlocker_keys_stored": len(keys),
                "bitlocker_key_ids_first8": [str(k.get("id", ""))[:8] for k in keys],
            }
        )
    out["entra"] = entra or "not found"
    return out
