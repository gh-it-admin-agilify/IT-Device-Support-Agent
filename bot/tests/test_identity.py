from bot.identity import IdentityResolver, Mode
from bot.tests.fakes import FakeGraph

ADMINS = "aaaaaaaa-0000-0000-0000-000000000001"
SUPPORT = "bbbbbbbb-0000-0000-0000-000000000002"


def resolver(groups):
    return IdentityResolver(FakeGraph({"transitiveMemberOf": [{"id": g} for g in groups]}), ADMINS, SUPPORT)


async def test_admin_is_approver():
    assert await resolver([ADMINS, SUPPORT]).mode_for("user-a") is Mode.APPROVER


async def test_support_member():
    assert await resolver([SUPPORT.upper()]).mode_for("user-b") is Mode.SUPPORT


async def test_other_user_unknown():
    assert await resolver(["cccccccc-0000-0000-0000-000000000003"]).mode_for("user-c") is Mode.UNKNOWN


async def test_missing_id_unknown_without_lookup():
    r = resolver([ADMINS])
    assert await r.mode_for(None) is Mode.UNKNOWN
    assert r._graph.calls == []


async def test_result_cached():
    r = resolver([SUPPORT])
    await r.mode_for("user-b")
    await r.mode_for("USER-B")
    assert len(r._graph.calls) == 1
