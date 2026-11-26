# IT Device Support Agent

The shared brain of the **Agent** that helps Agilify IT run the laptop fleet:
provisioning, resets, decommissioning, inventory, shipping and receiving.

It holds the Agent's rules, runbooks, shared knowledge and change requests.
The same files are used by:

- **The Agilify IT Bot** in Microsoft Teams (planned), which the IT Support
  Tech chats with, and
- **Claude Code** sessions opened in this repo (today: the Approver's).

> **Status:** proposal / setup. The Teams bot is **not built yet**.
> Design: *Agilify IT Teams Bot Design* (private page, ask the Approver for access).

---

## Who does what

| Role | Group | Does |
|---|---|---|
| **IT Support Tech** | `sg-itdesk-support` | Physical laptop work guided by the Agent; reports what happened so the Agent updates the inventory; reads BitLocker keys through the Entra portal. Uses **Teams only**. |
| **Approver** (today: Felix) | `sg-itdesk-admins` | Reviews every change request; runs every tenant change from his own admin laptop; merges every pull request in this repo. |
| **The Agent** | n/a | Explains, guides one step at a time, runs **read-only** checks, updates the inventory spreadsheet, drafts change requests. **Never changes the tenant.** |

Access comes from the **groups**, never from a named person, so the IT Support
Tech can be replaced with one group-membership change.

---

## The three rules

1. **Read-only towards Microsoft 365.** The Agent and its scripts only read
   Intune, Autopilot and Entra.
2. **Every tenant change is a change request.** The Agent writes it in
   `requests\`, the Approver reviews it, and the Approver runs it himself.
3. **No secrets and no personal details in this repo.** No passwords,
   BitLocker keys, tokens or MFA codes. Device facts only: no HR or incident
   details.

The full rules for the Agent are in [`CLAUDE.md`](CLAUDE.md).

---

## Repo layout

| Path | Contents |
|---|---|
| `CLAUDE.md` | The Agent's rules: roles, support / approver mode, change requests, git |
| `.claude/settings.json` | What the Agent may run or edit without asking (allow / ask / deny) |
| `knowledge/` | Shared memory: fleet facts, models, tenant setup, decisions (dated, with a name) |
| `runbooks/` | Step-by-step procedures: provision, reset, decommission, receive, ship |
| `scripts/readonly/` | The only scripts the Agent runs. Read-only. |
| `requests/` | Change requests for the Approver. Copy [`requests/_TEMPLATE.md`](requests/_TEMPLATE.md). |
| `reports/` | Daily read-only findings (when automated) |
| `tasks.md` | Shared open-task list |

The inventory spreadsheet is **not** in this repo. The one live copy is
`Agilify_Asset_Inventory.xlsx` in Teams: **Agilify IT** (private Team) →
**Device Support** (private channel) → Files → `Device Inventory`
(SharePoint site `AgilifyIT-DeviceSupport`). Its data tabs are Excel Tables
(`tblStock`, `tblDecommissioning`, `tblIntuneDevices`, `tblUnaccounted`,
`tblAutopilotNotInIntune`, `tblHardwareSpecs`, `tblIssues`). Spreadsheets, CSV exports, logs and screenshots are kept out of
git by [`.gitignore`](.gitignore).

---

## Starting a Claude Code session

1. Open a terminal (PowerShell 7) in the repo folder and run `git pull`.
2. Start Claude Code.
3. The Agent runs `.\scripts\readonly\Get-WhoAmI.ps1` first. It signs you in to
   Microsoft Graph if needed (your own Agilify account + MFA) and decides the
   mode from your group membership:

   | Last line | Meaning |
   |---|---|
   | `MODE=APPROVER` | Member of `sg-itdesk-admins` |
   | `MODE=SUPPORT` | Member of `sg-itdesk-support` |
   | `MODE=UNKNOWN` | Neither, wrong tenant, or not signed in: explanations only |

**Needs on the machine:** PowerShell 7, the `Microsoft.Graph.Authentication`
module, Git, GitHub CLI (`gh`), Claude Code.

---

## How a change request works

1. Something needs changing in the tenant (e.g. a returned laptop's records
   need removing).
2. The Agent copies `requests/_TEMPLATE.md` to
   `requests/YYYY-MM-DD-<serial-or-user>-<action>.md`, fills it in with
   read-only evidence, the exact command and how to undo it, and opens a
   **pull request** on a `request/…` branch.
3. The Approver reviews it, runs the change from his admin laptop, and records
   the result in section 9 of the request.
4. The Agent re-checks with a read-only script and updates the inventory.

---

## Changing this repo

- **Nobody pushes to `main`.** Work on a branch (`notes/…` for knowledge and
  runbooks, `request/…` for change requests) and open a pull request.
- **The Approver reviews and merges** every pull request.
- The Agent may create branches, commit, push its branch and open pull
  requests (it asks first). It never merges, never force-pushes and never
  changes repo settings.
- New knowledge: add or edit a file in `knowledge/`, with the date and the
  person's name for any decision.
- New or changed procedure: edit the runbook in `runbooks/` in the same pull
  request.
- New read-only script: add it to `scripts/readonly/` with a header saying
  **READ-ONLY**, what it does, what it needs and where output goes. The
  Approver reviews it before it is used.

---

## Related

- `gh-it-admin-agilify/m365-terraform`: the Approver's repo that manages the
  tenant (groups, permissions, policies). Changes to the bot's groups or
  permissions are made there, through a reviewed Terraform plan.
