"""One Teams message -> identity check -> (photos) -> Claude with the fixed tools -> reply."""
from __future__ import annotations

import asyncio
import logging
import time
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

REFRESH_WORDS = {"inventory refresh", "refresh inventory", "/inventory refresh"}
YES_WORDS = {"yes", "y", "yes."}
PENDING_TTL = 15 * 60  # a proposal must be confirmed within 15 minutes, by the very next message

# Called only AFTER the sender passed the identity check, so strangers' files are never downloaded.
FetchFiles = Callable[[], Awaitable[list[bytes]]]
Notify = Callable[[str], Awaitable[None]]


async def _no_notify(_: str) -> None:
    return None


class ItBot:
    def __init__(self, graph: GraphClient, identity: IdentityResolver, claude_client: Any, deployment: str,
                 max_steps: int = 8, max_tokens: int = 1500, memory: ConversationStore | None = None,
                 inventory: Any = None, lists: Any = None):
        self.graph = graph
        self.inventory = inventory
        self.lists = lists
        self.identity = identity
        self.claude = claude_client
        self.deployment = deployment
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.memory = memory or ConversationStore()
        self.pending: dict[str, dict] = {}  # conversation -> proposal waiting for "yes"

    # ---------------------------------------------------------------- Inventory Refresh

    async def _refresh_preview(self, conv: str, notify: Notify) -> str:
        from . import refresh
        from .inventory import TARGET_FILE

        await notify("⏳ Inventory Refresh, step 1 of 3: finding and downloading the inventory workbook…")
        item = await self.inventory.find(TARGET_FILE)
        if not item:
            return f"❌ I couldn't find '{TARGET_FILE}' in the Device Inventory folder."
        data = await self.inventory.download(item["id"])
        await notify("⏳ Step 2 of 3: reading Intune, Autopilot, Entra devices and users…")
        src = await refresh.gather(self.graph)
        await notify("⏳ Step 3 of 3: comparing with the workbook…")
        try:
            plan = await asyncio.to_thread(refresh.plan_refresh, data, src)
        except refresh.RefreshBlocked as exc:
            return f"❌ Inventory Refresh can't run safely: {exc}. Nothing was changed."
        self.pending[conv] = {"kind": "refresh", "item_id": item["id"], "plan": plan, "at": time.monotonic()}
        return (refresh.preview(plan) + f"\n\nFile: **{TARGET_FILE}**. ⚠️ **Close the workbook in Excel first** "
                "(on every PC): Excel's AutoSave can save its own copy over mine. Then type **yes** to save these "
                "changes (within 15 minutes). Anything else cancels.")

    async def _refresh_apply(self, pend: dict, who: str, notify: Notify) -> str:
        from . import refresh

        await notify("⏳ Saving: downloading the latest copy, applying the changes, uploading with the version check…")
        status = 0
        for attempt in range(1, 5):
            meta = await self.inventory.item(pend["item_id"])
            data = await self.inventory.download(pend["item_id"])
            try:
                new, summary = await asyncio.to_thread(refresh.apply_plan, data, pend["plan"], who)
            except refresh.RefreshBlocked as exc:
                return f"❌ Inventory Refresh stopped: {exc}. Nothing was changed."
            status, body = await self.inventory.replace(pend["item_id"], new, meta.get("eTag", ""))
            if status in (200, 201):
                return summary
            if status == 412:  # someone saved the file in the meantime: start again from their version
                await notify("⏳ Someone changed the file while I was working; re-reading their version…")
                continue
            if status == 423:  # open/locked
                await notify(f"⏳ The workbook is locked, probably open in Excel. Please close it; "
                             f"retrying in 15 seconds ({attempt}/4)…")
                await asyncio.sleep(15)
                continue
            return f"❌ Save failed: HTTP {status} {body.get('error', {}).get('code', '')}. Nothing was changed."
        if status == 423:
            return ("❌ The workbook is still locked (open in Excel). **Close it in Excel on every PC**, then type "
                    "**Inventory Refresh** again. Nothing was changed.")
        return "❌ I couldn't save after 4 tries (the file kept changing). Nothing was changed; try again later."

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
                     has_attachments: bool = False, fetch_files: FetchFiles | None = None,
                     who: str = "", notify: Notify | None = None) -> str:
        notify = notify or _no_notify
        mode = await self.identity.mode_for(aad_object_id)
        log.info("message from mode=%s attachments=%s", mode.value, has_attachments)
        if mode is Mode.UNKNOWN:
            return REFUSAL
        text = (text or "").strip()
        conv = conversation_id or f"user:{aad_object_id}"
        who = who or str(aad_object_id)

        # A proposal is confirmed only by "yes" as the very next message; anything else cancels it.
        pend = self.pending.pop(conv, None)
        if pend and time.monotonic() - pend["at"] > PENDING_TTL:
            pend = None
            if text.lower() in YES_WORDS:
                return "That proposal expired (15 minutes). Please ask again."
        if pend and text.lower() in YES_WORDS and not has_attachments:
            try:
                if pend["kind"] == "refresh":
                    return await self._refresh_apply(pend, who, notify)
            except Exception as exc:
                log.exception("applying %s failed", pend["kind"])
                return f"❌ Saving stopped: {type(exc).__name__}: {str(exc)[:300]}. Nothing was changed."
        if not pend and text.lower() in YES_WORDS and not has_attachments:
            return ("There's nothing waiting for a **yes** right now. The preview may have expired (15 minutes) or "
                    "the bot restarted (for example after an update). Please run the command again, e.g. "
                    "**Inventory Refresh**.")
        cancelled = "_(The pending change was cancelled.)_\n\n" if pend else ""

        if text.lower() in RESET_WORDS and not has_attachments:
            self.memory.reset(conv)
            return cancelled + RESET_REPLY
        if text.lower() in REFRESH_WORDS:
            if self.inventory is None:
                return "Inventory Refresh isn't available."
            try:
                return cancelled + await self._refresh_preview(conv, notify)
            except Exception as exc:
                log.exception("inventory refresh preview failed")
                return f"❌ Inventory Refresh stopped: {type(exc).__name__}: {str(exc)[:300]}. Nothing was changed."
        if text.lower() == "selftest lists":
            if mode is not Mode.APPROVER or self.lists is None:
                return "The list self-test is for approvers only."
            from .lists import selftest as list_selftest
            try:
                return cancelled + await list_selftest(self.lists)
            except Exception as exc:
                log.exception("list selftest failed")
                return f"❌ List self-test stopped: {type(exc).__name__}: {str(exc)[:300]}"
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
        return cancelled + "\n\n".join(prefix + notes + [reply])
