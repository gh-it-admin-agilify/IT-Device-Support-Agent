"""Web server for the Agilify IT Bot (Microsoft 365 Agents SDK 1.9, aiohttp).

Started on App Service (startup command set by m365-terraform):
  gunicorn --bind 0.0.0.0:8000 --worker-class aiohttp.GunicornWebWorker --timeout 120 bot.app:create_app
(aiohttp's Gunicorn worker accepts an async function that returns the Application.)

Sign-in to the Bot Service uses the user-assigned managed identity. App settings:
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE = UserManagedIdentity
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID = <managed identity client ID>
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID = <tenant ID>
  (exact spelling: CLIENT_ID / TENANT_ID are ignored; see tests/test_app_imports.py)
Incoming requests are verified by the SDK's jwt_authorization_middleware (only
the Bot Service, with a valid token for this bot, can post messages).
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque

from aiohttp.web import Application, Request, Response

log = logging.getLogger("itbot")

TYPING_EVERY_S = 3      # "Agilify IT Bot is typing…" refreshed every 3 seconds while working
STILL_WORKING_S = 12    # one "still working" message if a reply takes longer than this


async def keep_typing(send, done: asyncio.Event, every: float = TYPING_EVERY_S,
                      still_after: float = STILL_WORKING_S, still_text: str = "⏳ Still working on it…") -> None:
    """Send a typing indicator every few seconds until `done` is set; once, after `still_after`
    seconds, also send a short 'still working' message."""
    start, told = time.monotonic(), False
    while not done.is_set():
        try:
            await send(None)  # typing
            if not told and time.monotonic() - start >= still_after:
                told = True
                await send(still_text)
        except Exception:  # an indicator must never break the real work
            log.debug("typing indicator failed", exc_info=True)
        try:
            await asyncio.wait_for(done.wait(), timeout=every)
        except asyncio.TimeoutError:
            pass


def _log_failure(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception() is not None:
        log.error("background turn failed: %r", task.exception())


async def create_app() -> Application:
    from azure.identity import ManagedIdentityCredential
    from microsoft_agents.activity import Activity, ActivityTypes, load_configuration_from_env
    from microsoft_agents.authentication.msal import MsalConnectionManager
    from microsoft_agents.hosting.aiohttp import CloudAdapter, jwt_authorization_middleware, start_agent_process
    from microsoft_agents.hosting.core import AgentApplication, MemoryStorage, TurnContext, TurnState
    from microsoft_agents.hosting.core.app.m365_attachment_downloader import M365AttachmentDownloader

    from .agent import ItBot
    from .claude import make_client
    from .config import Settings
    from .graph import GraphClient
    from .identity import IdentityResolver
    from .inventory import InventoryStore
    from .memory import ConversationStore

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    settings = Settings.from_env()

    sdk_config = load_configuration_from_env(os.environ)
    connection_manager = MsalConnectionManager(**sdk_config)
    adapter = CloudAdapter(connection_manager=connection_manager)
    agent_app = AgentApplication[TurnState](
        storage=MemoryStorage(), adapter=adapter, connection_manager=connection_manager,
        start_typing_timer=False,  # we run our own 3-second typing loop in the background turn
        **sdk_config
    )

    downloader = M365AttachmentDownloader(connections=connection_manager)
    graph = GraphClient(ManagedIdentityCredential(client_id=settings.managed_identity_client_id))
    bot = ItBot(
        graph=graph,
        identity=IdentityResolver(graph, settings.admins_group_id, settings.support_group_id),
        claude_client=make_client(settings.claude_base_url, settings.managed_identity_client_id),
        deployment=settings.claude_deployment,
        max_steps=settings.max_tool_steps,
        max_tokens=settings.max_output_tokens,
        memory=ConversationStore(settings.memory_max_messages, settings.memory_ttl_hours),
        inventory=InventoryStore(graph),
    )

    recent_ids: deque = deque(maxlen=500)   # ignore a message Teams delivers twice
    background: set = set()                 # keep references so running tasks aren't garbage-collected

    async def process(ctx: TurnContext) -> None:
        """Handle one message: typing indicator every 3 s, progress notes, then the reply."""
        act = ctx.activity
        sender = getattr(act, "from_property", None)
        aad_id = getattr(sender, "aad_object_id", None)
        conv_id = getattr(getattr(act, "conversation", None), "id", None)
        # Teams adds a text/html copy of most messages; only other attachments are real files/images.
        real = [a for a in (act.attachments or [])
                if not str(getattr(a, "content_type", "") or "").startswith("text/html")]

        async def fetch_files() -> list[bytes]:
            # Downloads with the bot's own identity (managed identity); called only after the identity check.
            files = await downloader.download_files(ctx)
            return [f.content for f in files if f and f.content]

        async def send(text: str | None) -> None:
            await ctx.send_activity(text if text is not None else Activity(type=ActivityTypes.typing))

        done = asyncio.Event()
        typing = asyncio.create_task(keep_typing(send, done))
        try:
            reply = await bot.handle(aad_id, act.text or "", conv_id, has_attachments=bool(real),
                                     fetch_files=fetch_files, who=getattr(sender, "name", "") or "",
                                     notify=lambda t: send(t))
        except Exception:
            log.exception("message handling failed")
            reply = "Sorry, something went wrong on my side. Please try again in a minute."
        finally:
            done.set()
            await typing
        await ctx.send_activity(reply)

    @agent_app.activity("message")
    async def on_message(context: TurnContext, state: TurnState):
        act = context.activity
        if act.id and act.id in recent_ids:
            log.info("duplicate delivery ignored")
            return
        recent_ids.append(act.id)
        # Long work (Claude with several lookups, Inventory Refresh) can exceed the 10-15 s the
        # Bot Service waits for an answer. So: answer Teams now and do the work in a background
        # turn, using the same SDK call as its own long_running_messages option.
        identity = getattr(context, "identity", None)
        if identity is not None and hasattr(context.adapter, "continue_conversation_with_claims"):
            task = asyncio.create_task(context.adapter.continue_conversation_with_claims(
                claims_identity=identity, continuation_activity=act, callback=process))
            background.add(task)
            task.add_done_callback(background.discard)
            task.add_done_callback(_log_failure)
        else:
            await process(context)  # fallback: handle in the request itself

    async def messages(req: Request) -> Response:
        return await start_agent_process(req, req.app["agent_app"], req.app["adapter"])

    app = Application(middlewares=[jwt_authorization_middleware])
    app.router.add_post("/api/messages", messages)
    app["agent_configuration"] = connection_manager.get_default_connection_configuration()
    app["agent_app"] = agent_app
    app["adapter"] = adapter
    return app
