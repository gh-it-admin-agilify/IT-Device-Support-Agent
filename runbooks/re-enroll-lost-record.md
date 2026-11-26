# Re-enroll a laptop that lost its Intune record

For a laptop that is **in use** but missing from Intune. Proven on
AGY-U-7K1K5H4, 2026-11-17: fixed in place, no reset, user's data kept.

## How to recognise it (read-only)

`Check-LostLaptop.ps1 -Serial <serial>` shows all of:

- Autopilot: enrollmentState **notContacted**, but a managedDeviceId that isn't
  all zeros (it was enrolled once).
- Intune: **NOT FOUND**.
- Entra: device enabled, joined (AzureAd), **isManaged False**, recent sign-in.

If the managedDeviceId **is** all zeros, the laptop was never set up through
Autopilot: this runbook doesn't apply (usually a reset + Autopilot instead).

## The fix (Approver, with the user, in a Quick Assist session)

The user starts **Quick Assist** (Ctrl + Windows + Q) and shares the code. Note:
an admin (UAC) prompt only shows on the user's screen and pauses the session.

| # | Step |
|---|---|
| 1 | `winver`: note the Windows version (very old builds need updating after enrollment) |
| 2 | Open **gpedit.msc** → Computer Configuration → Administrative Templates → Windows Components → MDM |
| 3 | **Enable automatic MDM enrollment using default Azure AD credentials** → Enabled, credential type **User Credential** → OK |
| 4 | Restart; the user signs in |
| 5 | Wait ~10 minutes: Settings → Accounts → Access work or school → the Agilify account now has an **Info** button |
| 6 | Optional: activation check (provision.md, H2) |

This is a change to the laptop (and enrolls it), so it goes through a
**CHANGE REQUEST** first.

## Check afterwards (read-only)

`Check-LostLaptop.ps1 -Serial <serial>` → Intune record found, primary user =
the user; Autopilot enrollmentState **enrolled** with a new managedDeviceId;
Entra isManaged True. Then `Check-NewLaptops.ps1 -DeviceName AGY-U-<serial>`
→ compliant, encrypted, BitLocker key in Entra.

## If it fails

Event Viewer → Applications and Services Logs → Microsoft → Windows →
DeviceManagement-Enterprise-Diagnostics-Provider → Admin. Photo of the errors
to the Approver. Fallback: back up the user's data (OneDrive), then reset +
Autopilot.
