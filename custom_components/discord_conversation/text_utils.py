"""Pure text helpers for Discord message formatting."""

from __future__ import annotations

import re

MAX_MESSAGE_LENGTH = 2000


def chunk_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into <=limit pieces, preferring line boundaries."""
    chunks: list[str] = []
    buffer = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(buffer) + len(line) > limit:
            chunks.append(buffer)
            buffer = line
        else:
            buffer += line
    if buffer:
        chunks.append(buffer)
    return chunks or [""]


def strip_self_mention(content: str, bot_user_id: int) -> str:
    """Remove the bot's own mention (<@id> or <@!id>) from raw message content."""
    return re.sub(rf"<@!?{bot_user_id}>", "", content).strip()
