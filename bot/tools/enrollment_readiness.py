"""Tool: is this laptop + person ready for Autopilot / Intune enrollment? (read-only)
Same checks as scripts/readonly/Check-EnrollmentReadiness.ps1."""
from __future__ import annotations

from ._common import ENROLL_GROUPS, clean_serial, find_users, odata, pick_one

SPEC = {
    "name": "enrollment_readiness",
    "description": (
        "Check whether a laptop and the person it is for are ready for enrollment: the "
        "person's account is enabled, has an Intune licence, is in the Employees or IT group "
        "(the MDM auto-enrollment scope), how many Intune devices they already have vs the "
        "enrollment limit, the laptop's Autopilot record (assigned user, profile status) and "
        "whether its Entra device is in the 'All Autopilot Devices' group. Read-only."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "person": {"type": "string", "description": "Name or email of the person the laptop is for"},
            "serial": {"type": "string", "description": "Laptop serial / Dell service tag"},
        },
        "required": ["person", "serial"],
    },
}


async def run(graph, person: str, serial: str) -> dict:
    s = clean_serial(serial)
    if not s:
        return {"error": "Serial must be 5-20 letters/digits, e.g. CQ38514."}
    users = await find_users(graph, person)
    if isinstance(users, dict):
        return users
    if len(users) != 1:
        return pick_one(users)
    u = users[0]
    out: dict = {"person": {"name": u.get("displayName"), "email": u.get("userPrincipalName"),
                            "account_enabled": u.get("accountEnabled")}, "serial": s}

    lic = await graph.get_all(f"v1.0/users/{u['id']}/licenseDetails")
    plans = [p for l in lic for p in l.get("servicePlans", []) if str(p.get("servicePlanName", "")).startswith("INTUNE")]
    out["licences"] = [l.get("skuPartNumber") for l in lic]
    out["intune_plans"] = [{"plan": p.get("servicePlanName"), "status": p.get("provisioningStatus")} for p in plans]

    groups = await graph.get_all(
        f"v1.0/users/{u['id']}/transitiveMemberOf/microsoft.graph.group?$select=id,displayName&$top=999"
    )
    out["in_enrollment_groups"] = [ENROLL_GROUPS[g["id"]] for g in groups if g.get("id") in ENROLL_GROUPS]

    scope = []
    for p in await graph.get_all("beta/policies/mobileDeviceManagementPolicies"):
        entry = {"policy": p.get("displayName"), "applies_to": p.get("appliesTo")}
        if p.get("appliesTo") == "selected":
            inc = await graph.get_all(f"beta/policies/mobileDeviceManagementPolicies/{p['id']}/includedGroups")
            entry["groups"] = [g.get("displayName") for g in inc]
        scope.append(entry)
    out["mdm_auto_enrollment_scope"] = scope

    cfgs = await graph.get_all("beta/deviceManagement/deviceEnrollmentConfigurations")
    limits = [c.get("limit") for c in cfgs if c.get("limit") is not None]
    current = await graph.get_all(f"v1.0/users/{u['id']}/managedDevices?$select=deviceName")
    out["device_limit"] = {"intune_devices_now": len(current), "limits_configured": limits}

    ap = await graph.get_all(
        f"beta/deviceManagement/windowsAutopilotDeviceIdentities?$filter=contains(serialNumber,'{odata(s)}')"
    )
    out["autopilot"] = [
        {"model": a.get("model"), "assigned_user": a.get("userPrincipalName") or None,
         "group_tag": a.get("groupTag"), "profile_status": a.get("deploymentProfileAssignmentStatus"),
         "enrollment_state": a.get("enrollmentState"), "last_contact": a.get("lastContactedDateTime")}
        for a in ap
    ] or "not found"

    did = next((a.get("azureAdDeviceId") for a in ap if a.get("azureAdDeviceId")), None)
    flt = f"deviceId eq '{odata(did)}'" if did else f"displayName eq 'AGY-U-{s}'"
    dev = await graph.get_all(f"v1.0/devices?$filter={flt}&$select=id,displayName,accountEnabled,trustType,isManaged")
    if dev:
        member_of = await graph.get_all(f"v1.0/devices/{dev[0]['id']}/memberOf?$select=displayName")
        names = [g.get("displayName") for g in member_of]
        out["entra_device"] = {"name": dev[0].get("displayName"), "enabled": dev[0].get("accountEnabled"),
                               "join_type": dev[0].get("trustType"), "is_managed": dev[0].get("isManaged"),
                               "in_all_autopilot_devices": "All Autopilot Devices" in names, "groups": names}
    else:
        out["entra_device"] = "not found"
    return out
