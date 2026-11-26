# Knowledge (the Agent's shared memory)

Facts the Agent needs on every session. Device and tenant-setup facts only:
no HR, disciplinary or incident details, no secrets.

| File | Contents |
|---|---|
| [glossary.md](glossary.md) | Plain-language meaning of the terms used everywhere (start here if new to IT) |
| [fleet.md](fleet.md) | Laptop models, business vs developer classes, specs, buying patterns, naming |
| [tenant-setup.md](tenant-setup.md) | How Intune, Autopilot, BitLocker, compliance, apps and LAPS are set up |
| [troubleshooting.md](troubleshooting.md) | Known problems and proven fixes |
| [decisions.md](decisions.md) | Decisions, each with date and who made it |

## Rules for updating

- **Decisions** go in `decisions.md` with the date and the person's first name
  (e.g. `2026-11-25 Felix: business laptops = 16 GB devices`).
- **Facts** go in the matching file. If a fact changes, update it and add the
  date; don't leave two versions.
- **Per-laptop status** belongs in the inventory spreadsheet and `tasks.md`,
  not here.
- The Agent proposes knowledge changes as a pull request on a `notes/…` branch;
  the Approver merges.
