# Known problems and proven fixes

Each entry: what you see → what it means → what to do. Dates show when it was
proven.

## Setup and reset

| You see | Means | Do |
|---|---|---|
| Shift + Restart just reboots normally (Inspiron 15 3530) | Recovery menu not reachable this way | Forced recovery: two interrupted starts → [runbooks/reset-inspiron.md](../runbooks/reset-inspiron.md) (2026-11-25) |
| SupportAssist OS Recovery stuck on Wi-Fi “Connecting…” | Its download can't get online | Use Windows **Local reinstall** instead (2026-11-25) |
| Dell menu with “Pre-boot tasks, BIOS setup…” | F12 boot menu | Choose **Windows Boot Manager** |
| BitLocker recovery screen after interrupted starts | Normal | Enter the key from Entra (match the Key ID first) |
| “Clear this computer's TPM? F12 / ESC” during reset | Normal for a reset | **F12** for a laptop going to a new user |
| Pre-provision QR screen says “Assigned user: not assigned” right after assigning | Laptop cached the profile before the change | Wait until the Autopilot record shows the user (~5 min), then **Cancel** → Windows ×5 again |
| Windows ×5 does nothing on the region screen | Rare | Try on the Agilify sign-in screen; fallback `sysprep /oobe /reboot` (Shift+F10 at setup) |
| “Activate Windows” notice during provisioning | Expected | Check activation after the user signs in |
| “Setting up your account” sits on Apps 0 of 1 for 45+ minutes | Microsoft 365 apps installing slowly | Leave it plugged in; don't restart (2026-11-10) |

## After sign-in

| You see | Means | Do |
|---|---|---|
| New laptop **noncompliant**: Defender “signature out of date” | Factory antivirus definitions | User: Windows Security → Protection updates → Check for updates; then Settings → Accounts → Access work or school → Info → **Sync**. Re-check ~1 hour later |
| Activation “Not active”, error **0x8007232B**, key ending **T83GX** (Inspiron 3530s) | Generic Windows Pro key that needs a server Agilify doesn't have | If the firmware has a Pro OEM key: install it with `slmgr /ipk` + `/ato` (runbooks/provision.md H2). Fixed on one laptop 2026-11-24 |
| Office not shown in the device's apps list | App inventory lags (up to ~7 days) | Not a fault; ask the user if in doubt |

## Records

| You see | Means | Do |
|---|---|---|
| Laptop in use (recent Entra sign-in, isManaged False) but **not in Intune**; Autopilot “notContacted” with a non-zero managedDeviceId | **Lost Intune record** | [runbooks/re-enroll-lost-record.md](../runbooks/re-enroll-lost-record.md): auto-enroll fix, no reset (2026-11-17) |
| Autopilot managedDeviceId **all zeros**, not in Intune | Never set up through Autopilot | Reset + Autopilot, or join it properly (Approver decides) |
| Device record named only by serial, disabled, “last sign-in” = ship date | Autopilot placeholder for a laptop never set up | Find the laptop; it is probably boxed stock |
| Entra device lists a **previous user** | Entra's “registered owner / user” labels can't be edited in the portal | **CHANGE REQUEST**: Set-DeviceUser.ps1 (labels only) |
| Autopilot record still there ~30 minutes after deleting | Autopilot deletes are slow | Wait before deleting the Entra device |
| Autopilot user name differs from who has the laptop | Autopilot user is not kept up to date | Trust Intune primary user + Entra sign-ins instead |

## Scripts

| You see | Means | Do |
|---|---|---|
| “logs.txt is being used by another process” | The script writes logs.txt itself and `Tee-Object` also tried | Run it without `Tee-Object` |
| A script shows nothing when `Write-Host` output was piped | `Write-Host` isn't captured by a plain pipe | Add `*>&1` before the pipe to `Tee-Object logs.txt` |
| A pasted command breaks across lines | Line wrap / backtick in the paste | Paste the command as **one line** |
| “not recognized” for Get-MgContext / Invoke-MgGraphRequest | Graph module not loaded; any “Not found” results are **false** | Use PowerShell 7 (`pwsh`); install `Microsoft.Graph.Authentication` |
