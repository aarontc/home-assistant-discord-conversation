from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.discord_conversation.conversation_cache import ConversationCache
from custom_components.discord_conversation.conversation_router import (
    ConversationRouter,
    make_conversation_key,
    resolve_ha_user_id,
)


def _router(**overrides):
    defaults = dict(
        hass=object(),
        agent_id="conversation.ollama",
        language=None,
        channels={111},
        respond_dms=True,
        respond_mentions=True,
        allowlist=set(),
        user_map={},
        fallback_user=None,
        cache=ConversationCache(timedelta(minutes=15)),
    )
    defaults.update(overrides)
    return ConversationRouter(**defaults)


def test_make_conversation_key_dm_vs_channel():
    assert make_conversation_key(is_dm=True, channel_id=5, author_id=9) == "dm:9"
    assert make_conversation_key(is_dm=False, channel_id=5, author_id=9) == "channel:5"


@pytest.mark.parametrize(
    ("user_map", "fallback", "discord_id", "expected"),
    [
        ({7: "ha-a"}, "ha-fb", 7, "ha-a"),
        ({7: "ha-a"}, "ha-fb", 8, "ha-fb"),
        ({}, None, 8, None),
    ],
)
def test_resolve_ha_user_id(user_map, fallback, discord_id, expected):
    assert resolve_ha_user_id(user_map, fallback, discord_id) == expected


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (dict(is_dm=True, was_mentioned=False, channel_id=0, author_id=1), True),
        (dict(is_dm=False, was_mentioned=False, channel_id=111, author_id=1), True),
        (dict(is_dm=False, was_mentioned=True, channel_id=222, author_id=1), True),
        (dict(is_dm=False, was_mentioned=False, channel_id=222, author_id=1), False),
    ],
)
def test_should_respond_scope(kwargs, expected):
    assert _router().should_respond(**kwargs) is expected


def test_should_respond_dms_disabled():
    router = _router(respond_dms=False)
    result = router.should_respond(
        is_dm=True, was_mentioned=False, channel_id=0, author_id=1
    )
    assert result is False


def test_should_respond_allowlist_blocks_unlisted():
    router = _router(allowlist={42})
    unlisted = router.should_respond(
        is_dm=True, was_mentioned=False, channel_id=0, author_id=1
    )
    listed = router.should_respond(
        is_dm=True, was_mentioned=False, channel_id=0, author_id=42
    )
    assert unlisted is False
    assert listed is True


async def test_process_calls_async_converse_and_caches():
    router = _router(user_map={7: "ha-a"})
    fake_result = SimpleNamespace(
        response=SimpleNamespace(speech={"plain": {"speech": "Hi there"}}),
        conversation_id="conv-1",
    )
    with patch(
        "custom_components.discord_conversation.conversation_router.async_converse",
        new=AsyncMock(return_value=fake_result),
    ) as mock_converse:
        reply = await router.process(
            text="hello", discord_user_id=7, conversation_key="channel:111"
        )
    assert reply == "Hi there"
    # conversation_id was cached for the next turn
    assert router.cache.get("channel:111") == "conv-1"
    # mapped user identity passed via Context(user_id=...)
    _, kwargs = mock_converse.call_args
    assert kwargs["agent_id"] == "conversation.ollama"
    ctx = mock_converse.call_args.args[3]
    assert ctx.user_id == "ha-a"


async def test_process_handles_missing_speech():
    router = _router()
    fake_result = SimpleNamespace(
        response=SimpleNamespace(speech={}), conversation_id="conv-2"
    )
    with patch(
        "custom_components.discord_conversation.conversation_router.async_converse",
        new=AsyncMock(return_value=fake_result),
    ):
        reply = await router.process(
            text="hi", discord_user_id=1, conversation_key="dm:1"
        )
    assert reply == ""
