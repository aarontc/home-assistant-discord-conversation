"""REST-only discord.py helpers used by the config flow (no gateway connection)."""

from __future__ import annotations

import discord
from homeassistant.exceptions import HomeAssistantError


class InvalidAuth(HomeAssistantError):
    """The bot token was rejected."""


class CannotConnect(HomeAssistantError):
    """Could not reach Discord."""


async def validate_token(token: str) -> str:
    """Validate a bot token via REST login only; return the bot's user id."""
    client = discord.Client(intents=discord.Intents.none())
    try:
        await client.login(token)
        if client.user is None:
            raise CannotConnect("login returned no user")
        return str(client.user.id)
    except discord.LoginFailure as err:
        raise InvalidAuth from err
    except discord.HTTPException as err:
        raise CannotConnect from err
    finally:
        await client.close()


async def list_text_channels(token: str) -> list[tuple[str, str]]:
    """Return [(channel_id, 'Guild / #channel')] for all text channels (REST only)."""
    client = discord.Client(intents=discord.Intents.none())
    channels: list[tuple[str, str]] = []
    try:
        await client.login(token)
        async for guild in client.fetch_guilds(limit=200):
            for channel in await guild.fetch_channels():
                if isinstance(channel, discord.TextChannel):
                    label = f"{guild.name} / #{channel.name}"
                    channels.append((str(channel.id), label))
    except discord.LoginFailure as err:
        raise InvalidAuth from err
    except discord.HTTPException as err:
        raise CannotConnect from err
    finally:
        await client.close()
    return channels
