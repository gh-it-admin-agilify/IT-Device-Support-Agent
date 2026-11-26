# Provision a laptop for a user

From stock laptop to a user signed in on a compliant, encrypted laptop.
Proven on AGY-U-CQ38514 (Dell Inspiron 15 3530), 2026-11-25.

**Never sign in on the laptop yourself.** The first person to sign in becomes
its primary user and a local administrator.

---

## Part A: before touching the laptop (read-only)

| # | Check | How | Look for |
|---|---|---|---|
| A1 | Pick the laptop | Inventory spreadsheet, **Stock** tab | Status "Available". **Business laptop = 16 GB RAM**; 32 GB builds (Dell Pro 16 Ultra 7, Pro Max, Precision) are developer laptops |
| A2 | The laptop's records | `scripts\readonly\Check-LostLaptop.ps1 -Serial <serial>` | One Autopilot record with the profile assigned; who the Entra device's registered user is (a previous user's name means labels must move later, C3); at least one BitLocker key in Entra |
| A3 | The user is ready | `scripts\readonly\Check-EnrollmentReadiness.ps1 -Upn <upn> -Serial <serial>` | Account enabled; Business Premium (SPB) licence; member of **Employees** (or IT), which is what makes the laptop join Intune automatically; under the 10-device limit; laptop in **All Autopilot Devices**. Intune plans showing PendingInput / PendingActivation are normal in this tenant |
| A4 | Inventory | Agent updates the spreadsheet | Stock tab: Status → "Assigned: <user> (provisioning)" |

If A3 shows a missing licence or group: **CHANGE REQUEST** to the Approver before going further.

## Part B: optional, assign the user in Autopilot

Pre-fills the user's name on the sign-in screen. Cosmetic; skip if in a hurry.

- **CHANGE REQUEST**: `Set-AutopilotUser.ps1 -Serial <serial> -Upn <upn> -Step Assign`
  (Approver runs it; takes ~5 minutes to show).
- If the laptop is already on the pre-provision QR screen when it lands, click
  **Cancel**, then Windows key ×5 → Pre-provision again to reload it.

## Part C: reset the laptop

A reused laptop must be wiped first.

- Dell Inspiron 15 3530 (and any laptop where Shift+Restart does nothing):
  follow [reset-inspiron.md](reset-inspiron.md) to the region screen.
- Other laptops: from the sign-in screen, Power → hold **Shift** → Restart →
  Troubleshoot → Reset this PC → Remove everything → Local reinstall → Reset.
  Same BitLocker and TPM prompts as in reset-inspiron.md.

## Part D: get to the Agilify sign-in screen

| # | On screen | Do this |
|---|---|---|
| D1 | “Is this the right country or region?” | **United States** → Yes |
| D2 | Keyboard layout | **US** → Yes; second layout → **Skip** |
| D3 | Network | Connect Wi-Fi, wait for **Connected** → Next |
| D4 | Checking for updates | Wait; it may restart |
| D5 | Sign-in screen with **Agilify** branding | The Autopilot profile has downloaded. **Don't sign in.** |

## Part E: pre-provision and reseal

| # | On screen | Do this |
|---|---|---|
| E1 | Agilify sign-in screen | Press the **Windows key 5 times** |
| E2 | Pre-provision with Windows Autopilot · Install provisioning package | **Pre-provision with Windows Autopilot** → Continue |
| E3 | QR code screen | Check: organisation **agilifyus.com**, profile **Standard**, assigned user (or “not assigned”). Buttons are only Cancel / Next → **Next** |
| E4 | Setup progress | 20–40 minutes (policies, BitLocker settings, Edge / Chrome / Adobe). Plugged in. Don't touch it |
| E5 | **Green**: “Your device setup is complete … select Reseal” | **Reseal**. The laptop powers off. **Don't turn it on again**: the next person to power it on should be the user |
| E5 (red) | **Red** screen with an error | Photo of the error to the Agent / Approver. Don't retry until it's understood |

## Part F: confirm Intune has it (read-only)

`scripts\readonly\Check-NewLaptops.ps1 -DeviceName AGY-U-<serial>` *(to copy; writes logs.txt itself, don't add Tee-Object)*

Expected **before** the user signs in: enrolled today, recent last sync;
primary user blank; noncompliant; not encrypted; only the **old** BitLocker
key in Entra (it no longer works after the reset + TPM clear); Office not
detected yet. All normal.

Inventory: Stock tab Status → "Assigned: <user> (pre-provisioned <date>, shipping)".

## Part G: ship it

Follow [ship.md](ship.md).

## Part H: after the user signs in

| # | Check | How | Look for |
|---|---|---|---|
| H1 | Health | `Check-NewLaptops.ps1 -DeviceName AGY-U-<serial>` | Primary user = the user; **compliant**; **encrypted**; a **new** BitLocker key in Entra; recent last sync. Noncompliance from out-of-date Defender definitions usually clears after a sync |
| H2 | Windows activation (Inspiron 3530s) | Ask the user for Settings → System → Activation, or check in a Quick Assist session | “Active”. If “Not active” with error 0x8007232B: **CHANGE REQUEST** for the firmware-key fix (below) |
| H3 | Entra labels | A2 showed a previous user? | **CHANGE REQUEST**: `Set-DeviceUser.ps1 -DeviceName AGY-U-<serial> -NewUpn <upn> -OldUpn <old upn>` |
| H4 | Inventory | Agent updates the spreadsheet | Stock tab Status → "In use: <user> (<date>)"; close the provisioning issue |

### Activation fix (Approver, on the laptop, admin PowerShell)

Some Inspiron 3530s carry a generic Windows Pro key ending **T83GX** that never
activates. If the laptop has a Pro key in its firmware
(`(Get-CimInstance SoftwareLicensingService).OA3xOriginalProductKeyDescription`
shows *Professional OEM*), this activates it:

```powershell
$k=(Get-CimInstance SoftwareLicensingService).OA3xOriginalProductKey
cscript //nologo slmgr.vbs /ipk $k
cscript //nologo slmgr.vbs /ato
```

Never print or save the key itself.
