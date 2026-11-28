# Agilify IT Bot (IT Teams Bot)

Teams assistant for the **IT Support Tech** and the **Approver**. Runs in Azure
(`app-agilify-itbot`, rg-agilify-itdesk, Central US); infrastructure is managed in
the m365-terraform repo (`environments/prod/itdesk-bot.tf`).

## How a message flows
1. Teams → Azure Bot `bot-agilify-it` → `POST /api/messages` (token verified by the SDK).
2. `identity.py`: sender's verified Entra ID → **APPROVER** (sg-itdesk-admins),
   **SUPPORT** (sg-itdesk-support) or **refused**. Checked on every message (cached 10 min).
3. `claude.py`: Claude Sonnet 5.5 in Foundry (US-only DataZoneStandard), signed in with
   the managed identity. Claude can only use the **fixed tools** in `tools/`.
4. `graph.py`: every Graph call passes an **allow-list in code**: GET only, listed
   paths only, BitLocker key values blocked.

## Files
| File | Purpose |
|---|---|
| `app.py` | Web server (aiohttp + Microsoft 365 Agents SDK 1.9). Each message is handled in a **background turn** (SDK `continue_conversation_with_claims`) so Teams never times out; "typing…" every 3 s and one "⏳ Still working" after 12 s |
| `agent.py` | Identity check → Claude → reply; `reset`, `Inventory Refresh`, and the **"yes" confirmation** (next message, within 15 min; anything else cancels) |
| `refresh.py` | `Inventory Refresh`: rebuilds tblIntuneDevices and tblAutopilotNotInIntune from Graph (hand-written columns kept by serial, formula columns keep formulas), removes **in-use** laptops (Intune + primary user + check-in ≤ 30 days) from tblStock, and from tblDecommissioning only when used by **someone other than** the row's "Last user" (re-deployed; still with the last user = kept and shown in the preview), logs to tblChangeLog. Preview first; saved with the version check |
| `identity.py` | Group-based mode |
| `memory.py` | Conversation memory in RAM: last 60 messages per chat, forgotten after 4 h idle (app settings `MEMORY_MAX_MESSAGES`, `MEMORY_TTL_HOURS`); text only, no tool data or images |
| `inventory.py` | Inventory workbook on the Device Support site: find, download, round-trip, upload with version check (eTag). Uploads only into `Device Inventory`, `.xlsx` only; during 5e-0 only `TEST - *` files. Approver command `selftest inventory` proves it on the TEST copy |
| `claude.py` | Foundry client + bounded tool loop |
| `graph.py` | Graph client with allow-list |
| `tools/` | One file per tool: `laptop_status`, `person_devices`, `enrollment_readiness`, `not_enrolled`, `runbook` (shared helpers in `_common.py`) |
| `knowledge/` | Not in git: the repo's `runbooks/` and `knowledge/` are copied here at deploy, so editing a runbook updates the bot on the next deploy |
| `prompt.md` | The bot's instructions |
| `tests/` | Automated tests with fake Graph and Claude (no tenant access) |

## Adding a tool
1. New file in `tools/` with `SPEC` and `async def run(graph, ...)`.
2. Register it in `tools/__init__.py`.
3. If it needs a new Graph path, add it to `_READ_ALLOW` in `graph.py` (and the
   permission in m365-terraform `privileged/itdesk-bot-graph.tf` if not granted).
4. Tests in `tests/`. Pull request → tests run → merge → deployed.

## Deploy
`.github/workflows/deploy-bot.yml`: tests on every pull request; on merge to `main`,
tests then deploy with `sp-agilify-bot-deploy` (GitHub OIDC, no secret) to the
`production` environment. Variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
`AZURE_SUBSCRIPTION_ID`.

## App settings it needs (set by m365-terraform)
`AZURE_CLIENT_ID`, `BOT_TENANT_ID`, `CLAUDE_BASE_URL`, `CLAUDE_DEPLOYMENT`,
`ITDESK_ADMINS_GROUP_ID`, `ITDESK_SUPPORT_GROUP_ID`,
`CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE` = `UserManagedIdentity`,
`CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID`,
`CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID` (no underscore in CLIENTID /
TENANTID: the underscore spelling is silently ignored, proven by `tests/test_app_imports.py`).
