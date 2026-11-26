# Glossary

Plain-language meanings, for anyone new to IT. The Agent uses these
explanations when a term comes up for the first time.

| Term | What it means |
|---|---|
| **Tenant** | Agilify's whole Microsoft 365 setup (accounts, email, Teams, devices). Domain: agilifyus.com. “Live production tenant” = the real one people use every day |
| **Entra ID** (formerly Azure AD) | Microsoft's list of Agilify's people, groups and devices. Every laptop has an Entra “device” record |
| **Intune** | Microsoft's tool that manages laptops remotely: settings, security rules, apps, updates, remote wipe. A laptop “in Intune” is managed; one that isn't is effectively unprotected |
| **Windows Autopilot** | Sets up a new or reset laptop automatically the first time it connects. Dell registers laptops in Agilify's Autopilot when they're bought |
| **Pre-provisioning** | IT runs most of the Autopilot setup before shipping (Windows key ×5 on the setup screen), so the user's first sign-in is quicker |
| **Reseal** | The button at the end of pre-provisioning. Shuts the laptop down, ready for the user |
| **Primary user** | The person Intune links to a laptop: the first person who signs in. That's why IT never signs in on a laptop meant for someone else |
| **Compliant / noncompliant** | Whether a laptop meets Agilify's security rules (antivirus up to date, firewall on, recent Windows, etc.) |
| **BitLocker** | Encrypts the laptop's drive so nobody can read it if it's lost or stolen |
| **BitLocker recovery key** | A 48-digit number that unlocks an encrypted drive when the laptop asks for it. Stored in Entra. Treat it like a password: never write it down, paste it or send it |
| **Key ID** | The first characters shown on the BitLocker screen, used to find the right key. Safe to share |
| **TPM** | A security chip in the laptop that holds encryption and sign-in keys. Clearing it during a reset removes the old user's keys |
| **Service tag / serial** | Dell's ID for the laptop, on a label underneath (e.g. 7 characters). Agilify device names are `AGY-U-<serial>` |
| **UPN** | A person's sign-in name, e.g. `first.last@agilifyus.com` |
| **MFA** | Multi-factor authentication: password + a second check (phone app or security key) |
| **Group** | A list of people or devices in Entra. Access and settings are given to groups, not individuals |
| **Licence** | What Microsoft charges per user. Agilify uses Microsoft 365 Business Premium (shown as **SPB**), which includes Intune |
| **ESP** (“Setting up your account”) | The screen during first sign-in while apps and settings install. Microsoft 365 apps can take up to an hour: don't restart |
| **Wipe** | Intune remote command that erases a laptop back to a fresh Windows |
| **Decommission** | Retire a laptop for good: wipe it, remove its records, record disposal |
| **LAPS** | Rotates a unique password for the laptop's built-in admin account and stores it in Entra, so IT can sign in for repairs without a shared password |
| **Quick Assist** | Built-in Windows tool (Ctrl + Windows + Q) that lets IT see and control a user's screen with their permission |
| **Change request** | A written request (in `requests\`) for the Approver to make a change in the tenant. The Agent never makes tenant changes itself |
| **Read-only** | Can look, can't change |
