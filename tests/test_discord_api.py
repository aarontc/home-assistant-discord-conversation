"""Tests for discord_api.py REST helpers (discord.py fully mocked)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from custom_components.discord_conversation.discord_api import (
    CannotConnect,
    InvalidAuth,
    list_text_channels,
    validate_token,
)


def _client_mock(**attrs):
    client = MagicMock()
    client.login = AsyncMock()
    client.close = AsyncMock()
    for key, value in attrs.items():
        setattr(client, key, value)
    return client


async def test_validate_token_ok():
    client = _client_mock(user=SimpleNamespace(id=42))
    with patch("discord.Client", return_value=client):
        assert await validate_token("good") == "42"
    client.close.assert_awaited_once()


async def test_validate_token_bad_raises_invalid_auth():
    client = _client_mock()
    client.login = AsyncMock(side_effect=discord.LoginFailure("nope"))
    with patch("discord.Client", return_value=client):
        with pytest.raises(InvalidAuth):
            await validate_token("bad")
    client.close.assert_awaited_once()


async def test_validate_token_http_error_raises_cannot_connect():
    client = _client_mock()
    client.login = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "boom"))
    with patch("discord.Client", return_value=client):
        with pytest.raises(CannotConnect):
            await validate_token("x")


async def test_list_text_channels():
    text_channel = MagicMock(spec=discord.TextChannel)
    text_channel.id = 555
    text_channel.name = "general"
    voice_channel = MagicMock()  # not a TextChannel -> filtered out

    guild = MagicMock()
    guild.name = "Home"
    guild.fetch_channels = AsyncMock(return_value=[text_channel, voice_channel])

    async def _aiter_guilds(*_args, **_kwargs):
        yield guild

    client = _client_mock()
    client.fetch_guilds = _aiter_guilds
    with patch("discord.Client", return_value=client), patch(
        "custom_components.discord_conversation.discord_api.isinstance",
        side_effect=lambda obj, typ: obj is text_channel,
    ):
        channels = await list_text_channels("good")
    assert channels == [("555", "Home / #general")]
