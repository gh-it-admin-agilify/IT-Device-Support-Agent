import pytest

from bot.graph import GraphRefused, check_allowed


@pytest.mark.parametrize(
    "path",
    [
        "v1.0/deviceManagement/managedDevices?$filter=serialNumber eq 'CQ38514'",
        "beta/deviceManagement/windowsAutopilotDeviceIdentities?$filter=contains(serialNumber,'CQ38514')",
        "v1.0/devices?$filter=displayName eq 'AGY-U-CQ38514'",
        "v1.0/users/abc/transitiveMemberOf/microsoft.graph.group?$select=id",
        "v1.0/informationProtection/bitlocker/recoveryKeys?$filter=deviceId eq 'x'",
    ],
)
def test_reads_allowed(path):
    check_allowed("GET", path)


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
def test_writes_refused(method):
    with pytest.raises(GraphRefused):
        check_allowed(method, "v1.0/devices/abc")


@pytest.mark.parametrize(
    "path",
    [
        "v1.0/informationProtection/bitlocker/recoveryKeys/abc123",
        "v1.0/informationProtection/bitlocker/recoveryKeys/abc123?$select=key",
        "v1.0/informationProtection/bitlocker/recoveryKeys?$select=key",
        "v1.0/me/messages",
        "v1.0/sites/root/drive/root/children",
        "v1.0/users/abc/mailFolders",
    ],
)
def test_blocked_or_not_listed(path):
    with pytest.raises(GraphRefused):
        check_allowed("GET", path)
