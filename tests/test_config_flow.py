from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.discord_conversation.const import (
    CONF_AGENT_ID,
    CONF_CHANNELS,
    CONF_TOKEN,
    DOMAIN,
)

_CHANNELS = [("555", "Home / #general")]


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(
    enable_custom_integrations, setup_core_components
):
    """Load the custom integration so its config flow is discoverable."""
    yield


async def test_full_user_flow(hass: HomeAssistant):
    with patch(
        "custom_components.discord_conversation.config_flow.validate_token",
        new=AsyncMock(return_value="botid-1"),
    ), patch(
        "custom_components.discord_conversation.config_flow.list_text_channels",
        new=AsyncMock(return_value=_CHANNELS),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TOKEN: "good-token"}
        )
        assert result["step_id"] == "config"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AGENT_ID: "conversation.ollama", CONF_CHANNELS: ["555"]},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TOKEN] == "good-token"
    assert result["options"][CONF_CHANNELS] == ["555"]


async def test_invalid_token_shows_error(hass: HomeAssistant):
    from custom_components.discord_conversation.discord_api import InvalidAuth

    with patch(
        "custom_components.discord_conversation.config_flow.validate_token",
        new=AsyncMock(side_effect=InvalidAuth),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TOKEN: "bad"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_single_entry_per_bot(hass: HomeAssistant):
    MockConfigEntry(domain=DOMAIN, unique_id="botid-1").add_to_hass(hass)
    with patch(
        "custom_components.discord_conversation.config_flow.validate_token",
        new=AsyncMock(return_value="botid-1"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TOKEN: "good"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_token(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="botid-1",
        data={CONF_TOKEN: "old", "bot_id": "botid-1"},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.discord_conversation.config_flow.validate_token",
        new=AsyncMock(return_value="botid-1"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data=entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TOKEN: "new"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "new"
