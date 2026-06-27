"""The Discord Conversation integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import discord
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .bot import DiscordConversationClient
from .const import CONF_TOKEN, DOMAIN
from .conversation_router import ConversationRouter

_LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimeData:
    """Per-entry runtime objects."""

    client: DiscordConversationClient
    router: ConversationRouter


type DiscordConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: DiscordConfigEntry) -> bool:
    """Set up Discord Conversation from a config entry."""
    router = ConversationRouter.from_entry(hass, entry)
    client = DiscordConversationClient(hass, router)
    entry.runtime_data = RuntimeData(client=client, router=router)

    async def _run() -> None:
        try:
            await client.start(entry.data[CONF_TOKEN])
        except discord.LoginFailure:
            _LOGGER.warning("Discord token rejected; starting reauth")
            entry.async_start_reauth(hass)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Discord gateway task failed")

    entry.async_create_background_task(
        hass, _run(), name=f"{DOMAIN}-gateway-{entry.entry_id}"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DiscordConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.client.close()
    return True
