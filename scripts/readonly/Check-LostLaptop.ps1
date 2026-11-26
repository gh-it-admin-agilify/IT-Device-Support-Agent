<#
  READ-ONLY. Checks one laptop across Autopilot, Intune, Entra and BitLocker
  key escrow (key labels only, never key values). Changes nothing.

  Example:  .\scripts\readonly\Check-LostLaptop.ps1 -Serial ABC1234
            (device name assumed AGY-U-<serial>)
  Needs:    PowerShell 7, Microsoft.Graph.Authentication. Delegated scopes:
            DeviceManagementServiceConfig.Read.All, DeviceManagementManagedDevices.Read.All,
            Device.Read.All, User.Read.All, BitlockerKey.ReadBasic.All
  Output:   screen + logs.txt in the repo root.
  Used by:  runbooks provision (A2), receive, decommission, re-enroll-lost-record.
#>
param([Parameter(Mandatory)][string]$Serial)

$ErrorActionPreference = 'Stop'
$log = Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')) 'logs.txt'
$scopes = @(
    'DeviceManagementServiceConfig.Read.All',
    'DeviceManagementManagedDevices.Read.All',
    'Device.Read.All',
    'User.Read.All',
    'BitlockerKey.ReadBasic.All'
)
$ctx = Get-MgContext
$missing = if ($ctx) { $scopes | Where-Object { $_ -notin $ctx.Scopes } } else { $scopes }
if ($missing) { Connect-MgGraph -Scopes $scopes -NoWelcome }

$h = @{
    'ocp-client-name'    = 'Agilify-IT-Device-Support-Agent'
    'ocp-client-version' = '1.0'
}
function Get-G([string]$u) {
    Invoke-MgGraphRequest -Method GET -Uri $u -Headers $h -OutputType PSObject
}
function Format-Utc($d) {
    if (-not $d) { return '(none)' }
    $t = [datetime]$d
    $u = $t.ToUniversalTime().ToString('yyyy-MM-dd HH:mm')
    $l = $t.ToLocalTime().ToString('yyyy-MM-dd h:mm tt')
    "$u UTC = $l local"
}

$name = "AGY-U-$Serial"
$now  = Get-Date -Format 'yyyy-MM-dd HH:mm'
$out  = @("=== $name / serial $Serial  (checked $now local) ===")

# --- Autopilot ---
$f = "contains(serialNumber,'$Serial')"
$u = "beta/deviceManagement/windowsAutopilotDeviceIdentities?`$filter=$f"
$ap = (Get-G $u).value
if ($ap) {
    foreach ($a in $ap) {
        $out += "Autopilot : $($a.manufacturer) $($a.model) | " +
                "user $($a.userPrincipalName) | $($a.enrollmentState)"
        $out += "            profile $($a.deploymentProfileAssignmentStatus)" +
                " | last contact $(Format-Utc $a.lastContactedDateTime)"
        $out += "            managedDeviceId $($a.managedDeviceId)"
    }
} else { $out += 'Autopilot : NOT FOUND' }

# --- Intune (by serial, then by name) ---
$f = "serialNumber eq '$Serial'"
$md = (Get-G "v1.0/deviceManagement/managedDevices?`$filter=$f").value
if (-not $md) {
    $f = "deviceName eq '$name'"
    $md = (Get-G "v1.0/deviceManagement/managedDevices?`$filter=$f").value
}
if ($md) {
    foreach ($m in $md) {
        $out += "Intune    : $($m.deviceName) | $($m.userPrincipalName)" +
                " | $($m.complianceState) | encrypted $($m.isEncrypted)"
        $out += "            last check-in $(Format-Utc $m.lastSyncDateTime)"
    }
} else { $out += 'Intune    : NOT FOUND (by serial or name)' }

# --- Entra ---
$f = "displayName eq '$name'"
$sel = 'id,deviceId,displayName,accountEnabled,isManaged,trustType,' +
       'approximateLastSignInDateTime,registrationDateTime,' +
       'operatingSystemVersion'
$ed = (Get-G "v1.0/devices?`$filter=$f&`$select=$sel").value
if ($ed) {
    foreach ($e in $ed) {
        $out += "Entra     : $($e.displayName) | enabled $($e.accountEnabled)" +
                " | isManaged $($e.isManaged) | trust $($e.trustType)" +
                " | OS $($e.operatingSystemVersion)"
        $out += "            last sign-in " +
                "$(Format-Utc $e.approximateLastSignInDateTime)"
        $out += "            registered $(Format-Utc $e.registrationDateTime)"

        $ru = (Get-G "v1.0/devices/$($e.id)/registeredUsers").value
        $names = ($ru | ForEach-Object { $_.userPrincipalName }) -join ', '
        $out += "            registered users: $(if ($names) {$names} else {'(none)'})"

        # --- BitLocker keys escrowed for this device (labels only) ---
        $f = "deviceId eq '$($e.deviceId)'"
        $u = "v1.0/informationProtection/bitlocker/recoveryKeys?`$filter=$f"
        try {
            $k = (Get-G $u).value
            $out += "BitLocker : $(@($k).Count) key(s) in Entra"
            foreach ($x in $k) {
                $out += "            Key ID $($x.id.Substring(0,8))… created $(Format-Utc $x.createdDateTime)" +
                        " | volume $($x.volumeType)"
            }
        } catch {
            $out += "BitLocker : read FAILED - $($_.Exception.Message)"
        }
    }
} else { $out += 'Entra     : NOT FOUND' }

$out | ForEach-Object { Write-Host $_ }
$out | Set-Content -Path $log -Encoding utf8
