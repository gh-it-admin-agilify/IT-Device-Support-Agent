"""Photos / screenshots sent to the bot in Teams.

The image bytes are downloaded by the Agents SDK (M365AttachmentDownloader,
signed in with the bot's managed identity), checked here, sent to Claude for
this one message, and then dropped: never stored, never logged.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

MAX_IMAGES = 3
MAX_BYTES = 5 * 1024 * 1024  # 5 MB per image (Claude's limit is higher; keeps cost/latency down)


@dataclass
class Image:
    data: bytes
    media_type: str


def detect_media_type(data: bytes) -> str | None:
    """Identify the real image type from the file's first bytes (don't trust labels)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def accept(files: list[bytes]) -> tuple[list[Image], list[str]]:
    """Keep up to MAX_IMAGES valid images; return them plus notes for the person."""
    images: list[Image] = []
    notes: list[str] = []
    for data in files:
        mt = detect_media_type(data or b"")
        if mt is None:
            notes.append("I can only read photos and screenshots (PNG, JPEG, GIF or WebP); I skipped one attachment.")
        elif len(data) > MAX_BYTES:
            notes.append(f"One image is {len(data) // 1024 // 1024} MB; the limit is 5 MB, so I skipped it.")
        elif len(images) >= MAX_IMAGES:
            notes.append(f"I can look at {MAX_IMAGES} images per message; I skipped the rest.")
        else:
            images.append(Image(data, mt))
    return images, notes


def receipt(images: list[Image]) -> str:
    sizes = ", ".join(f"{max(1, len(i.data) // 1024)} KB" for i in images)
    return f"\U0001F4F7 Got your image{'s' if len(images) > 1 else ''} ({sizes})."


def content_blocks(images: list[Image], text: str) -> list[dict]:
    blocks: list[dict] = [
        {"type": "image", "source": {"type": "base64", "media_type": i.media_type,
                                     "data": base64.b64encode(i.data).decode("ascii")}}
        for i in images
    ]
    blocks.append({"type": "text", "text": text or "Here is a photo of the screen. What is it, and what should I do next?"})
    return blocks
