"""Constants for the Discord Conversation integration."""

DOMAIN = "discord_conversation"

# Entry data (secret / identity)
CONF_TOKEN = "token"
CONF_BOT_ID = "bot_id"

# Entry options (editable)
CONF_AGENT_ID = "agent_id"
CONF_CHANNELS = "channels"
CONF_RESPOND_DMS = "respond_dms"
CONF_RESPOND_MENTIONS = "respond_mentions"
CONF_IDLE_MINUTES = "idle_minutes"
CONF_LANGUAGE = "language"
CONF_ALLOWLIST = "allowlist"
CONF_USER_MAP = "user_map"
CONF_FALLBACK_USER = "fallback_ha_user"

DEFAULT_RESPOND_DMS = True
DEFAULT_RESPOND_MENTIONS = True
DEFAULT_IDLE_MINUTES = 15
