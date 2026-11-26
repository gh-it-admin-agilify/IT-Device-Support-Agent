# Shared open tasks: laptop fleet

How this list works:
- One line per task. Device facts only: no HR, disciplinary or incident details
  ("user has left" is enough).
- **Owner** is a role: *Approver* or *IT Support Tech* (or *User* when we're
  waiting on the laptop's user).
- When something changes, update the line with the date and who reported it.
  Move finished tasks to **Done** with the date; don't delete them.
- Tenant changes in a task (wipe, delete, assign) always go through a change
  request in `requests\`. The task line links to it.
- "Inv #n" = issue number on the *Issues & Actions* tab of the inventory
  spreadsheet.

Last reviewed: 2026-11-26 (Approver)

---

## 1. Setting up this project

| # | Task | Next step | Owner | Status |
|---|---|---|---|---|
| S1 | Leadership approval for the IT Teams Bot design | Share the private design page with Agilify leadership | Approver | Open |
| S2 | Commit the starter files and protect `main` | n/a | Approver | **Done 2026-11-26**: commit 03f3c7c (24 files); `main` requires a PR, 0 approvals, no bypass for admins, no force push / delete |
| S3 | Test the permission rules | Open Claude Code in this repo, run `/permissions`, check every rule is accepted | Approver | Open |
| S4 | Test the copied read-only scripts once (Check-LostLaptop, Check-EnrollmentReadiness, Check-NewLaptops on a known laptop; Get-BitLockerKey in your own window) | Run each once; confirm logs.txt lands in this repo | Approver | Open (scripts copied 2026-11-26; syntax-checked only) |
| S5 | Create groups `sg-itdesk-support` (role-assignable) and `sg-itdesk-admins` | Terraform PR in m365-terraform | Approver | After S1 |
| S6 | Move the inventory spreadsheet to the Agilify IT Team; convert main tabs to Excel Tables; IT Support Tech read-only | Upload the latest version; retire the local copy | Approver | After S1 |
| S7 | Build the Teams bot, Release 1 | See design page, section 13 | Approver | After S1 |

## 2. Laptops being provisioned

| # | Laptop | User | Next step | Owner | Status |
|---|---|---|---|---|---|
| P1 | AGY-U-CQ38514 (Inspiron 15 3530) | Jennifer Irons | Shipped after pre-provisioning (green, resealed 2026-11-25). After she signs in: check primary user, compliant, encrypted, **new** BitLocker key, Windows activated (Inspiron key risk). Inv #19 | User, then Approver | Waiting for first sign-in |
| P2 | AGY-U-5FHB9G4 (Dell Pro 16, 16 GB) | Megan Spencer | Handover in the office, week of 30 Nov. Stale since 2026-03-06, not encrypted, old Windows build: reset (or sync + Windows Update) at handover, then check compliant + encrypted + primary user. Inv #18 | Approver | Planned |
| P3 | AGY-U-1JB9514 (Inspiron 15 3530) | none (stock) | Reset using the forced-recovery reset runbook (Shift+Restart and SupportAssist don't work on it). Entra still lists the previous user (left): move labels after setup. Inv #20 | Approver | Open |
| P4 | 8K1K5H4 (Dell Pro 16) | Felix (assigned) | Currently enrolled in another tenant; re-enroll in Agilify Intune later. Inv #17 | Approver | Later |

## 3. Waiting on someone

| # | Laptop | User | Waiting for | Then | Owner | Since |
|---|---|---|---|---|---|---|
| W1 | AGY-U-FPN8514 (Inspiron 15 3530) | Jacob Cloward | Reply to the Quick Assist request | In the session: winver → auto-enroll fix (Intune) + restart → activation check. Laptop is in use but **not managed by Intune** and may be unpatched (highest priority on this list) | Approver | 2026-11-24 |
| W2 | 6M37QL3 (Vostro 7620) | Jonathan Jenkins | His screenshots (computer name, serial, join status) | Decide: auto-enroll fix, or reset + Autopilot. Never set up through Autopilot | Approver | 2026-11-20 |
| W3 | AGY-U-Y926243V9 (Surface) | Nhi Nguyen | Sync + Defender update on her laptop (asked 2026-11-20) | Re-check last sync and compliance | Approver | 2026-11-20 |

## 4. Coming back / decommissioning

Rule: keep all records until the laptop is **in hand**. Order: BitLocker key
check → Intune wipe → delete Intune → delete Autopilot (only once in hand +
wiped) → delete Entra **last** → record disposal. Each delete = change request.

| # | Laptop | Last user | Status | Next step | Owner |
|---|---|---|---|---|---|
| D1 | AGY-U-3R37QL3 (Vostro 7620) | Sara Yates | Being shipped back (she has her new laptop) | Receive → decommission | IT Support Tech, then Approver |
| D2 | AGY-U-FS37QL3 (Vostro 7620) | Adrienne Streater | Being shipped back after her holiday | Receive → decommission | IT Support Tech, then Approver |
| D3 | AGY-U-DRZ8DL3 (Vostro 15 7510) | user left | Reset started 2026-11-15 | Power off at setup screen → delete Autopilot → delete Entra last → record disposal | Approver |
| D4 | 9SZ8DL3 (Vostro 15 7510), 7V8QJZ2 (Inspiron 5570) | users left | Broken | Delete from Autopilot + Entra after wipe / disposal | Approver |

## 5. Laptops not physically accounted for

| # | Laptop | Last user | What we know | Next step | Owner |
|---|---|---|---|---|---|
| U1 | AGY-U-1HQRLB4 (Dell Pro 16) | user left | Still checking in (last 2026-10-21) | Recover → wipe → reassign or decommission | Approver |
| U2 | AGY-U-6FHB9G4 (Dell Pro 16) | user left | Still checking in (last 2026-11-18) | Recover → wipe → reassign or decommission | Approver |
| U3 | BS37QL3 (Vostro 7620) | user left | Entra sign-in 2026-09-23: someone has it | Contact former manager; recover | Approver |
| U4 | 8X37QL3 (Vostro 7620) | none | Set up before; location unknown | Find; reset or decommission | IT Support Tech |
| U5 | 91DN6G4, B1DN6G4 (Dell Pro 16, 32 GB) | none | Shipped 2025-12-13, never set up | Check boxed stock / Dell order | IT Support Tech |

## 6. Health follow-ups

| # | Item | Laptops | Next step | Owner |
|---|---|---|---|---|
| H1 | No Intune check-in for 90+ days | AGY-U-2TSY8G3, 4ZP1BK4, 6XSY8G3, 9FHB9G4, C2JN6G4, HGQRLB4 | Ask each user whether they still use it; retire old ones | Approver |
| H2 | LAPS wave 4 check | AGY-U-96V8514 (Brad McDonald) | Check LAPS password backed up + admin tile hidden | Approver |
| H3 | Autopilot user doesn't match the real user (cosmetic) | AGY-U-8S37QL3; AGY-U-9N38514 and 2P38514 (blank) | Fix Autopilot user via change request | Approver |
| H4 | Windows activation on Inspiron 15 3530s (generic key risk) | FPN8514 (W1), CQ38514 (P1) | Check at next session; fix with the firmware key if "Not active" | Approver |

---

## Done (recent)

| Date | Task |
|---|---|
| 2026-11-25 | AGY-U-CQ38514 pre-provisioned for Jennifer Irons (green, resealed); reset runbook written |
| 2026-11-25 | Inventory spreadsheet refreshed from Intune (Stock, Decommissioning, Intune tabs; issues #17–#20) |
| 2026-11-24 | AGY-U-2P38514 handed over to Sara Yates (compliant, encrypted, new BitLocker key) |
| 2026-11-24 | AGY-U-9N38514 in use by Adrienne Streater (Windows activated with the firmware key) |
| 2026-11-17 | AGY-U-7K1K5H4 re-enrolled in Intune (auto-enroll fix, no reset) |
