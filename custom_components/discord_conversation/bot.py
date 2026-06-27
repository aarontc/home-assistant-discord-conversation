"""discord.py gateway client that bridges Discord messages to the conversation agent."""

from __future__ import annotations

import logging

import discord
from homeassistant.core import HomeAssistant

from .conversation_router import ConversationRouter, make_conversation_key
from .text_utils import chunk_message, strip_self_mention

_LOGGER = logging.getLogger(__name__)

ERROR_REPLY = "Sorry, I hit an error talking to Home Assistant."
EMPTY_REPLY = "(no response)"


class DiscordConversationClient(discord.Client):
    """Listens for messages and routes them to the HA conversation agent."""

    def __init__(self, hass: HomeAssistant, router: ConversationRouter) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.hass = hass
        self.router = router

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        was_mentioned = self.user in message.mentions
        if not self.router.should_respond(
            is_dm=is_dm,
            was_mentioned=was_mentioned,
            channel_id=message.channel.id,
            author_id=message.author.id,
        ):
            return

        text = strip_self_mention(message.content, self.user.id)
        if not text:
            return

        key = make_conversation_key(
            is_dm=is_dm, channel_id=message.channel.id, author_id=message.author.id
        )
        reply = ERROR_REPLY
        try:
            reply = await self._answer(message, text, key)
        except Exception:  # noqa: BLE001 - never let the gateway die
            _LOGGER.exception("Conversation processing failed")
        for part in chunk_message(reply or EMPTY_REPLY):
            try:
                await message.channel.send(part)
            except discord.HTTPException:
                _LOGGER.warning(
                    "Failed to send reply to channel %s", message.channel.id
                )
                break

    async def _answer(self, message: discord.Message, text: str, key: str) -> str:
        """Process the message, showing a typing indicator best-effort.

        A typing-indicator failure must not block the actual reply (spec §11),
        so fall back to answering without it.
        """
        try:
            async with message.channel.typing():
                return await self.router.process(
                    text=text, discord_user_id=message.author.id, conversation_key=key
                )
        except discord.HTTPException:
            return await self.router.process(
                text=text, discord_user_id=message.author.id, conversation_key=key
            )
