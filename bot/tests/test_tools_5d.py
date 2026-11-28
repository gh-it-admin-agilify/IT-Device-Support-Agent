"""Tests for the 5d lookup tools and runbook tool, with a fake Graph.
FakeGraph also checks every call against the allow-list."""
from bot.tests.fakes import FakeGraph
from bot.tools import enrollment_readiness, not_enrolled, person_devices, runbook

USER_A = {"id": "u-a", "displayName": "User A", "userPrincipalName": "user.a@example.com", "accountEnabled": True}
AP = [
    {"serialNumber": "SERIAL1", "model": "Inspiron 15 3530", "userPrincipalName": "user.a@example.com",
     "enrollmentState": "enrolled", "azureAdDeviceId": "dev-1", "deploymentProfileAssignmentStatus": "assigned"},
    {"serialNumber": "SERIAL2", "model": "Inspiron 15 3530", "userPrincipalName": "",
     "enrollmentState": "notContacted", "lastContactedDateTime": "2026-11-20T00:00:00Z"},
]


# ---- person_devices
async def test_person_devices_by_email():
    g = FakeGraph({
        "v1.0/users?": [USER_A],
        "/managedDevices": [{"deviceName": "AGY-U-SERIAL1", "serialNumber": "SERIAL1", "complianceState": "compliant"}],
        "windowsAutopilotDeviceIdentities": AP,
    })
    out = await person_devices.run(g, person="user.a@example.com")
    assert out["person"]["email"] == "user.a@example.com"
    assert out["intune_devices"][0]["serial"] == "SERIAL1"
    assert [a["serial"] for a in out["autopilot_assigned"]] == ["SERIAL1"]


async def test_person_devices_ambiguous_name_asks():
    g = FakeGraph({"v1.0/users?": [USER_A, {**USER_A, "id": "u-b", "displayName": "User Ab",
                                             "userPrincipalName": "user.ab@example.com"}]})
    out = await person_devices.run(g, person="User")
    assert "candidates" in out and len(out["candidates"]) == 2


async def test_person_devices_rejects_odd_input():
    g = FakeGraph({})
    out = await person_devices.run(g, person="x) or 1 eq 1")
    assert "error" in out and g.calls == []


async def test_person_name_with_apostrophe_is_escaped():
    g = FakeGraph({})
    await person_devices.run(g, person="Dan O'Brien")
    assert "O''Brien" in g.calls[0]


# ---- enrollment_readiness
async def test_readiness_full():
    g = FakeGraph({
        "v1.0/users?": [USER_A],
        "licenseDetails": [{"skuPartNumber": "SPB", "servicePlans": [
            {"servicePlanName": "INTUNE_A", "provisioningStatus": "Success"},
            {"servicePlanName": "EXCHANGE_S_STANDARD", "provisioningStatus": "Success"}]}],
        "transitiveMemberOf": [{"id": "59d31b64-a3d5-48fd-b0ce-610ecff77c81"}],
        "includedGroups": [{"displayName": "Employees"}, {"displayName": "IT"}],
        "mobileDeviceManagementPolicies": [{"id": "p1", "displayName": "Microsoft Intune", "appliesTo": "selected"}],
        "deviceEnrollmentConfigurations": [{"displayName": "Default", "limit": 15}],
        "/managedDevices": [{"deviceName": "AGY-U-OLD"}],
        "windowsAutopilotDeviceIdentities": AP[:1],
        "/memberOf": [{"displayName": "All Autopilot Devices"}],
        "v1.0/devices?": [{"id": "e-1", "displayName": "AGY-U-SERIAL1", "accountEnabled": True}],
    })
    out = await enrollment_readiness.run(g, person="user.a@example.com", serial="serial1")
    assert out["intune_plans"] == [{"plan": "INTUNE_A", "status": "Success"}]
    assert out["in_enrollment_groups"] == ["Employees"]
    assert out["mdm_auto_enrollment_scope"][0]["groups"] == ["Employees", "IT"]
    assert out["device_limit"] == {"intune_devices_now": 1, "limits_configured": [15]}
    assert out["autopilot"][0]["assigned_user"] == "user.a@example.com"
    assert out["entra_device"]["in_all_autopilot_devices"] is True


async def test_readiness_bad_serial():
    g = FakeGraph({})
    out = await enrollment_readiness.run(g, person="user.a@example.com", serial="bad serial!")
    assert "error" in out and g.calls == []


# ---- not_enrolled
async def test_not_enrolled_lists_autopilot_without_intune():
    g = FakeGraph({
        "windowsAutopilotDeviceIdentities": AP,
        "managedDevices": [{"serialNumber": "serial1"}],
    })
    out = await not_enrolled.run(g)
    assert out["autopilot_total"] == 2 and out["intune_total"] == 1
    assert [d["serial"] for d in out["not_in_intune"]] == ["SERIAL2"]


# ---- runbook
async def test_runbook_list_and_get():
    listing = await runbook.run(None)
    names = [r["name"] for r in listing["runbooks"]]
    assert "reset-inspiron" in names and "provision" in names
    assert "readme" not in names
    assert any(k["name"] == "glossary" for k in listing["knowledge"])
    doc = await runbook.run(None, name="reset-inspiron")
    assert doc["kind"] == "runbooks" and len(doc["text"]) > 100


async def test_runbook_rejects_path_tricks():
    out = await runbook.run(None, name="../CLAUDE")
    assert "error" in out and "available" in out
