"""One Teams message -> identity check -> Claude with the fixed tools -> reply."""
from __future__ import annotations

import logging
from typing import Any

from . import tools
from .claude import ask
from .graph import GraphClient, GraphRefused
from .identity import IdentityResolver, Mode
from .memory import ConversationStore

log = logging.getLogger("itbot")

REFUSAL = (
    "Sorry, I can only help members of Agilify's IT support team. "
    "If you think this is a mistake, please contact IT."
)
RESET_WORDS = {"reset", "/reset", "start over", "new chat"}
RESET_REPLY = "OK, I've cleared this conversation. What would you like to do?"


class ItBot:
    def __init__(self, graph: GraphClient, identity: IdentityResolver, claude_client: Any, deployment: str,
                 max_steps: int = 8, max_tokens: int = 1500, memory: ConversationStore | None = None):
        self.graph = graph
        self.identity = identity
        self.claude = claude_client
        self.deployment = deployment
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.memory = memory or ConversationStore()

    async def run_tool(self, name: str, args: dict) -> dict:
        module = tools.TOOLS.get(name)
        if module is None:
            return {"error": f"unknown tool {name}"}
        try:
            result = await module.run(self.graph, **args)
            log.info("tool %s ok", name)
            return result
        except GraphRefused as exc:
            log.warning("tool %s refused by allow-list: %s", name, exc)
            return {"error": "That lookup isn't allowed for the bot."}
        except TypeError as exc:
            return {"error": f"bad arguments for {name}: {exc}"}

    async def handle(self, aad_object_id: str | None, text: str, conversation_id: str | None = None) -> str:
        mode = await self.identity.mode_for(aad_object_id)
        log.info("message from mode=%s", mode.value)
        if mode is Mode.UNKNOWN:
            return REFUSAL
        text = (text or "").strip()
        conv = conversation_id or f"user:{aad_object_id}"
        if text.lower() in RESET_WORDS:
            self.memory.reset(conv)
            return RESET_REPLY
        if not text:
            return "Hi! Ask me about a laptop, e.g. \"What's the status of CQ38514?\""
        reply = await ask(
            self.claude, self.deployment, mode.value, text, tools.specs(), self.run_tool,
            max_steps=self.max_steps, max_tokens=self.max_tokens, history=self.memory.history(conv),
        )
        self.memory.add_turn(conv, text, reply)
        return reply
