<!--
  CHANGE REQUEST TEMPLATE

  How the Agent uses this file:
  1. Copy it to requests\YYYY-MM-DD-<serial-or-user>-<short-action>.md
     e.g. requests\2026-12-02-SERIAL-2-decommission-records.md
  2. Fill in every section. Write "n/a" rather than deleting a section.
  3. Open a pull request with only this file (branch: request/<same name>).
  4. Tell the requester in plain words that the request has gone to the
     Approver, and what to do meanwhile.
  5. After the Approver runs the change, record the result in section 9 and
     re-check with a read-only script.

  Never put passwords, BitLocker keys, tokens or MFA codes in this file.
  Device facts only: no HR, disciplinary or incident details.
  Delete this comment block in the copy.
-->

# Change request: <short title, e.g. "Remove records for decommissioned laptop SERIAL-2">

| Field | Value |
|---|---|
| Request ID | YYYY-MM-DD-<serial-or-user>-<short-action> |
| Status | Draft / **Sent** / Approved / Rejected / Done / Cancelled |
| Requested by | IT Support Tech / Approver (role, and first name) |
| Drafted by | the Agent |
| Date sent | YYYY-MM-DD |
| Urgency | Normal / Today / Urgent (say why if not Normal) |
| Runbook step | e.g. `runbooks/decommission.md` step 6 |

## 1. What needs to change

One or two plain sentences: what the Approver is being asked to do.

## 2. Why

What happened that makes this necessary (e.g. "laptop returned, wiped on
YYYY-MM-DD, inventory row updated").

## 3. Target

| Item | Value |
|---|---|
| Device name | AGY-U-xxxxxxx |
| Serial | |
| User (UPN) | |
| Intune device ID | |
| Autopilot ID | |
| Entra device ID | |

## 4. Current state (read-only evidence)

What the Agent checked, with the script and time, so the Approver can see the
facts without re-running anything:

```text
<paste the relevant lines of logs.txt; no keys or secrets>
```

Checked with: `scripts/readonly/<script>.ps1 <parameters>` at YYYY-MM-DD HH:MM.

## 5. Exact change (the Approver runs this from his admin laptop)

Portal steps **or** command, exactly as they should be run, one action per
step. Use the Approver's existing change scripts where one exists (e.g.
`Remove-DeviceRecords.ps1 -Step …`, which checks first and asks for a typed
confirmation).

```powershell
<exact command(s)>
```

## 6. What this does NOT do

Things a reader might assume but that stay unchanged (e.g. "does not delete
the user's account, does not touch the BitLocker key until the Entra step").

## 7. Risk and undo

| | |
|---|---|
| Risk | Low / Medium / High, and what could go wrong |
| Can it be undone? | Yes / Partly / **No** |
| How to undo | exact steps, or "cannot be undone: <consequence>" |
| Order matters? | e.g. "Entra delete must be LAST: it removes the BitLocker key" |

## 8. Check after the change

The read-only check the Agent runs afterwards and what it expects to see:

`scripts/readonly/<script>.ps1 <parameters>` → expect: …

## 9. Decision and result (filled after the Approver acts)

| Field | Value |
|---|---|
| Decision | Approved / Rejected / Changed (say how) |
| Decided by | Approver (first name) |
| Decided on | YYYY-MM-DD |
| Run on | YYYY-MM-DD HH:MM, from the Approver's admin laptop |
| Result | What the after-check (section 8) showed |
| Inventory updated | Yes (tab, row, cells) / n/a |
| Notes | |
