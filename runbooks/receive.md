# Receive a laptop

For a laptop that arrives back: a user's old laptop after a swap, a leaver's
laptop, or a laptop returned for repair or reuse.

**Keep every record (Intune, Autopilot, Entra) until the laptop is in hand.**
Don't power it on and sign in: if it was the user's laptop, their data may
still be on it until it is wiped.

## On arrival

| # | Step | Done when |
|---|---|---|
| 1 | Check the serial (service tag underneath) | Matches the inventory row you expected. If not: tell the Agent, it looks the serial up |
| 2 | Check what came back | Laptop, charger, any accessories listed in inventory. Note anything missing or damaged |
| 3 | Photo of any damage | Sent to the Agent / Approver |
| 4 | Report arrival to the Agent | e.g. “SERIAL-2 arrived today, charger included, no damage” |

The Agent then:

- Updates the spreadsheet (Decommissioning or Stock tab: "Received <date>", condition).
- Checks the laptop's records read-only (`Check-LostLaptop.ps1 -Serial <serial>`):
  last check-in, user, BitLocker key present in Entra.
- Updates tasks.md.

## Decide what happens next

| Case | Next |
|---|---|
| Decision already recorded (e.g. “decommission”) | [decommission.md](decommission.md) |
| Reuse as stock | **CHANGE REQUEST**: Intune wipe. Then reset/provision when needed ([provision.md](provision.md)); Stock tab Status → "Available" after the wipe |
| Not decided | The Agent asks the Approver; the laptop stays powered off and stored |

## Before any wipe

- The user's OneDrive was synced before they shipped it (ask, if unsure).
- At least one BitLocker key exists in Entra for this laptop (step 4 check).
- The wipe itself is a **CHANGE REQUEST** run by the Approver.
