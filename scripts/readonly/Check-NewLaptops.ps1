<#
  READ-ONLY. Health check of newly provisioned Autopilot laptops.

  For each device name: primary user, compliance (per policy, plus the failing
  settings), encryption, BitLocker key escrow in Entra (labels only, never key
  values), Office detection and last sync. GET requests only; changes nothing.

  Example:  .\scripts\readonly\Check-NewLaptops.ps1 -DeviceName AGY-U-xxxx
            .\scripts\readonly\Check-NewLaptops.ps1 -DeviceName AGY-U-xxxx,AGY-U-yyyy
  Needs:    PowerShell 7, Microsoft.Graph.Authentication. Delegated scopes:
            DeviceManagementManagedDevices.Read.All, DeviceManagementConfiguration.Read.All,
            BitlockerKey.ReadBasic.All
  Output:   screen + logs.txt in the repo root (the script writes it itself:
            don't add Tee-Object, or you get "file in use").
  Used by:  runbooks provision (F, H1), re-enroll-lost-record.
#>
param(
    [Parameter(Mandatory)][string[]]$DeviceName,
    [string]$OutFile = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')) 'logs.txt')
)

$scopes = @(
    'DeviceManagementManagedDevices.Read.All'
    'DeviceManagementConfiguration.Read.All'
    'BitlockerKey.ReadBasic.All'
)

# Reuse the current Graph session; sign in (or add scopes) only if needed.
$ctx = Get-MgContext
$missing = if ($ctx) { $scopes | Where-Object { $_ -notin $ctx.Scopes } } else { $scopes }
if ($missing) {
    Write-Host "Signing in to Graph for: $($missing -join ', ')"
    Connect-MgGraph -Scopes $scopes -NoWelcome
}

# GET with paging.
function Get-All([string]$Uri) {
    $items = @()
    while ($Uri) {
        $r = Invoke-MgGraphRequest -Method GET -Uri $Uri
        $items += $r.value
        $Uri = $r.'@odata.nextLink'
    }
    $items
}

$report = [System.Collections.Generic.List[string]]::new()
function Out-Line([string]$Text) { $report.Add($Text); Write-Host $Text }

$okStates = @('compliant', 'notApplicable')
$sel = 'id,deviceName,userPrincipalName,complianceState,isEncrypted,' +
       'lastSyncDateTime,azureADDeviceId,osVersion,enrolledDateTime'

Out-Line "Laptop check - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

foreach ($name in $DeviceName) {
    Out-Line ''
    Out-Line "===== $name ====="

    $base = 'beta/deviceManagement/managedDevices'
    $found = Get-All "$base`?`$filter=deviceName eq '$name'&`$select=$sel"
    if (-not $found) { Out-Line 'Not found in Intune.'; continue }
    if (@($found).Count -gt 1) {
        Out-Line "Note: $(@($found).Count) Intune records; showing the most recent sync."
    }
    $d = @($found) | Sort-Object { [datetime]$_.lastSyncDateTime } -Descending |
        Select-Object -First 1

    Out-Line "Primary user : $($d.userPrincipalName)"
    Out-Line "Compliance   : $($d.complianceState)"
    Out-Line "Encrypted    : $($d.isEncrypted)"
    Out-Line "OS version   : $($d.osVersion)"
    Out-Line "Enrolled     : $($d.enrolledDateTime)"
    Out-Line "Last sync    : $($d.lastSyncDateTime)"

    # Compliance policies, with failing settings.
    $dev = "$base/$($d.id)"
    $policies = Get-All "$dev/deviceCompliancePolicyStates"
    Out-Line 'Compliance policies:'
    foreach ($p in $policies) {
        Out-Line "  $($p.displayName) = $($p.state)"
        if ($p.state -notin $okStates) {
            $settings = $p.settingStates
            if (-not $settings) {
                $settings = Get-All "$dev/deviceCompliancePolicyStates/$($p.id)/settingStates"
            }
            foreach ($s in $settings | Where-Object { $_.state -notin $okStates }) {
                Out-Line "      $($s.setting) [$($s.settingName)] = $($s.state)"
            }
        }
    }

    # BitLocker recovery keys escrowed to Entra (labels only, no key values).
    $keys = Get-All "v1.0/informationProtection/bitlocker/recoveryKeys?`$filter=deviceId eq '$($d.azureADDeviceId)'"
    Out-Line "BitLocker keys in Entra: $(@($keys).Count)"
    foreach ($k in $keys) { Out-Line "  $($k.volumeType) key, created $($k.createdDateTime)" }

    # Office detection. "Microsoft.MicrosoftOfficeHub" is the small Microsoft 365
    # hub app that ships with Windows, not the Office apps: ignore it.
    $apps = Get-All "$dev/detectedApps"
    $office = $apps | Where-Object {
        $_.displayName -match 'Microsoft 365|Office' -and $_.displayName -notmatch 'OfficeHub'
    }
    if ($office) {
        foreach ($a in $office) { Out-Line "Office       : $($a.displayName) $($a.version)" }
    } else {
        Out-Line "Office       : not detected yet ($(@($apps).Count) apps inventoried)"
    }
}

$report | Set-Content -Path $OutFile -Encoding utf8
Write-Host ''
Write-Host "Saved to $OutFile"
