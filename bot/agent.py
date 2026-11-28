"""One Teams message -> identity check -> (photos) -> Claude with the fixed tools -> reply."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from . import images as img
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
DOWNLOAD_FAILED = (
    "I couldn't download the image you sent. Please try pasting it again, or describe what's on the screen."
)

# Called only AFTER the sender passed the identity check, so strangers' files are never downloaded.
FetchFiles = Callable[[], Awaitable[list[bytes]]]


class ItBot:
    def __init__(self, graph: GraphClient, identity: IdentityResolver, claude_client: Any, deployment: str,
                 max_steps: int = 8, max_tokens: int = 1500, memory: ConversationStore | None = None,
                 inventory: Any = None):
        self.graph = graph
        self.inventory = inventory
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

    async def handle(self, aad_object_id: str | None, text: str, conversation_id: str | None = None,
                     has_attachments: bool = False, fetch_files: FetchFiles | None = None) -> str:
        mode = await self.identity.mode_for(aad_object_id)
        log.info("message from mode=%s attachments=%s", mode.value, has_attachments)
        if mode is Mode.UNKNOWN:
            return REFUSAL
        text = (text or "").strip()
        conv = conversation_id or f"user:{aad_object_id}"
        if text.lower() in RESET_WORDS and not has_attachments:
            self.memory.reset(conv)
            return RESET_REPLY
        if text.lower() == "selftest inventory":
            if mode is not Mode.APPROVER or self.inventory is None:
                return "The inventory self-test is for approvers only."
            from .inventory import selftest
            try:
                return await selftest(self.inventory)
            except Exception as exc:
                log.exception("inventory selftest failed")
                return f"❌ Inventory self-test stopped: {type(exc).__name__}: {str(exc)[:300]}"

        pictures: list[img.Image] = []
        notes: list[str] = []
        if has_attachments and fetch_files is not None:
            try:
                files = await fetch_files()
            except Exception:
                log.exception("attachment download failed")
                files = []
            if not files:
                return DOWNLOAD_FAILED
            pictures, notes = img.accept(files)
            log.info("images accepted=%d skipped=%d", len(pictures), len(notes))

        if not text and not pictures:
            return " ".join(notes) or "Hi! Ask me about a laptop, e.g. \"What's the status of CQ38514?\""

        user_content: str | list[dict] = img.content_blocks(pictures, text) if pictures else text
        reply = await ask(
            self.claude, self.deployment, mode.value, user_content, tools.specs(), self.run_tool,
            max_steps=self.max_steps, max_tokens=self.max_tokens, history=self.memory.history(conv),
        )
        # Memory keeps text only: a short note stands in for the photo.
        remembered = (f"[sent {len(pictures)} photo(s) of the screen] " if pictures else "") + text
        self.memory.add_turn(conv, remembered.strip(), reply)

        prefix = [img.receipt(pictures)] if pictures else []
        return "\n\n".join(prefix + notes + [reply])
