"""The full message path with a fake Claude: refusal for strangers, tool loop for members."""
from types import SimpleNamespace as NS

from bot.agent import REFUSAL, ItBot
from bot.identity import IdentityResolver
from bot.tests.fakes import FakeGraph

ADMINS, SUPPORT = "a-group", "s-group"


class FakeClaude:
    """First reply asks for laptop_status, second reply answers in text."""

    def __init__(self):
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return NS(stop_reason="tool_use",
                      content=[NS(type="tool_use", id="t1", name="laptop_status", input={"serial": "SERIAL1"})])
        return NS(stop_reason="end_turn", content=[NS(type="text", text="SERIAL1 is compliant.")])


def bot(groups):
    graph = FakeGraph({"transitiveMemberOf": [{"id": g} for g in groups]})
    claude = FakeClaude()
    return ItBot(graph, IdentityResolver(graph, ADMINS, SUPPORT), claude, "claude-sonnet-5-5"), claude


async def test_stranger_refused_and_claude_not_called():
    b, claude = bot(["other"])
    assert await b.handle("user-x", "status of SERIAL1?") == REFUSAL
    assert claude.calls == []


async def test_support_member_gets_answer_via_tool():
    b, claude = bot([SUPPORT])
    assert await b.handle("user-b", "status of SERIAL1?") == "SERIAL1 is compliant."
    first = claude.calls[0]
    assert first["model"] == "claude-sonnet-5-5"
    assert "Current mode\nSUPPORT" in first["system"]
    assert [t["name"] for t in first["tools"]] == ["laptop_status"]
    tool_result = claude.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "t1"


async def test_unknown_tool_is_reported_not_run():
    b, _ = bot([ADMINS])
    assert "error" in await b.run_tool("wipe_device", {"serial": "X"})
