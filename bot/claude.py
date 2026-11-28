"""Claude Sonnet 5.5 in Microsoft Foundry (US-only DataZoneStandard deployment),
signed in with the bot's managed identity. No API key exists (key access is off
on the Foundry account)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

FOUNDRY_SCOPE = "https://ai.azure.com/.default"
PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")

ToolRunner = Callable[[str, dict], Awaitable[dict]]


def make_client(base_url: str, managed_identity_client_id: str):
    """Create the AnthropicFoundry client. Imported lazily so tests don't need Azure."""
    from anthropic import AnthropicFoundry
    from azure.identity import ManagedIdentityCredential, get_bearer_token_provider

    credential = ManagedIdentityCredential(client_id=managed_identity_client_id)
    token_provider = get_bearer_token_provider(credential, FOUNDRY_SCOPE)
    return AnthropicFoundry(azure_ad_token_provider=token_provider, base_url=base_url)


async def ask(
    client: Any,
    deployment: str,
    mode: str,
    user_text: str,
    tool_specs: list[dict],
    run_tool: ToolRunner,
    max_steps: int = 6,
    max_tokens: int = 1500,
) -> str:
    """One user message -> answer, letting Claude call the fixed tools (bounded)."""
    system = f"{PROMPT}\n\n## Current mode\n{mode}"
    messages: list[dict] = [{"role": "user", "content": user_text}]

    for _ in range(max_steps):
        resp = await asyncio.to_thread(
            client.messages.create,
            model=deployment,
            max_tokens=max_tokens,
            system=system,
            tools=tool_specs,
            messages=messages,
        )
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip() or "(no answer)"

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if getattr(block, "type", "") != "tool_use":
                continue
            try:
                result = await run_tool(block.name, dict(block.input or {}))
            except Exception as exc:  # report, don't crash the conversation
                result = {"error": f"{type(exc).__name__}: {exc}"}
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)[:20000]}
            )
        messages.append({"role": "user", "content": results})

    return "I couldn't finish that within my step limit. Please ask again more specifically."
