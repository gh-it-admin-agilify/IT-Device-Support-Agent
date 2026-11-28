"""Web server for the Agilify IT Bot (Microsoft 365 Agents SDK 1.9, aiohttp).

Started on App Service (startup command set by m365-terraform):
  gunicorn --bind 0.0.0.0:8000 --worker-class aiohttp.GunicornWebWorker --timeout 120 bot.app:create_app
(aiohttp's Gunicorn worker accepts an async function that returns the Application.)

Sign-in to the Bot Service uses the user-assigned managed identity. App settings:
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE = UserManagedIdentity
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENT_ID = <managed identity client ID>
  CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANT_ID = <tenant ID>
Incoming requests are verified by the SDK's jwt_authorization_middleware (only
the Bot Service, with a valid token for this bot, can post messages).
"""
from __future__ import annotations

import logging
import os

from aiohttp.web import Application, Request, Response

log = logging.getLogger("itbot")


async def create_app() -> Application:
    from azure.identity import ManagedIdentityCredential
    from microsoft_agents.activity import load_configuration_from_env
    from microsoft_agents.authentication.msal import MsalConnectionManager
    from microsoft_agents.hosting.aiohttp import CloudAdapter, jwt_authorization_middleware, start_agent_process
    from microsoft_agents.hosting.core import AgentApplication, MemoryStorage, TurnContext, TurnState

    from .agent import ItBot
    from .claude import make_client
    from .config import Settings
    from .graph import GraphClient
    from .identity import IdentityResolver

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    settings = Settings.from_env()

    sdk_config = load_configuration_from_env(os.environ)
    connection_manager = MsalConnectionManager(**sdk_config)
    adapter = CloudAdapter(connection_manager=connection_manager)
    agent_app = AgentApplication[TurnState](
        storage=MemoryStorage(), adapter=adapter, connection_manager=connection_manager, **sdk_config
    )

    graph = GraphClient(ManagedIdentityCredential(client_id=settings.managed_identity_client_id))
    bot = ItBot(
        graph=graph,
        identity=IdentityResolver(graph, settings.admins_group_id, settings.support_group_id),
        claude_client=make_client(settings.claude_base_url, settings.managed_identity_client_id),
        deployment=settings.claude_deployment,
        max_steps=settings.max_tool_steps,
        max_tokens=settings.max_output_tokens,
    )

    @agent_app.activity("message")
    async def on_message(context: TurnContext, state: TurnState):
        # Sender identity verified by Teams / Bot Service: activity.from_property.aad_object_id
        sender = getattr(context.activity, "from_property", None)
        aad_id = getattr(sender, "aad_object_id", None)
        try:
            reply = await bot.handle(aad_id, context.activity.text or "")
        except Exception:
            log.exception("message handling failed")
            reply = "Sorry, something went wrong on my side. Please try again in a minute."
        await context.send_activity(reply)

    async def messages(req: Request) -> Response:
        return await start_agent_process(req, req.app["agent_app"], req.app["adapter"])

    app = Application(middlewares=[jwt_authorization_middleware])
    app.router.add_post("/api/messages", messages)
    app["agent_configuration"] = connection_manager.get_default_connection_configuration()
    app["agent_app"] = agent_app
    app["adapter"] = adapter
    return app
