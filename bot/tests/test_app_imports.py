"""Checks that every Microsoft 365 Agents SDK name app.py relies on exists in the
installed version, so a wrong name fails in the pull request, not on the live app.
Nothing here signs in or calls Azure."""
import inspect


def test_app_module_loads():
    import bot.app

    assert inspect.iscoroutinefunction(bot.app.create_app)  # aiohttp Gunicorn worker needs an async factory


def test_sdk_names_used_by_app_exist():
    from microsoft_agents.activity import load_configuration_from_env  # noqa: F401
    from microsoft_agents.authentication.msal import MsalConnectionManager
    from microsoft_agents.hosting.aiohttp import CloudAdapter, jwt_authorization_middleware, start_agent_process  # noqa: F401
    from microsoft_agents.hosting.core import AgentApplication, MemoryStorage, TurnContext, TurnState  # noqa: F401

    assert hasattr(MsalConnectionManager, "get_default_connection_configuration")
    assert hasattr(AgentApplication, "activity")
    assert "connection_manager" in inspect.signature(AgentApplication.__init__).parameters


def test_sender_id_field_names():
    from microsoft_agents.activity import Activity, ChannelAccount

    assert "aad_object_id" in ChannelAccount.model_fields
    assert "from_property" in Activity.model_fields


def test_managed_identity_auth_type_value():
    from microsoft_agents.hosting.core import AuthTypes

    assert AuthTypes.user_managed_identity.value == "UserManagedIdentity"


def test_sdk_reads_managed_identity_settings_from_env():
    from microsoft_agents.activity import load_configuration_from_env
    from microsoft_agents.authentication.msal import MsalConnectionManager

    env = {
        "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE": "UserManagedIdentity",
        "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENT_ID": "11111111-2222-3333-4444-555555555555",
        "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANT_ID": "66666666-7777-8888-9999-000000000000",
    }
    manager = MsalConnectionManager(**load_configuration_from_env(env))
    cfg = manager.get_default_connection_configuration()
    # Attribute names differ between SDK versions (e.g. AUTH_TYPE vs auth_type), so check the values.
    values = {k: str(v) for k, v in vars(cfg).items()}
    seen = " ".join(values.values())
    assert "UserManagedIdentity" in seen or "user_managed_identity" in seen, values
    assert "11111111-2222-3333-4444-555555555555" in values.values(), values
    assert "66666666-7777-8888-9999-000000000000" in values.values(), values
