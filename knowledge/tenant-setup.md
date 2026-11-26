# How the tenant is set up for laptops

Last updated: 2026-11-26 (Agent, from the Approver's read-only checks of
2026-11-08 to 2026-11-25). The Agent can read these settings but never
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

## Groups for this project (planned)

| Group | Members | Purpose |
|---|---|---|
| `sg-itdesk-support` (role-assignable) | IT Support Tech | Bot access (support mode), BitLocker key read, inventory read |
| `sg-itdesk-admins` | Approver | Bot access (approver mode), receives change requests |

Both to be created through the Approver's Terraform repo (tasks.md S5).
