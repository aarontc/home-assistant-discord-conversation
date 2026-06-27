"""Config and options flow for Discord Conversation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_AGENT_ID,
    CONF_ALLOWLIST,
    CONF_BOT_ID,
    CONF_CHANNELS,
    CONF_FALLBACK_USER,
    CONF_IDLE_MINUTES,
    CONF_LANGUAGE,
    CONF_RESPOND_DMS,
    CONF_RESPOND_MENTIONS,
    CONF_TOKEN,
    CONF_USER_MAP,
    DEFAULT_IDLE_MINUTES,
    DEFAULT_RESPOND_DMS,
    DEFAULT_RESPOND_MENTIONS,
    DOMAIN,
)
from .discord_api import CannotConnect, InvalidAuth, list_text_channels, validate_token

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


def build_config_schema(channel_options: list[SelectOptionDict]) -> vol.Schema:
    """Schema for the main settings form (shared by config + options flows)."""
    return vol.Schema(
        {
            vol.Required(CONF_AGENT_ID): EntitySelector(
                EntitySelectorConfig(filter=EntityFilterSelectorConfig(domain="conversation"))
            ),
            vol.Optional(CONF_CHANNELS, default=[]): SelectSelector(
                SelectSelectorConfig(
                    options=channel_options, multiple=True, mode=SelectSelectorMode.LIST
                )
            ),
            vol.Optional(
                CONF_RESPOND_DMS, default=DEFAULT_RESPOND_DMS
            ): BooleanSelector(),
            vol.Optional(
                CONF_RESPOND_MENTIONS, default=DEFAULT_RESPOND_MENTIONS
            ): BooleanSelector(),
            vol.Optional(
                CONF_IDLE_MINUTES, default=DEFAULT_IDLE_MINUTES
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=240, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Optional(CONF_LANGUAGE, default=""): TextSelector(),
            vol.Optional(CONF_ALLOWLIST, default=[]): SelectSelector(
                SelectSelectorConfig(options=[], multiple=True, custom_value=True)
            ),
        }
    )


class DiscordConversationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Discord Conversation config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._token: str | None = None
        self._bot_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                bot_id = await validate_token(user_input[CONF_TOKEN])
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(bot_id)
                self._abort_if_unique_id_configured()
                self._token = user_input[CONF_TOKEN]
                self._bot_id = bot_id
                return await self.async_step_config()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._token is not None
        if user_input is not None:
            options = dict(user_input)
            options[CONF_LANGUAGE] = options.get(CONF_LANGUAGE) or None
            options.setdefault(CONF_USER_MAP, {})
            options.setdefault(CONF_FALLBACK_USER, None)
            return self.async_create_entry(
                title="Discord Conversation",
                data={CONF_TOKEN: self._token, CONF_BOT_ID: self._bot_id},
                options=options,
            )

        try:
            channels = await list_text_channels(self._token)
        except (InvalidAuth, CannotConnect):
            channels = []
        options = [SelectOptionDict(value=cid, label=label) for cid, label in channels]
        return self.async_show_form(
            step_id="config", data_schema=build_config_schema(options)
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_token(user_input[CONF_TOKEN])
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_TOKEN: user_input[CONF_TOKEN]},
                )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=STEP_USER_SCHEMA, errors=errors
        )
