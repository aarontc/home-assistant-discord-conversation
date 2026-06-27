from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from custom_components.discord_conversation.bot import DiscordConversationClient


def _message(content, *, author_bot=False, is_dm=False, mentions=None, channel_id=111):
    dm_spec = discord.DMChannel
    text_spec = discord.TextChannel
    channel = MagicMock(spec=dm_spec) if is_dm else MagicMock(spec=text_spec)
    channel.id = channel_id
    channel.send = AsyncMock()
    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock()
    typing_cm.__aexit__ = AsyncMock()
    channel.typing = MagicMock(return_value=typing_cm)
    return SimpleNamespace(
        content=content,
        channel=channel,
        author=SimpleNamespace(id=7, bot=author_bot),
        mentions=mentions or [],
    )


def _client(router, monkeypatch):
    with patch("discord.Client.__init__", return_value=None):
        client = DiscordConversationClient(hass=object(), router=router)
    # discord.Client.user is normally read-only; stub it for tests
    monkeypatch.setattr(
        type(client), "user", property(lambda self: SimpleNamespace(id=999))
    )
    return client


async def test_on_message_dispatches_and_replies(monkeypatch):
    router = MagicMock()
    router.should_respond.return_value = True
    router.process = AsyncMock(return_value="The light is on.")
    client = _client(router, monkeypatch)
    msg = _message("<@999> is the light on?", mentions=[SimpleNamespace(id=999)])
    await client.on_message(msg)
    router.process.assert_awaited_once()
    msg.channel.send.assert_awaited_once_with("The light is on.")


async def test_on_message_ignores_other_bots(monkeypatch):
    router = MagicMock()
    client = _client(router, monkeypatch)
    msg = _message("hi", author_bot=True)
    await client.on_message(msg)
    router.should_respond.assert_not_called()


async def test_on_message_skips_when_should_respond_false(monkeypatch):
    router = MagicMock()
    router.should_respond.return_value = False
    router.process = AsyncMock()
    client = _client(router, monkeypatch)
    await client.on_message(_message("random channel chatter"))
    router.process.assert_not_called()


async def test_on_message_posts_apology_on_error(monkeypatch):
    router = MagicMock()
    router.should_respond.return_value = True
    router.process = AsyncMock(side_effect=RuntimeError("boom"))
    client = _client(router, monkeypatch)
    msg = _message("<@999> hi", mentions=[SimpleNamespace(id=999)])
    await client.on_message(msg)
    sent = msg.channel.send.await_args.args[0]
    assert "error" in sent.lower()
