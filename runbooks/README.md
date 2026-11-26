# Runbooks

Step-by-step procedures the Agent follows and keeps up to date.

| Runbook | Use when |
|---|---|
| [provision.md](provision.md) | A laptop is being set up for a user (new or reused stock laptop) |
| [reset-inspiron.md](reset-inspiron.md) | A stock laptop must be wiped and the usual reset routes don't work (proven on Dell Inspiron 15 3530) |
| [ship.md](ship.md) | A laptop is being sent to a user |
| [receive.md](receive.md) | A laptop arrives back (returned, swapped, or a leaver's) |
| [decommission.md](decommission.md) | A laptop is being retired for good |
| [re-enroll-lost-record.md](re-enroll-lost-record.md) | A laptop is in use but missing from Intune (the "lost record" pattern) |

## How the Agent uses a runbook

- Says which runbook and which step the person is on.
- For hands-on steps: **asks what is on the screen first**, then gives **one**
  action for that exact screen.
- Runs only `scripts\readonly\` scripts. Any step marked **CHANGE REQUEST**
  is drafted with `requests\_TEMPLATE.md` and run by the Approver.
- When a step turns out different on a real laptop, updates the runbook (same
  pull request as the notes) and says what changed.

## Conventions in these files

- `<serial>`: the Dell service tag, e.g. `CQ38514`. Device name = `AGY-U-<serial>`
  (last 9 characters for long serials).
- `<upn>`: the user's sign-in, e.g. `first.last@agilifyus.com`.
- Scripts named here live in `scripts\readonly\`. `Get-BitLockerKey.ps1` is
  the exception: a person runs it in their own PowerShell window, never the Agent.
- Never write a BitLocker key, password or token anywhere.
