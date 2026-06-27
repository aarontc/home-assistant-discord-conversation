from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.discord_conversation.const import (
    CONF_AGENT_ID,
    CONF_BOT_ID,
    CONF_CHANNELS,
    CONF_FALLBACK_USER,
    CONF_TOKEN,
    CONF_USER_MAP,
    DOMAIN,
)


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(
    enable_custom_integrations, setup_core_components
):
    """Load the custom integration so its options flow is discoverable."""
    yield


def _entry(hass, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="botid-1",
        data={CONF_TOKEN: "tok", CONF_BOT_ID: "botid-1"},
        options=options or {CONF_AGENT_ID: "conversation.ollama", CONF_USER_MAP: {}},
    )
    entry.add_to_hass(hass)
    return entry


async def test_options_menu_shown(hass: HomeAssistant):
    entry = _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {
        "settings", "add_user_map", "remove_user_map"
    }


async def test_options_settings_updates(hass: HomeAssistant):
    entry = _entry(hass)
    with patch(
        "custom_components.discord_conversation.config_flow.list_text_channels",
        new=AsyncMock(return_value=[("555", "Home / #general")]),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "settings"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_AGENT_ID: "conversation.ollama", CONF_CHANNELS: ["555"]},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_CHANNELS] == ["555"]


async def test_add_user_mapping(hass: HomeAssistant):
    entry = _entry(hass)
    fake_user = SimpleNamespace(
        id="ha-user-1", name="Alice", is_active=True, system_generated=False
    )
    with patch.object(
        hass.auth, "async_get_users", AsyncMock(return_value=[fake_user])
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_user_map"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"discord_user_id": "7", CONF_FALLBACK_USER: "ha-user-1"},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_USER_MAP] == {"7": "ha-user-1"}


async def test_add_user_mapping_rejects_non_numeric_discord_id(hass: HomeAssistant):
    entry = _entry(hass)
    fake_user = SimpleNamespace(
        id="ha-user-1", name="Alice", is_active=True, system_generated=False
    )
    with patch.object(
        hass.auth, "async_get_users", AsyncMock(return_value=[fake_user])
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_user_map"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"discord_user_id": "not-a-number", CONF_FALLBACK_USER: "ha-user-1"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_user_id"}
    # No mapping was created
    assert entry.options.get(CONF_USER_MAP, {}) == {}


async def test_remove_user_mapping(hass: HomeAssistant):
    entry = _entry(
        hass,
        options={
            CONF_AGENT_ID: "conversation.ollama",
            CONF_USER_MAP: {"7": "ha-user-1", "8": "ha-user-2"},
        },
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_user_map"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"discord_user_id": "7"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_USER_MAP] == {"8": "ha-user-2"}
