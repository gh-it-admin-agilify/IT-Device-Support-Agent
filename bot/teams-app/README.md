# Teams app package: Agilify IT Bot

| File | Purpose |
|---|---|
| `manifest.json` | Teams manifest v1.30. Personal (1:1) chat only. `botId` = the Azure Bot's Microsoft App ID = the bot's managed identity client ID (`id-agilify-itbot`, see m365-terraform `itdesk-bot.tf` `microsoft_app_id`). |
| `color.png` | 192 × 192 full-colour icon |
| `outline.png` | 32 × 32 white outline on a transparent background |

The manifest `id` (`5d7e2b1c-…`) is the Teams app's own ID: **keep it the same** in
every update, or Teams treats it as a different app.

## Build the zip (PowerShell, from the repo root)
```powershell
Compress-Archive bot\teams-app\manifest.json, bot\teams-app\color.png, bot\teams-app\outline.png -DestinationPath $env:TEMP\AgilifyITBot.zip -Force
```
The three files must be at the **top level** of the zip (no folder).

## Upload / update (Approver, Teams admin center)
1. Teams apps → **Manage apps** → **Upload new app** → choose the zip.
   (Update later: open the app → **Upload file** with a higher `version`.)
2. Open the app → **Users and groups** → **Edit availability** → **Specific users or groups**
   → `sg-itdesk-admins` (pilot), later also `sg-itdesk-support` (S9).
3. Availability can take a few hours (up to 24 h) to reach Teams.

The bot itself also refuses anyone outside the two groups, so availability is a
second layer, not the only one.

## Changes that need a new version
Increase `version` (e.g. 1.0.0 → 1.1.0) when changing the manifest, e.g. when
photo upload (`supportsFiles`) is added in step 5d.
