# Decisions

Newest first. Format: date, who, decision, and why where it matters.
Only decisions about laptops, inventory and how this project works.

| Date | Who | Decision |
|---|---|---|
| 2026-11-26 | Agilify leadership (reported by Felix) | **IT Teams Bot design approved**: an automated read-only reader of user and device data, a bot that edits the inventory spreadsheet, and an IT Support Tech with BitLocker key read access |
| 2026-11-26 | Agilify leadership | AI model for the bot: **Claude through Microsoft Foundry** in Agilify's Azure subscription (managed identity, no API key, billed on the Azure invoice). Fallback only if unavailable: Anthropic API key in Key Vault |
| 2026-11-26 | Agilify leadership | IT Support Tech's key access: **custom Entra role "BitLocker Key Reader"** (read keys only) on `sg-itdesk-support`; fallback Security Reader if the custom role can't hold that permission |
| 2026-11-26 | Agilify leadership | Inventory **stays in Excel** (main tabs converted to Excel Tables) for now; a SharePoint list only if Excel stops working well |
| 2026-11-26 | Agilify leadership | IT Support Tech sign-in: **MFA now**; add an Agilify-managed-device rule once the tech has an Agilify laptop |
| 2026-11-26 | Agilify leadership | The bot's updates to this repo go through **pull requests** that the Approver merges |
| 2026-11-26 | Felix | The Approver's own Claude Code work on Agilify moves to an **Agilify Claude licence** (not a personal / other-company plan) |
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
