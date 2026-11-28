"""Short-term conversation memory, in the web app's memory only.

- Keeps the last N messages (default 60) per Teams conversation.
- Only the conversation TEXT is kept (what the person wrote and the bot's
  final answers), never raw Graph results or images.
- A conversation is forgotten after T hours without messages (default 4).
- Nothing is written to disk; a restart or deploy clears everything.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class _Conversation:
    messages: deque
    last_seen: float = field(default_factory=time.monotonic)


class ConversationStore:
    def __init__(self, max_messages: int = 60, ttl_hours: float = 4.0, clock=time.monotonic):
        self.max_messages = max(2, int(max_messages))
        self.ttl = float(ttl_hours) * 3600
        self._clock = clock
        self._convs: dict[str, _Conversation] = {}

    def _expire(self) -> None:
        now = self._clock()
        for key in [k for k, c in self._convs.items() if now - c.last_seen > self.ttl]:
            del self._convs[key]

    def history(self, conversation_id: str) -> list[dict]:
        self._expire()
        conv = self._convs.get(conversation_id)
        return list(conv.messages) if conv else []

    def add_turn(self, conversation_id: str, user_text: str, bot_text: str) -> None:
        self._expire()
        conv = self._convs.get(conversation_id)
        if conv is None:
            conv = self._convs[conversation_id] = _Conversation(deque(maxlen=self.max_messages))
        conv.messages.append({"role": "user", "content": user_text})
        conv.messages.append({"role": "assistant", "content": bot_text})
        conv.last_seen = self._clock()

    def reset(self, conversation_id: str) -> None:
        self._convs.pop(conversation_id, None)
