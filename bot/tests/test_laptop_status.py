from bot.tests.fakes import FakeGraph
from bot.tools import laptop_status


def fake():
    return FakeGraph(
        {
            "windowsAutopilotDeviceIdentities": [
                {"model": "Inspiron 15 3530", "userPrincipalName": "user.a@example.com", "enrollmentState": "enrolled"}
            ],
            "managedDevices": [
                {"deviceName": "AGY-U-SERIAL1", "userPrincipalName": "user.a@example.com",
                 "complianceState": "compliant", "isEncrypted": True, "azureADDeviceId": "dev-1"}
            ],
            "v1.0/devices?": [{"deviceId": "dev-1", "accountEnabled": True, "trustType": "AzureAd"}],
            "recoveryKeys": [{"id": "1234567890abcdef"}],
        }
    )


async def test_rejects_bad_serial():
    g = fake()
    out = await laptop_status.run(g, serial="SER'; drop")
    assert "error" in out and g.calls == []


async def test_full_lookup_uses_allowed_paths_and_no_key_values():
    g = fake()
    out = await laptop_status.run(g, serial="serial1")
    assert out["serial"] == "SERIAL1"
    assert out["intune"][0]["compliance"] == "compliant"
    assert out["entra"][0]["bitlocker_keys_stored"] == 1
    assert out["entra"][0]["bitlocker_key_ids_first8"] == ["12345678"]
    assert "key" not in str(out).replace("keys_stored", "").replace("key_ids", "")
    assert any("deviceId eq 'dev-1'" in c for c in g.calls)  # Entra found via Intune's device ID


async def test_not_found():
    out = await laptop_status.run(FakeGraph({}), serial="NOPE123")
    assert out["autopilot"] == "not found" and out["intune"] == "not found" and out["entra"] == "not found"
