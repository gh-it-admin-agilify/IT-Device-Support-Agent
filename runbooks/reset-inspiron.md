# Reset a stock laptop when the usual routes fail

Proven on AGY-U-CQ38514 (Dell Inspiron 15 3530), 2026-11-25.
AGY-U-1JB9514 has the same problem.

**Erases everything on the laptop.** Confirm nothing on it is needed (previous
user has left, or their OneDrive is synced) before starting.

## What does NOT work on these laptops

| Tried | What happened |
|---|---|
| Shift + Restart from the sign-in screen | Reboots normally to Windows; no recovery menu |
| F12 → SupportAssist OS Recovery | Download screen stuck on Wi-Fi “Connecting…” |
| Pressing F12 during startup | Opens the Dell boot menu, not Windows recovery |

## Before you start

- Charger plugged in.
- BitLocker key ready (you will need it at step 6):
  - **Teams bot:** ask for the key link → open it → sign in + MFA → *Show recovery key*.
  - **Script:** in **your own** PowerShell window (never through the Agent):
    `.\scripts\readonly\Get-BitLockerKey.ps1 -DeviceName AGY-U-<serial>`. Screen only.
  - **Portal:** Entra admin center → Devices → All devices → AGY-U-<serial> → BitLocker keys.

## Steps

| # | On screen | Do this |
|---|---|---|
| 1 | Dell menu (“Pre-boot tasks, BIOS setup, Diagnostics, SupportAssist OS Recovery…”) | That's the F12 menu. Select **Windows Boot Manager** (near the top) → Enter |
| 2 | Windows sign-in screen | **Hold the power button ~10 seconds** until completely off |
| 3 | Off | Press power once. When the **Dell logo with spinning dots** appears, **hold power** until it turns off |
| 4 | Off | Do step 3 **once more** (two interrupted starts in total) |
| 5 | Off | Press power once and **touch nothing** |
| 6 | **BitLocker recovery** screen | Check the first 8 characters of the Recovery key ID match the key you have. Type the 48-digit key. (“Skip this drive” doesn't help: Local reinstall needs the drive unlocked) |
| 7 | Blue screen: Restart / Advanced options | **Advanced options** |
| 8 | Continue · Troubleshoot · Turn off your PC · Use a device | **Troubleshoot** |
| 9 | Reset this PC · Advanced options | **Reset this PC** |
| 10 | Keep my files · Remove everything | **Remove everything** |
| 11 | Cloud download · Local reinstall | **Local reinstall** (no Wi-Fi needed) |
| 12 | Reset this PC? (confirm) | **Reset** / Yes. 30–60 minutes, several restarts. Don't press anything |
| 13 | “A configuration change was requested to clear this computer's TPM … F12 to clear or ESC to reject” | **F12** (clear). Right for a laptop going to a new user |
| 14 | “Is this the right country or region?” | Reset done. Continue with [provision.md](provision.md) Part D |

## If something else appears

Stop, photo the screen, and send it to the Agent. Don't guess.
