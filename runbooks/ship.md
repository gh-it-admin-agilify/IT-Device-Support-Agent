# Ship a laptop to a user

For a laptop that has been pre-provisioned and resealed
([provision.md](provision.md) Part E), or a returned laptop being sent on.

> **To be completed by the Approver:** carrier and account, insurance value,
> packaging supplies, who pays, and whether a signature is required.
> Until then the Agent asks the Approver for these details on each shipment.

## Before packing

| # | Check | Done when |
|---|---|---|
| 1 | Laptop resealed and **powered off** (not asleep) | Screen black, no lights |
| 2 | Intune has it | provision.md Part F shows it enrolled today |
| 3 | Charger and cable | In the box with the laptop |
| 4 | Serial noted | Service tag on the label underneath matches the inventory row |

## Pack and send

| # | Step |
|---|---|
| 5 | Pack laptop + charger securely (padding, no loose parts) |
| 6 | Address: the user's shipping address from the Approver (never guess or copy from old records) |
| 7 | Create the label and send; keep the tracking number |

## Tell the user

Send (Teams or email) the message below, filling in the tracking number:

> **Your new Agilify laptop is on its way** (tracking: <number>)
> 1. Plug in the charger and connect to your Wi-Fi.
> 2. Sign in with your **@agilifyus.com** account and password, then approve the MFA prompt.
> 3. You'll see “Setting up your account”. **Don't restart or close the lid.** Microsoft 365 apps install now; it can take up to an hour.
> 4. When you reach the desktop, open OneDrive and sign in if asked.
> 5. Let IT know once you're in.

## Records

The Agent updates the inventory spreadsheet:

- Stock tab: Status → "Shipped to <user> (<date>, tracking <number>)".
- tasks.md: the provisioning task → "Waiting for first sign-in".

Then, after the user signs in: provision.md Part H.
