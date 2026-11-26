<#
  READ-ONLY. Is a user + laptop set up for Intune auto-enrollment and Autopilot?
   1 user   2 licences + Intune service plans   3 in Employees / IT groups
   4 MDM auto-enrollment scope   5 enrollment limits + user's devices
   6 Autopilot record   7 Entra device + its groups

  Example:  .\scripts\readonly\Check-EnrollmentReadiness.ps1 -Upn first.last@agilifyus.com -Serial ABC1234
            Entra device found via the Autopilot record, else name AGY-U-<serial>.
  Needs:    PowerShell 7, Microsoft.Graph.Authentication. Delegated scopes:
            User.Read.All, GroupMember.Read.All, Device.Read.All, Policy.Read.All,
            DeviceManagementServiceConfig.Read.All, DeviceManagementManagedDevices.Read.All
  Output:   logs.txt in the repo root (the script writes it itself: don't add Tee-Object).
  Used by:  runbooks provision (A3).

  Intune plans showing PendingInput / PendingActivation are normal in this tenant.
#>
param(
    [Parameter(Mandatory)][string]$Upn,
    [Parameter(Mandatory)][string]$Serial
)
$ErrorActionPreference = 'Stop'
$out = Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')) 'logs.txt'

# The two groups in the MDM auto-enrollment scope (Entra > Mobility > Microsoft Intune)
$enrollGroups = @{
    '59d31b64-a3d5-48fd-b0ce-610ecff77c81' = 'Employees'
    '0d3c5ae7-41dd-4d12-aa5c-95165e1647e3' = 'IT'
}

$scopes = @('User.Read.All','GroupMember.Read.All','Device.Read.All','Policy.Read.All',
            'DeviceManagementServiceConfig.Read.All','DeviceManagementManagedDevices.Read.All')
$ctx = Get-MgContext
$missing = if ($ctx) { $scopes | Where-Object { $_ -notin $ctx.Scopes } } else { $scopes }
if ($missing) { Connect-MgGraph -NoWelcome -Scopes $scopes }

function G($u) { Invoke-MgGraphRequest -Method GET -Uri $u -OutputType PSObject }
function W($title, $obj) {
  "`n=== $title" | Out-File $out -Append -Encoding utf8
  if ($null -eq $obj) { '   (nothing returned)' | Out-File $out -Append -Encoding utf8 }
  else { $obj | Format-List | Out-String -Width 250 | Out-File $out -Append -Encoding utf8 }
}
"--- Enrollment readiness: $Upn / $Serial  $(Get-Date -Format 'yyyy-MM-dd HH:mm')" | Out-File $out -Encoding utf8

# 1. Account
$u = G "v1.0/users/${Upn}?`$select=id,displayName,accountEnabled,usageLocation"
W '1 User' ($u | Select-Object displayName,accountEnabled,usageLocation,id)

# 2. Licence: Intune service plans
$lic = (G "v1.0/users/$($u.id)/licenseDetails").value
W '2a Licences (SKUs)' ($lic | Select-Object skuPartNumber)
W '2b Intune service plans' ($lic.servicePlans | Where-Object servicePlanName -like 'INTUNE*' |
  Select-Object servicePlanName,provisioningStatus)

# 3. Groups that matter (Employees / IT = MDM auto-enrollment scope)
$grp = (G "v1.0/users/$($u.id)/transitiveMemberOf/microsoft.graph.group?`$select=id,displayName&`$top=999").value
W '3 In Employees / IT?' ($grp | Where-Object { $enrollGroups.ContainsKey($_.id) } |
  Select-Object displayName,id)

# 4. MDM auto-enrollment scope (Entra > Mobility)
$mdm = (G "beta/policies/mobileDeviceManagementPolicies").value
foreach ($p in $mdm) {
  W "4 MDM scope: $($p.displayName)" ($p | Select-Object displayName,appliesTo,id)
  if ($p.appliesTo -eq 'selected') {
    W "4 MDM scope groups: $($p.displayName)" ((G "beta/policies/mobileDeviceManagementPolicies/$($p.id)/includedGroups").value |
      Select-Object displayName,id)
  }
}

# 5. Enrollment limits / restrictions
$cfg = (G "beta/deviceManagement/deviceEnrollmentConfigurations").value
W '5a Enrollment configs' ($cfg | Select-Object displayName,'@odata.type',priority,limit)
W '5b User Intune devices (count vs limit)' ((G "v1.0/users/$($u.id)/managedDevices?`$select=deviceName,operatingSystem,lastSyncDateTime").value |
  Select-Object deviceName,operatingSystem,lastSyncDateTime)

# 6. Autopilot record for this laptop
$ap = (G "beta/deviceManagement/windowsAutopilotDeviceIdentities?`$filter=contains(serialNumber,'$Serial')").value
W '6 Autopilot record' ($ap | Select-Object serialNumber,model,userPrincipalName,groupTag,deploymentProfileAssignmentStatus,enrollmentState,managedDeviceId,azureAdDeviceId,lastContactedDateTime)

# 7. Entra device: in "All Autopilot Devices"?
$did = @($ap | Where-Object azureAdDeviceId | Select-Object -First 1).azureAdDeviceId
$f = if ($did) { "deviceId eq '$did'" } else { "displayName eq 'AGY-U-$Serial'" }
$dev = (G "v1.0/devices?`$filter=$f&`$select=id,displayName,isManaged,accountEnabled,trustType").value
W '7a Entra device' ($dev | Select-Object displayName,accountEnabled,trustType,isManaged,id)
if ($dev) {
  W '7b Entra device groups' ((G "v1.0/devices/$($dev[0].id)/memberOf?`$select=displayName,id").value |
    Select-Object displayName,id)
}
"`n--- done" | Out-File $out -Append -Encoding utf8
Write-Host "Saved to $out"
