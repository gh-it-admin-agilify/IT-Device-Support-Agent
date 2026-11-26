<#
  READ-ONLY. Who is using the Agent right now, and in which mode?

  The Agent runs this at the start of every session (see CLAUDE.md, section 1).
  It reports:
    - the Microsoft account signed in to Microsoft Graph in this session
      (the account that passed MFA; this is what the Agent trusts)
    - that the account belongs to the Agilify tenant (agilifyus.com)
    - the Windows account of this session (for information only)
    - membership of the two IT Desk groups
    - the resulting MODE: APPROVER, SUPPORT or UNKNOWN

  Mode rules:
    member of the admins group                    -> APPROVER
    member of the support group (and not admins)  -> SUPPORT
    anything else, wrong tenant, or not signed in -> UNKNOWN

  Example:
    .\scripts\readonly\Get-WhoAmI.ps1
  Group names default to the IT Desk groups; override only if they are renamed:
    .\scripts\readonly\Get-WhoAmI.ps1 -AdminsGroup sg-itdesk-admins -SupportGroup sg-itdesk-support

  Needs:  PowerShell 7, Microsoft.Graph.Authentication module.
          Delegated scopes User.Read + GroupMember.Read.All
          (GroupMember.Read.All needs admin consent once for the tenant).
  Makes:  GET requests only. Changes nothing.
  Output: screen + logs.txt in the repo root. Last line is "MODE=<mode>"
          so the Agent can read it reliably.
#>
param(
    [string]$AdminsGroup  = 'sg-itdesk-admins',
    [string]$SupportGroup = 'sg-itdesk-support',
    [string]$TenantDomain = 'agilifyus.com'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$logFile  = Join-Path $repoRoot 'logs.txt'
$lines    = [System.Collections.Generic.List[string]]::new()

function Write-Line([string]$text, [string]$color = 'Gray') {
    Write-Host $text -ForegroundColor $color
    $script:lines.Add($text)
}
function Get-Graph([string]$uri) {
    Invoke-MgGraphRequest -Method GET -Uri $uri -OutputType PSObject
}
function Complete-Run([string]$mode, [string]$reason) {
    $color = switch ($mode) { 'APPROVER' { 'Green' } 'SUPPORT' { 'Cyan' } default { 'Yellow' } }
    Write-Line ''
    Write-Line ("MODE              : {0}" -f $mode) $color
    if ($reason) { Write-Line ("Reason            : {0}" -f $reason) $color }
    Write-Line ("MODE={0}" -f $mode)
    $script:lines | Out-File -FilePath $script:logFile -Encoding utf8
    exit 0
}

Write-Line ("=== Who am I  ({0}) ===" -f (Get-Date -Format 'yyyy-MM-dd HH:mm'))

# 1. Windows account (information only: an admin laptop may be signed in
#    to Windows with a different organisation's account)
$winUser = try { (whoami /upn 2>$null) } catch { $null }
if (-not $winUser) { $winUser = "$env:USERDOMAIN\$env:USERNAME" }
Write-Line ("Windows account   : {0}  (information only)" -f $winUser)

# 2. Graph sign-in (the identity the Agent trusts)
if (-not (Get-Module -ListAvailable Microsoft.Graph.Authentication)) {
    Write-Line 'Graph module      : NOT INSTALLED (Install-Module Microsoft.Graph.Authentication -Scope CurrentUser)' 'Red'
    Complete-Run 'UNKNOWN' 'Microsoft Graph module missing'
}
$ctx = Get-MgContext
if (-not $ctx -or -not $ctx.Account) {
    Write-Line 'Graph sign-in     : not signed in. Opening sign-in (use your own Agilify account + MFA)...' 'Yellow'
    try {
        Connect-MgGraph -NoWelcome -Scopes 'User.Read','GroupMember.Read.All'
        $ctx = Get-MgContext
    } catch {
        Write-Line ("Graph sign-in     : FAILED ({0})" -f $_.Exception.Message) 'Red'
        Complete-Run 'UNKNOWN' 'not signed in to Microsoft Graph'
    }
}
if ($ctx.AuthType -ne 'Delegated') {
    Write-Line ("Graph sign-in     : {0} (app sign-in, not a person)" -f $ctx.AuthType) 'Yellow'
    Complete-Run 'UNKNOWN' 'session is signed in as an app, not a person'
}

$me = Get-Graph 'v1.0/me?$select=id,displayName,userPrincipalName,accountEnabled'
Write-Line ("Signed-in account : {0}  ({1})" -f $me.userPrincipalName, $me.displayName)

# 3. Right tenant?
$org = (Get-Graph 'v1.0/organization?$select=displayName,verifiedDomains').value | Select-Object -First 1
$domains = @($org.verifiedDomains | ForEach-Object name)
if ($domains -notcontains $TenantDomain) {
    Write-Line ("Tenant            : {0}  NOT {1}" -f $org.displayName, $TenantDomain) 'Red'
    Complete-Run 'UNKNOWN' "signed in to a different tenant; sign in with your @$TenantDomain account"
}
Write-Line ("Tenant            : {0}  ({1})  OK" -f $org.displayName, $TenantDomain)

# 4. Group membership (direct or nested)
$groups = [System.Collections.Generic.List[object]]::new()
$uri = 'v1.0/me/transitiveMemberOf/microsoft.graph.group?$select=id,displayName&$top=999'
try {
    while ($uri) {
        $page = Get-Graph $uri
        $page.value | ForEach-Object { $groups.Add($_) }
        $uri = $page.'@odata.nextLink'
    }
} catch {
    Write-Line ("Group check       : FAILED ({0})" -f $_.Exception.Message) 'Red'
    Complete-Run 'UNKNOWN' 'could not read group membership (GroupMember.Read.All consent?)'
}
$isAdmin   = [bool]($groups | Where-Object displayName -eq $AdminsGroup)
$isSupport = [bool]($groups | Where-Object displayName -eq $SupportGroup)
Write-Line ("{0,-17} : {1}" -f $AdminsGroup,  $(if ($isAdmin)   { 'member' } else { 'not a member' }))
Write-Line ("{0,-17} : {1}" -f $SupportGroup, $(if ($isSupport) { 'member' } else { 'not a member' }))

# 5. Mode
if ($isAdmin)   { Complete-Run 'APPROVER' '' }
if ($isSupport) { Complete-Run 'SUPPORT'  '' }
Complete-Run 'UNKNOWN' "not in $AdminsGroup or $SupportGroup (groups may not exist yet)"
