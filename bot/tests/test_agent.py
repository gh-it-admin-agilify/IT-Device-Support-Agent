"""The full message path with a fake Claude: refusal for strangers, tool loop,
conversation memory and reset."""
from types import SimpleNamespace as NS

from bot.agent import REFUSAL, RESET_REPLY, ItBot
from bot.identity import IdentityResolver
from bot.memory import ConversationStore
from bot.tests.fakes import FakeGraph

ADMINS, SUPPORT = "a-group", "s-group"


class FakeClaude:
    """Odd calls ask for laptop_status, even calls answer in text."""

    def __init__(self):
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot
        if len(self.calls) % 2 == 1:
            return NS(stop_reason="tool_use",
                      content=[NS(type="tool_use", id=f"t{len(self.calls)}", name="laptop_status",
                                  input={"serial": "SERIAL1"})])
        return NS(stop_reason="end_turn", content=[NS(type="text", text="SERIAL1 is compliant.")])


def bot(groups):
    graph = FakeGraph({"transitiveMemberOf": [{"id": g} for g in groups]})
    claude = FakeClaude()
    return ItBot(graph, IdentityResolver(graph, ADMINS, SUPPORT), claude, "claude-sonnet-5-5"), claude


async def test_stranger_refused_and_claude_not_called():
    b, claude = bot(["other"])
    assert await b.handle("user-x", "status of SERIAL1?", "conv-x") == REFUSAL
    assert claude.calls == []


async def test_support_member_gets_answer_via_tool():
    b, claude = bot([SUPPORT])
    assert await b.handle("user-b", "status of SERIAL1?", "conv-b") == "SERIAL1 is compliant."
    first = claude.calls[0]
    assert first["model"] == "claude-sonnet-5-5"
    assert "Current mode\nSUPPORT" in first["system"]
    assert {t["name"] for t in first["tools"]} == {
        "laptop_status", "person_devices", "enrollment_readiness", "not_enrolled", "runbook"}
    tool_result = claude.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "t1"


async def test_second_message_includes_text_history_but_not_tool_data():
    b, claude = bot([SUPPORT])
    await b.handle("user-b", "status of SERIAL1?", "conv-b")
    await b.handle("user-b", "and what next?", "conv-b")
    sent = claude.calls[2]["messages"]  # first Claude call of the 2nd message
    assert sent == [
        {"role": "user", "content": "status of SERIAL1?"},
        {"role": "assistant", "content": "SERIAL1 is compliant."},
        {"role": "user", "content": "and what next?"},
    ]


async def test_conversations_are_separate():
    b, claude = bot([SUPPORT])
    await b.handle("user-b", "status of SERIAL1?", "conv-1")
    await b.handle("user-b", "hello", "conv-2")
    assert claude.calls[2]["messages"] == [{"role": "user", "content": "hello"}]


async def test_reset_clears_memory_without_calling_claude():
    b, claude = bot([SUPPORT])
    await b.handle("user-b", "status of SERIAL1?", "conv-b")
    assert await b.handle("user-b", "reset", "conv-b") == RESET_REPLY
    assert len(claude.calls) == 2
    await b.handle("user-b", "hello", "conv-b")
    assert claude.calls[2]["messages"] == [{"role": "user", "content": "hello"}]


async def test_unknown_tool_is_reported_not_run():
    b, _ = bot([ADMINS])
    assert "error" in await b.run_tool("wipe_device", {"serial": "X"})


async def test_bad_tool_arguments_reported():
    b, _ = bot([ADMINS])
    assert "error" in await b.run_tool("laptop_status", {"wrong": "X"})


def test_memory_limits_and_expiry():
    now = [0.0]
    store = ConversationStore(max_messages=4, ttl_hours=1, clock=lambda: now[0])
    for i in range(3):
        store.add_turn("c", f"q{i}", f"a{i}")
    assert [m["content"] for m in store.history("c")] == ["q1", "a1", "q2", "a2"]  # last 4 only
    now[0] = 3601
    assert store.history("c") == []  # forgotten after 1 hour idle
