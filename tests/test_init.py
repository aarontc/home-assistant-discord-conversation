from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.discord_conversation.const import (
    CONF_AGENT_ID,
    CONF_BOT_ID,
    CONF_TOKEN,
    DOMAIN,
)


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(
    enable_custom_integrations, setup_core_components
):
    """Load the custom integration so setup/unload run the real entry path."""
    yield


def _entry():
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="botid-1",
        data={CONF_TOKEN: "tok", CONF_BOT_ID: "botid-1"},
        options={CONF_AGENT_ID: "conversation.ollama"},
    )


async def test_setup_and_unload(hass: HomeAssistant):
    entry = _entry()
    entry.add_to_hass(hass)

    fake_client = MagicMock()
    fake_client.start = AsyncMock()
    fake_client.close = AsyncMock()

    with patch(
        "custom_components.discord_conversation.DiscordConversationClient",
        return_value=fake_client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()
        assert entry.runtime_data.client is fake_client
        fake_client.start.assert_awaited()

        assert await hass.config_entries.async_unload(entry.entry_id) is True
        fake_client.close.assert_awaited_once()


async def test_login_failure_triggers_reauth(hass: HomeAssistant):
    import discord

    entry = _entry()
    entry.add_to_hass(hass)
    fake_client = MagicMock()
    fake_client.start = AsyncMock(side_effect=discord.LoginFailure("bad"))
    fake_client.close = AsyncMock()

    with patch(
        "custom_components.discord_conversation.DiscordConversationClient",
        return_value=fake_client,
    ), patch.object(entry, "async_start_reauth") as mock_reauth:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    mock_reauth.assert_called_once()
