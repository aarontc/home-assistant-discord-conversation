"""Per-conversation-key cache of HA conversation_id with idle TTL eviction."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util


class ConversationCache:
    """Maps a conversation key to (conversation_id, last_used); evicts on idle TTL."""

    def __init__(
        self,
        ttl: timedelta,
        now: Callable[[], datetime] = dt_util.utcnow,
    ) -> None:
        self._ttl = ttl
        self._now = now
        self._store: dict[str, tuple[str, datetime]] = {}

    def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        conversation_id, last_used = item
        if self._now() - last_used > self._ttl:
            del self._store[key]
            return None
        return conversation_id

    def set(self, key: str, conversation_id: str | None) -> None:
        if conversation_id is None:
            self._store.pop(key, None)
            return
        self._store[key] = (conversation_id, self._now())
