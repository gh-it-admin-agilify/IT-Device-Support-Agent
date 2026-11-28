"""Photos: type detection, limits, and the message path with a fake Claude."""
from types import SimpleNamespace as NS

from bot import images as img
from bot.agent import DOWNLOAD_FAILED, REFUSAL, ItBot
from bot.identity import IdentityResolver
from bot.tests.fakes import FakeGraph

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "
PDF = b"%PDF-1.7 ..."


def test_detect_media_type():
    assert img.detect_media_type(PNG) == "image/png"
    assert img.detect_media_type(JPG) == "image/jpeg"
    assert img.detect_media_type(b"GIF89a....") == "image/gif"
    assert img.detect_media_type(WEBP) == "image/webp"
    assert img.detect_media_type(PDF) is None


def test_accept_limits():
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (img.MAX_BYTES + 1)
    pics, notes = img.accept([PNG, PDF, big, JPG, PNG, PNG])
    assert [p.media_type for p in pics] == ["image/png", "image/jpeg", "image/png"]
    assert len(notes) == 3  # PDF skipped, too big, 4th image over the limit


def test_content_blocks_default_question():
    blocks = img.content_blocks([img.Image(PNG, "image/png")], "")
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["media_type"] == "image/png"
    assert blocks[-1]["type"] == "text" and "photo" in blocks[-1]["text"]


class FakeClaude:
    def __init__(self):
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return NS(stop_reason="end_turn", content=[NS(type="text", text="That's the BitLocker recovery screen.")])


def bot(groups):
    graph = FakeGraph({"transitiveMemberOf": [{"id": g} for g in groups]})
    claude = FakeClaude()
    return ItBot(graph, IdentityResolver(graph, "a", "s"), claude, "dep"), claude


async def test_photo_goes_to_claude_and_memory_keeps_only_a_note():
    b, claude = bot(["s"])

    async def fetch():
        return [PNG]

    reply = await b.handle("u", "", "c1", has_attachments=True, fetch_files=fetch)
    assert reply.startswith("\U0001F4F7 Got your image (2 KB).")
    assert "BitLocker recovery screen" in reply
    sent = claude.calls[0]["messages"][-1]["content"]
    assert sent[0]["type"] == "image"
    history = b.memory.history("c1")
    assert history[0]["content"].startswith("[sent 1 photo(s) of the screen]")
    assert "base64" not in str(history)


async def test_stranger_photo_never_downloaded():
    b, claude = bot(["other"])
    called = []

    async def fetch():
        called.append(1)
        return [PNG]

    assert await b.handle("u", "", "c1", has_attachments=True, fetch_files=fetch) == REFUSAL
    assert called == [] and claude.calls == []


async def test_download_failure_reported():
    b, claude = bot(["s"])

    async def fetch():
        raise RuntimeError("401")

    assert await b.handle("u", "what is this?", "c1", has_attachments=True, fetch_files=fetch) == DOWNLOAD_FAILED
    assert claude.calls == []


async def test_non_image_only_gets_note():
    b, claude = bot(["s"])

    async def fetch():
        return [PDF]

    reply = await b.handle("u", "", "c1", has_attachments=True, fetch_files=fetch)
    assert "PNG, JPEG, GIF or WebP" in reply and claude.calls == []
