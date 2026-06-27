"""Decision logic + HA conversation-agent dispatch for the Discord bot."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.conversation import async_converse
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant

from .const import (
    CONF_AGENT_ID,
    CONF_ALLOWLIST,
    CONF_CHANNELS,
    CONF_FALLBACK_USER,
    CONF_IDLE_MINUTES,
    CONF_LANGUAGE,
    CONF_RESPOND_DMS,
    CONF_RESPOND_MENTIONS,
    CONF_USER_MAP,
    DEFAULT_IDLE_MINUTES,
    DEFAULT_RESPOND_DMS,
    DEFAULT_RESPOND_MENTIONS,
)
from .conversation_cache import ConversationCache

_LOGGER = logging.getLogger(__name__)


def _coerce_int_set(values, field):
    """Coerce an iterable to a set of ints, logging and skipping non-numeric values."""
    result = set()
    for value in values:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            _LOGGER.warning("Ignoring non-numeric %s value: %r", field, value)
    return result


def make_conversation_key(*, is_dm: bool, channel_id: int, author_id: int) -> str:
    """One conversation per DM (by user) or per channel."""
    return f"dm:{author_id}" if is_dm else f"channel:{channel_id}"


def resolve_ha_user_id(
    user_map: dict[int, str], fallback_user: str | None, discord_user_id: int
) -> str | None:
    """Mapped HA user, else fallback HA user, else None (unrestricted Context)."""
    return user_map.get(discord_user_id) or fallback_user


@dataclass
class ConversationRouter:
    """Filters Discord messages and dispatches them to an HA conversation agent."""

    hass: HomeAssistant
    agent_id: str | None
    language: str | None
    channels: set[int]
    respond_dms: bool
    respond_mentions: bool
    allowlist: set[int]
    user_map: dict[int, str]
    fallback_user: str | None
    cache: ConversationCache

    def should_respond(
        self, *, is_dm: bool, was_mentioned: bool, channel_id: int, author_id: int
    ) -> bool:
        if self.allowlist and author_id not in self.allowlist:
            return False
        if is_dm:
            return self.respond_dms
        if channel_id in self.channels:
            return True
        if was_mentioned:
            return self.respond_mentions
        return False

    async def process(
        self, *, text: str, discord_user_id: int, conversation_key: str
    ) -> str:
        ha_user_id = resolve_ha_user_id(
            self.user_map, self.fallback_user, discord_user_id
        )
        context = Context(user_id=ha_user_id) if ha_user_id else Context()
        conversation_id = self.cache.get(conversation_key)
        result = await async_converse(
            self.hass,
            text,
            conversation_id,
            context,
            language=self.language,
            agent_id=self.agent_id,
        )
        self.cache.set(conversation_key, result.conversation_id)
        speech = result.response.speech or {}
        return (speech.get("plain") or {}).get("speech") or ""

    @classmethod
    def from_entry(
        cls, hass: HomeAssistant, entry: ConfigEntry
    ) -> ConversationRouter:
        opts = entry.options
        user_map: dict[int, str] = {}
        for key, value in opts.get(CONF_USER_MAP, {}).items():
            try:
                user_map[int(key)] = value
            except (TypeError, ValueError):
                _LOGGER.warning(
                    "Ignoring non-numeric Discord user id in mapping: %r", key
                )
        return cls(
            hass=hass,
            agent_id=opts.get(CONF_AGENT_ID),
            language=opts.get(CONF_LANGUAGE) or None,
            channels=_coerce_int_set(opts.get(CONF_CHANNELS, []), "channel"),
            respond_dms=opts.get(CONF_RESPOND_DMS, DEFAULT_RESPOND_DMS),
            respond_mentions=opts.get(CONF_RESPOND_MENTIONS, DEFAULT_RESPOND_MENTIONS),
            allowlist=_coerce_int_set(opts.get(CONF_ALLOWLIST, []), "allowlist id"),
            user_map=user_map,
            fallback_user=opts.get(CONF_FALLBACK_USER) or None,
            cache=ConversationCache(
                timedelta(minutes=opts.get(CONF_IDLE_MINUTES, DEFAULT_IDLE_MINUTES))
            ),
        )
