# How the tenant is set up for laptops

Last updated: 2026-11-26 (Agent, from the Approver's read-only checks of
2026-11-08 to 2026-11-25, and the IT Desk group / role apply of 2026-11-26). The Agent can read these settings but never
changes them; changes go through a change request.

## Autopilot

| Setting | Value |
|---|---|
| Deployment profile | **Standard**: Entra-joined, user-driven, single user, device name `AGY-U-%SERIAL%`, EULA / privacy / keyboard pages hidden, **pre-provisioning allowed**, “convert all targeted devices” on |
| Assigned to | Dynamic device group **All Autopilot Devices** (every Autopilot-registered laptop joins it automatically) |
| Group tags | Not used |
| Setup screen (ESP) | Default: all devices, 240-minute timeout |
| Assigned user | Optional and cosmetic (pre-fills the sign-in name). **Not reliable** for knowing who actually has a laptop |
| Users' rights | Autopilot users become **local administrators** of their laptop (known finding, unchanged) |

## Intune enrollment

| Setting | Value |
|---|---|
| Automatic enrollment (MDM scope) | Selected groups: **Employees** and **IT**. A user in neither group can sign in but the laptop won't join Intune |
| Device limit | 10 per user |
| Licence | Microsoft 365 Business Premium (SPB). Intune service plans show **PendingInput / PendingActivation** for everyone: normal here, not a fault |
| Clean-up rules | None (Intune doesn't auto-delete stale devices) |

## Security

| Area | Setup |
|---|---|
| **BitLocker** | Policy “Agilify BitLocker Configuration” (silent encryption) assigned to group **Agilify Workstations**, which contains **All Autopilot Devices**, so every Autopilot laptop is covered. Laptops encrypt after the first user sign-in; recovery keys are stored in Entra |
| **Compliance** | “Agilify Basic Compliance” + the default compliance policy. Defender definitions out of date is the most common reason a new laptop is noncompliant (clears after a sync). Compliance does not currently require BitLocker. No sign-in rule blocks noncompliant laptops today |
| **Other policies** | Attack surface reduction, restrictions, browser updates and a security baseline also target Agilify Workstations |
| **LAPS** | Turned on in Entra; Intune policy “Agilify Windows LAPS” applies to the LAPS pilot group (a dynamic group). Pilot complete on 5 laptops (2026-11-19); wider rollout on hold. The managed admin account is hidden from the sign-in screen by an Intune script |
| **Windows updates** | Windows Autopatch groups are in use |

## Apps

| App | Assignment |
|---|---|
| Adobe Reader, Microsoft Edge, Google Chrome | Required → Agilify Workstations (install during pre-provisioning) |
| Microsoft 365 apps (Office) | Required → all licensed users (install at the user's first sign-in; slow) |
| Cisco AnyConnect VPN | Only the VPN group (most users don't need it) |

## Remote help

| Tool | Available? |
|---|---|
| **Quick Assist** (Ctrl + Windows + Q) | **Yes**: free, works even on laptops not in Intune. A UAC admin prompt shows only on the user's screen and pauses the session |
| Intune Remote Help, Remediations, Defender Live Response | **No** (not licensed / not set up) |

## Groups and role for this project (created 2026-11-26)

| Object | Members / scope | Purpose | Managed in (m365-terraform) |
|---|---|---|---|
| `sg-itdesk-admins` (group `fe4e4496-59c8-400f-8220-f6d5dcce16fb`) | Approver | Bot access (approver mode), receives change requests | `environments/prod/entra-groups.tf` (pipeline) |
| `sg-itdesk-support` (group `41825516-a26b-4d3b-af0b-bee626d9a5db`, role-assignable) | IT Support Tech (**empty** until their account exists) | Bot access (support mode), BitLocker key read, inventory read | `privileged/itdesk-support.tf` (applied locally by a Global Admin) |
| Custom Entra role **“BitLocker Key Reader”** (`0907e661-26c2-4d82-89f9-31e997130158`) | Assigned tenant-wide to `sg-itdesk-support` | One permission only: `microsoft.directory/bitlockerKeys/key/read` | `privileged/itdesk-support.tf` |

Why two places: changing a role-assignable group or a role assignment needs
RoleManagement.ReadWrite.Directory, which no pipeline identity has on purpose
(it could grant any admin role). Those changes are applied by a Global Admin
from the admin laptop. Swapping the IT Support Tech = edit `members` in
`privileged/itdesk-support.tf` → pull request → local apply.
