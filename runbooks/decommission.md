# Decommission a laptop

Retire a laptop for good and remove its cloud records in the right order.

**Every delete is a CHANGE REQUEST run by the Approver.** The Agent drafts one
request per step (or one request covering the steps in order), with read-only
evidence before and after.

## The order (don't change it)

| # | Step | Why the order matters |
|---|---|---|
| 1 | **In hand.** Laptop received ([receive.md](receive.md)) | Until then the records keep it tied to Agilify and allow a remote wipe |
| 2 | **BitLocker key check**: at least one key in Entra | The key lives on the Entra device; it is lost when that record is deleted |
| 3 | **Intune wipe** | Erases the laptop |
| 4 | **Delete the Intune record** | Autopilot delete is blocked while an Intune record exists |
| 5 | **Delete the Autopilot record** (only once in hand **and** wiped) | Otherwise the laptop could set itself up again as Agilify's. Skip this step if the laptop will be reused |
| 6 | **Disable, then delete the Entra device, LAST** | Removes the BitLocker key; Autopilot delete is asynchronous (records can linger ~30 minutes), so wait for step 5 to finish |
| 7 | **Record disposal** | Spreadsheet Decommissioning tab: date, method (recycled / sold / destroyed), who |

The Approver's tool for steps 4–6 checks first and refuses steps out of order:
`Remove-DeviceRecords.ps1 -DeviceName AGY-U-<serial> -Serial <serial> -Step Check | DeleteIntune | DeleteAutopilot | DisableEntra | DeleteEntra`

## Read-only checks the Agent runs

- Before each step: `Check-LostLaptop.ps1 -Serial <serial>` → shows what
  still exists in Autopilot, Intune and Entra, and the BitLocker key count.
- After step 6: the same check should find nothing.

## Inventory

The Agent updates the spreadsheet after each step: Decommissioning tab row
(In Autopilot / In Intune / In Entra columns, Next steps), and the Stock or
Intune tabs if the laptop was listed there.

## Special cases

| Case | Do |
|---|---|
| Laptop missing and over ~4 years old | Approver may write it off: same deletes (no wipe possible), reason recorded as “written off” |
| Laptop still checking in but the user left | Recover it first ([receive.md](receive.md)); a remote wipe is possible meanwhile if needed (**CHANGE REQUEST**) |
| Broken laptop that never comes back | Skip the wipe; deletes after disposal is confirmed |
