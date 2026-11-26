<#
  READ-ONLY, SENSITIVE. Shows the BitLocker recovery key(s) for one Entra device,
  with the Key ID to match against the laptop's recovery screen.

  *** A PERSON RUNS THIS IN THEIR OWN POWERSHELL WINDOW. THE AGENT NEVER RUNS IT. ***
  Anything a script prints while the Agent runs it lands in the chat transcript,
  and a recovery key must never be there. The script therefore:
    - refuses to run in a non-interactive session (how the Agent runs commands),
    - asks the person to type the device name to confirm,
    - prints to the screen only: never to logs.txt or any file.
  It is also blocked for the Agent in .claude/settings.json.

  Example (in your own PowerShell 7 window, repo root):
            .\scripts\readonly\Get-BitLockerKey.ps1 -DeviceName AGY-U-ABC1234
  Needs:    Microsoft.Graph.Authentication. Delegated scopes BitlockerKey.Read.All
            + Device.Read.All, and a role that may read keys (IT Support Tech:
            custom "BitLocker Key Reader" via sg-itdesk-support; Approver: Global Admin).
  Note:     every key read is recorded in the Entra audit log under your name.
            Prefer the Entra portal link from the bot when available.
  Used by:  runbooks reset-inspiron (before step 6).
#>
param(
    [Parameter(Mandatory)][string]$DeviceName
)
$ErrorActionPreference = 'Stop'

# 1. Refuse non-interactive runs (the Agent's tool runs PowerShell with -NonInteractive)
$args0 = [Environment]::GetCommandLineArgs()
if ($args0 | Where-Object { $_ -match '^-NonI' }) {
    Write-Host 'Refused: run this yourself in your own PowerShell window, not through the Agent.' -ForegroundColor Red
    return
}
$typed = Read-Host "Type the device name ($DeviceName) to show its BitLocker key on THIS screen"
if ($typed -ne $DeviceName) { Write-Host 'Name did not match - nothing shown.' -ForegroundColor Yellow; return }

Connect-MgGraph -NoWelcome -Scopes BitlockerKey.Read.All,Device.Read.All

$h = @{ 'ocp-client-name' = 'Agilify-IT-Device-Support-Agent'; 'ocp-client-version' = '1.0' }
$u = 'v1.0/informationProtection/bitlocker/recoveryKeys'

# 2. Find the Entra device by name -> its deviceId
$dev = (Invoke-MgGraphRequest -Method GET -Uri ("v1.0/devices?`$filter=displayName eq '$DeviceName'" +
        "&`$select=displayName,deviceId,accountEnabled") -OutputType PSObject).value
if (-not $dev) { Write-Host "No Entra device named $DeviceName" -ForegroundColor Red; return }
if (@($dev).Count -gt 1) { Write-Host "More than one Entra device named $DeviceName - stopping" -ForegroundColor Red; return }
Write-Host "Device: $($dev.displayName)  deviceId $($dev.deviceId)  enabled $($dev.accountEnabled)"

# 3. List its recovery keys, then read each key value (screen only)
$keys = (Invoke-MgGraphRequest -Method GET -Uri "$u`?`$filter=deviceId eq '$($dev.deviceId)'" -Headers $h -OutputType PSObject).value
if (-not $keys) { Write-Host 'No BitLocker keys stored in Entra for this device' -ForegroundColor Yellow; return }
foreach ($i in $keys) {
    $k = Invoke-MgGraphRequest -Method GET -Uri "$u/$($i.id)?`$select=key" -Headers $h -OutputType PSObject
    Write-Host ''
    Write-Host "Key ID : $($i.id)   (match the first 8 characters on the laptop screen)"
    Write-Host "Created: $($i.createdDateTime)   volume type $($i.volumeType)"
    Write-Host "Key    : $($k.key)" -ForegroundColor Green
}
Write-Host ''
Write-Host 'Type the key into the laptop, then close this window. Never copy the key anywhere else.' -ForegroundColor Yellow
