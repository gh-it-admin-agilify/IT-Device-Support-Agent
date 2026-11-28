"""Tool: laptops registered in Autopilot but NOT in Intune (read-only).
Same idea as scripts/readonly/Check-NewLaptops.ps1: new/unboxed laptops, lost
Intune records, or decommissioned laptops still in Autopilot."""
from __future__ import annotations

SPEC = {
    "name": "not_enrolled",
    "description": (
        "List laptops that are registered in Windows Autopilot but have no Intune record: "
        "new laptops not yet set up, laptops that lost their Intune record, or old laptops "
        "still in Autopilot. Returns serial, model, assigned user, Autopilot enrollment "
        "state and last contact. Read-only."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


async def run(graph) -> dict:
    ap = await graph.get_all("beta/deviceManagement/windowsAutopilotDeviceIdentities")
    md = await graph.get_all("v1.0/deviceManagement/managedDevices?$select=serialNumber")
    in_intune = {(m.get("serialNumber") or "").upper() for m in md}
    missing = [a for a in ap if (a.get("serialNumber") or "").upper() not in in_intune]
    missing.sort(key=lambda a: a.get("lastContactedDateTime") or "", reverse=True)
    return {
        "autopilot_total": len(ap),
        "intune_total": len(md),
        "not_in_intune": [
            {"serial": a.get("serialNumber"), "model": a.get("model"),
             "assigned_user": a.get("userPrincipalName") or None,
             "enrollment_state": a.get("enrollmentState"), "last_contact": a.get("lastContactedDateTime")}
            for a in missing
        ],
    }
