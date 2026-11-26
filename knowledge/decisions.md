# Decisions

Newest first. Format: date, who, decision, and why where it matters.
Only decisions about laptops, inventory and how this project works.

| Date | Who | Decision |
|---|---|---|
| 2026-11-26 | Felix | The IT Support Tech works **only in Teams**, through the Agilify IT Bot. The virtual desktop (IT Desk) is optional / later |
| 2026-11-26 | Felix | **The bot updates the inventory spreadsheet**, from its first release. The IT Support Tech does not edit it by hand; the Approver does not apply edits for the bot |
| 2026-11-26 | Felix | The IT Support Tech **may read BitLocker keys** (Entra portal, via the bot's link; never in chat) |
| 2026-11-26 | Felix | **All tenant changes come to the Approver as change requests**; the Approver runs them from his admin laptop |
| 2026-11-26 | Felix | All access is given to **groups** (`sg-itdesk-support`, `sg-itdesk-admins`), never to a named person, so the IT Support Tech can be replaced with one membership change |
| 2026-11-26 | Felix | The shared project is the private GitHub repo `IT-Device-Support-Agent` (same GitHub account as m365-terraform) |
| 2026-11-26 | Felix | Design documents use role titles (“IT Support Tech”) and generic example users, not real names |
| 2026-11-26 | Felix | Old laptops being shipped back: **don't wipe before shipping**. Keep them enrolled (remote wipe stays possible); the user confirms OneDrive is synced, shuts down fully, ships; wipe once in hand. Wipe remotely only if it doesn't arrive in a reasonable time |
| 2026-11-25 | Felix | **Business laptop = a 16 GB device.** 32 GB builds are developer laptops |
| 2026-11-25 | Felix | Laptop 8K1K5H4 is assigned to Felix (not stock); to be re-enrolled in Agilify Intune later |
| 2026-11-25 | Felix | Laptop 5FHB9G4 belongs to Megan Spencer (handover in the office); not available stock |
| 2026-11-24 | Felix | Old laptops returned after a swap are **decommissioned, not reused**, including deleting their Autopilot records |
| 2026-11-24 | Felix | **Delete an Autopilot record only after the laptop is in hand and wiped** (keeps it tied to Agilify meanwhile; Autopilot delete is blocked while an Intune record exists) |
| 2026-11-24 | Felix | Windows activation check dropped for one already-handed-over laptop; revisit only if the user reports “Activate Windows” |
| 2026-11-17 | Felix | For laptops that lost their Intune record: fix in place with the auto-enroll setting (no reset) before considering a reset |
| 2026-11-15 | Felix | Missing laptops over ~4 years old are written off: removed from Autopilot and Entra, recorded on the Decommissioning tab |
| 2026-11-09 | Felix | Autopilot “assign user” is optional (cosmetic) when pre-provisioning |
