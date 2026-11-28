"""Settings from App Service app settings (set by m365-terraform). No secrets here:
the bot signs in with its user-assigned managed identity."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _req(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing app setting {name}")
    return value


@dataclass(frozen=True)
class Settings:
    managed_identity_client_id: str
    tenant_id: str
    claude_base_url: str
    claude_deployment: str
    admins_group_id: str
    support_group_id: str
    max_tool_steps: int = 6
    max_output_tokens: int = 1500

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            managed_identity_client_id=_req("AZURE_CLIENT_ID"),
            tenant_id=_req("BOT_TENANT_ID"),
            claude_base_url=_req("CLAUDE_BASE_URL"),
            claude_deployment=_req("CLAUDE_DEPLOYMENT"),
            admins_group_id=_req("ITDESK_ADMINS_GROUP_ID"),
            support_group_id=_req("ITDESK_SUPPORT_GROUP_ID"),
        )
