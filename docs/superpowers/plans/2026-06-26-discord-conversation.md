# Discord Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `discord_conversation`, a HACS-installable Home Assistant custom integration that exposes HA's conversation (Assist) capability over a Discord bot — designated channels, `@mentions`, and DMs route to a configured conversation agent and the reply is posted back to Discord.

**Architecture:** An in-process integration. `async_setup_entry` builds a `discord.py` gateway client and runs it as a config-entry background task; each inbound message is filtered, mapped to an HA user identity, and sent to the conversation agent via `conversation.async_converse(...)` (no REST, no token). Logic is split into pure, unit-testable helpers (`text_utils`, `conversation_cache`, `conversation_router`) and thin I/O shells (`bot.py`, `config_flow.py`, `__init__.py`).

**Tech Stack:** Python 3.14, `discord.py==2.7.1`, Home Assistant config-entry framework, `pytest` + `pytest-homeassistant-custom-component`, `uv`/`mise`, `ruff`.

## Global Constraints

These apply to **every** task. Each task's requirements implicitly include this section.

- **Domain:** `discord_conversation` (never `discord` — collides with core). Friendly name "Discord Conversation".
- **Python:** 3.14. **Pin** `discord.py==2.7.1` in `manifest.json` `requirements`.
- **codeowners:** `["@aarontc"]`. Docs/issue URLs → `https://gitlab.idleengineers.com/aaron/home-assistant-discord-conversation`.
- **Conversation call:** `from homeassistant.components.conversation import async_converse`; signature `async_converse(hass, text, conversation_id, context, language=None, agent_id=None, ...)`; reply at `result.response.speech["plain"]["speech"]`; persist `result.conversation_id`.
- **Discord lifecycle:** subclass `discord.Client`; start via `entry.async_create_background_task(hass, client.start(token), name=...)`; `await client.close()` on unload. Never `client.run()`. `intents.message_content = True` (privileged).
- **Options flow:** subclass `OptionsFlowWithReload`. Do **not** define `__init__(self, config_entry)` or assign `self.config_entry` (read-only property in current core). Do **not** also register an update listener (raises `ValueError`).
- **Naming/style (user global rules):** full words not abbreviations; every file ends with a newline; YAML files use `.yaml` (exception: `.gitlab-ci.yml`); SQL n/a. Keep `mise.toml` and `.tool-versions` in sync.
- **No AI attribution anywhere** — commit messages, trailers, comments, docs, author identity. No `Co-Authored-By`/`Generated with` trailers. Write everything as the user's own work.
- **Commits:** conventional-commit style (`feat:`, `test:`, `docs:`, `chore:`). Commit at the end of every task.
- **Test command (from repo root):** `uv run pytest <path> -v`. Discord and `async_converse` are always mocked — no live gateway or LLM in tests.

---

## File Structure

```
home-assistant-discord-conversation/
├─ custom_components/discord_conversation/
│  ├─ __init__.py            # lifecycle: setup/unload, RuntimeData, background task, reauth-on-LoginFailure
│  ├─ const.py               # DOMAIN, CONF_* keys, defaults
│  ├─ text_utils.py          # chunk_message(), strip_self_mention()  (pure)
│  ├─ conversation_cache.py  # ConversationCache  (per-key conversation_id w/ TTL, injected clock)
│  ├─ conversation_router.py # should_respond/resolve_ha_user_id/make_conversation_key + ConversationRouter
│  ├─ discord_api.py         # validate_token(), list_text_channels()  (REST-only discord.py helpers)
│  ├─ bot.py                 # DiscordConversationClient(discord.Client): on_message → router → reply
│  ├─ config_flow.py         # ConfigFlow (user/config/reauth) + OptionsFlow (settings + user-map menu)
│  ├─ manifest.json
│  ├─ strings.json
│  └─ translations/en.json
├─ tests/
│  ├─ conftest.py            # phcc harness + component symlink
│  ├─ test_text_utils.py
│  ├─ test_conversation_cache.py
│  ├─ test_router.py
│  ├─ test_discord_api.py
│  ├─ test_config_flow.py
│  ├─ test_options_flow.py
│  ├─ test_bot.py
│  ├─ test_init.py
│  └─ test_translations.py
├─ hacs.json
├─ pyproject.toml            # dev/test deps, ruff + pytest config
├─ mise.toml                 # python 3.14, uv  (+ .tool-versions mirror)
├─ .tool-versions
├─ .gitlab-ci.yml            # ruff + pytest
├─ .github/workflows/validate.yaml  # HACS + hassfest validation (runs on the GitHub mirror)
├─ .gitignore
├─ README.md
└─ LICENSE
```

Dependency order of tasks: scaffolding → pure helpers (`text_utils`, `conversation_cache`, router helpers, `ConversationRouter`) → `discord_api` → `config_flow` → `OptionsFlow` → `bot` → `__init__` → strings/translations → packaging.

---

### Task 1: Project scaffolding + test harness

**Files:**
- Create: `custom_components/discord_conversation/const.py`
- Create: `custom_components/discord_conversation/__init__.py` (minimal; filled in Task 9)
- Create: `custom_components/discord_conversation/manifest.json`
- Create: `tests/conftest.py`
- Create: `tests/test_scaffolding.py`
- Create: `pyproject.toml`, `mise.toml`, `.tool-versions`, `.gitignore`, `hacs.json`, `LICENSE`, `README.md` (stub)

**Interfaces:**
- Produces: `const.DOMAIN = "discord_conversation"` and all `CONF_*` / default constants used by every later task.

- [ ] **Step 1: Write `const.py`**

```python
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
```

- [ ] **Step 2: Write minimal `__init__.py`** (replaced in Task 9; valid package now)

```python
"""The Discord Conversation integration."""

from __future__ import annotations
```

- [ ] **Step 3: Write `manifest.json`**

```json
{
  "domain": "discord_conversation",
  "name": "Discord Conversation",
  "codeowners": ["@aarontc"],
  "config_flow": true,
  "documentation": "https://gitlab.idleengineers.com/aaron/home-assistant-discord-conversation",
  "iot_class": "cloud_push",
  "issue_tracker": "https://gitlab.idleengineers.com/aaron/home-assistant-discord-conversation/-/issues",
  "requirements": ["discord.py==2.7.1"],
  "version": "0.1.0"
}
```

- [ ] **Step 4: Write `tests/conftest.py`** (adapted from `home-assistant-area-lighting`)

```python
"""Pytest bootstrap: load pytest-homeassistant-custom-component and expose the
component to HA's integration loader via a symlink into testing_config.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMPONENT_DIR = _REPO_ROOT / "custom_components" / "discord_conversation"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _ensure_component_symlink_in_testing_config() -> None:
    try:
        import pytest_homeassistant_custom_component as phcc
    except ImportError:
        return

    target = (
        Path(phcc.__file__).resolve().parent
        / "testing_config"
        / "custom_components"
        / "discord_conversation"
    )
    if target.is_symlink():
        try:
            if target.resolve() == _COMPONENT_DIR.resolve():
                return
        except OSError:
            pass
        target.unlink()
    elif target.exists():
        print(
            f"[discord_conversation conftest] warning: {target} exists and is "
            "not a symlink; skipping auto-link.",
            file=sys.stderr,
        )
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(_COMPONENT_DIR, target)


_ensure_component_symlink_in_testing_config()

pytest_plugins = ["pytest_homeassistant_custom_component"]
```

- [ ] **Step 5: Write `pyproject.toml`**

```toml
[project]
name = "discord-conversation"
version = "0.1.0"
description = "Home Assistant custom integration: Assist conversation over a Discord bot"
requires-python = ">=3.14"

[dependency-groups]
dev = [
    "discord.py==2.7.1",
    "pytest",
    "pytest-homeassistant-custom-component",
    "ruff",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

> Note: pin `pytest-homeassistant-custom-component` (and the `homeassistant` it pulls) to the version matching the **deployed HA** (`haconf/.HA_VERSION`) during implementation, so tests run against the same core the box runs.

- [ ] **Step 6: Write `mise.toml` and `.tool-versions` (kept in sync)**

`mise.toml`:
```toml
[tools]
python = "3.14"
uv = "latest"
```

`.tool-versions`:
```
python 3.14
uv latest
```

- [ ] **Step 7: Write `hacs.json`, `.gitignore`, `LICENSE`, `README.md` stub**

`hacs.json`:
```json
{
  "name": "Discord Conversation",
  "homeassistant": "2024.1.0"
}
```

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
*.egg-info/
```

`README.md` (stub — finalized in Task 10):
```markdown
# Discord Conversation

A Home Assistant custom integration that exposes the Assist conversation agent over a Discord bot.
```

`LICENSE`: MIT, copyright holder "Aaron" (match the author's other repos; confirm preferred license/name at implementation).

- [ ] **Step 8: Write `tests/test_scaffolding.py`**

```python
"""Smoke test: the component imports and the test harness is wired up."""

import json
from pathlib import Path

from custom_components.discord_conversation.const import DOMAIN


def test_domain_constant():
    assert DOMAIN == "discord_conversation"


def test_manifest_is_valid():
    manifest_path = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "discord_conversation"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == ["discord.py==2.7.1"]
    assert manifest["codeowners"] == ["@aarontc"]
```

- [ ] **Step 9: Install deps and run the smoke test**

Run: `uv sync && uv run pytest tests/test_scaffolding.py -v`
Expected: 2 tests PASS (proves the harness, symlink, and package import all work).

- [ ] **Step 10: Commit**

```bash
git add custom_components tests pyproject.toml mise.toml .tool-versions .gitignore hacs.json LICENSE README.md
git commit -m "chore: scaffold discord_conversation component and test harness"
```

---

### Task 2: Text utilities (`text_utils.py`)

**Files:**
- Create: `custom_components/discord_conversation/text_utils.py`
- Test: `tests/test_text_utils.py`

**Interfaces:**
- Produces: `chunk_message(text: str, limit: int = 2000) -> list[str]`; `strip_self_mention(content: str, bot_user_id: int) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from custom_components.discord_conversation.text_utils import (
    chunk_message,
    strip_self_mention,
)


def test_chunk_short_message_single_chunk():
    assert chunk_message("hello") == ["hello"]


def test_chunk_empty_returns_single_empty():
    assert chunk_message("") == [""]


def test_chunk_splits_on_line_boundaries_under_limit():
    text = "\n".join(["line"] * 10)
    chunks = chunk_message(text, limit=12)
    assert all(len(c) <= 12 for c in chunks)
    assert "".join(chunks) == text


def test_chunk_hard_splits_overlong_single_line():
    chunks = chunk_message("x" * 5000, limit=2000)
    assert [len(c) for c in chunks] == [2000, 2000, 1000]
    assert "".join(chunks) == "x" * 5000


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("<@123> hello", "hello"),
        ("<@!123> hello", "hello"),
        ("hey <@123> there", "hey  there".strip()),
        ("no mention", "no mention"),
        ("<@999> keep other", "<@999> keep other"),
    ],
)
def test_strip_self_mention(content, expected):
    assert strip_self_mention(content, 123) == expected
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_text_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: ... text_utils`.

- [ ] **Step 3: Implement `text_utils.py`**

```python
"""Pure text helpers for Discord message formatting."""

from __future__ import annotations

import re

MAX_MESSAGE_LENGTH = 2000


def chunk_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into <=limit pieces, preferring line boundaries."""
    chunks: list[str] = []
    buffer = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(buffer) + len(line) > limit:
            chunks.append(buffer)
            buffer = line
        else:
            buffer += line
    if buffer:
        chunks.append(buffer)
    return chunks or [""]


def strip_self_mention(content: str, bot_user_id: int) -> str:
    """Remove the bot's own mention (<@id> or <@!id>) from raw message content."""
    return re.sub(rf"<@!?{bot_user_id}>", "", content).strip()
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_text_utils.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/discord_conversation/text_utils.py tests/test_text_utils.py
git commit -m "feat: add text chunking and self-mention stripping helpers"
```

---

### Task 3: Conversation cache (`conversation_cache.py`)

**Files:**
- Create: `custom_components/discord_conversation/conversation_cache.py`
- Test: `tests/test_conversation_cache.py`

**Interfaces:**
- Produces: `ConversationCache(ttl: timedelta, now: Callable[[], datetime] = dt_util.utcnow)` with `.get(key) -> str | None` and `.set(key, conversation_id: str | None) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timedelta, timezone

from custom_components.discord_conversation.conversation_cache import ConversationCache


class FakeClock:
    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta):
        self.now += delta


def _clock():
    return FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_get_missing_returns_none():
    cache = ConversationCache(timedelta(minutes=15), now=_clock())
    assert cache.get("channel:1") is None


def test_set_then_get_returns_id():
    cache = ConversationCache(timedelta(minutes=15), now=_clock())
    cache.set("channel:1", "conv-abc")
    assert cache.get("channel:1") == "conv-abc"


def test_expired_entry_evicted():
    clock = _clock()
    cache = ConversationCache(timedelta(minutes=15), now=clock)
    cache.set("channel:1", "conv-abc")
    clock.advance(timedelta(minutes=16))
    assert cache.get("channel:1") is None


def test_within_ttl_survives():
    clock = _clock()
    cache = ConversationCache(timedelta(minutes=15), now=clock)
    cache.set("channel:1", "conv-abc")
    clock.advance(timedelta(minutes=14))
    assert cache.get("channel:1") == "conv-abc"


def test_set_none_clears_entry():
    cache = ConversationCache(timedelta(minutes=15), now=_clock())
    cache.set("channel:1", "conv-abc")
    cache.set("channel:1", None)
    assert cache.get("channel:1") is None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_conversation_cache.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `conversation_cache.py`**

```python
"""Per-conversation-key cache of HA conversation_id with idle TTL eviction."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util


class ConversationCache:
    """Maps a conversation key to (conversation_id, last_used); evicts on idle TTL."""

    def __init__(
        self,
        ttl: timedelta,
        now: Callable[[], datetime] = dt_util.utcnow,
    ) -> None:
        self._ttl = ttl
        self._now = now
        self._store: dict[str, tuple[str, datetime]] = {}

    def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        conversation_id, last_used = item
        if self._now() - last_used > self._ttl:
            del self._store[key]
            return None
        return conversation_id

    def set(self, key: str, conversation_id: str | None) -> None:
        if conversation_id is None:
            self._store.pop(key, None)
            return
        self._store[key] = (conversation_id, self._now())
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_conversation_cache.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/discord_conversation/conversation_cache.py tests/test_conversation_cache.py
git commit -m "feat: add conversation_id cache with idle TTL eviction"
```

---

### Task 4: Router helpers + `ConversationRouter` (`conversation_router.py`)

**Files:**
- Create: `custom_components/discord_conversation/conversation_router.py`
- Test: `tests/test_router.py`

**Interfaces:**
- Consumes: `ConversationCache` (Task 3), `const` (Task 1), `conversation.async_converse`.
- Produces:
  - `make_conversation_key(*, is_dm: bool, channel_id: int, author_id: int) -> str`
  - `resolve_ha_user_id(user_map: dict[int, str], fallback_user: str | None, discord_user_id: int) -> str | None`
  - `ConversationRouter` with `.should_respond(*, is_dm, was_mentioned, channel_id, author_id) -> bool`, `async .process(*, text, discord_user_id, conversation_key) -> str`, and classmethod `.from_entry(hass, entry) -> ConversationRouter`.

- [ ] **Step 1: Write the failing tests**

```python
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
    assert router.should_respond(is_dm=True, was_mentioned=False, channel_id=0, author_id=1) is False


def test_should_respond_allowlist_blocks_unlisted():
    router = _router(allowlist={42})
    assert router.should_respond(is_dm=True, was_mentioned=False, channel_id=0, author_id=1) is False
    assert router.should_respond(is_dm=True, was_mentioned=False, channel_id=0, author_id=42) is True


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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_router.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `conversation_router.py`**

```python
"""Decision logic + HA conversation-agent dispatch for the Discord bot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.conversation import async_converse
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant

from .const import (
    CONF_AGENT_ID,
    CONF_ALLOWLIST,
    CONF_CHANNELS,
    CONF_FALLBACK_USER,
    CONF_IDLE_MINUTES,
    CONF_LANGUAGE,
    CONF_RESPOND_DMS,
    CONF_RESPOND_MENTIONS,
    CONF_USER_MAP,
    DEFAULT_IDLE_MINUTES,
    DEFAULT_RESPOND_DMS,
    DEFAULT_RESPOND_MENTIONS,
)
from .conversation_cache import ConversationCache


def make_conversation_key(*, is_dm: bool, channel_id: int, author_id: int) -> str:
    """One conversation per DM (by user) or per channel."""
    return f"dm:{author_id}" if is_dm else f"channel:{channel_id}"


def resolve_ha_user_id(
    user_map: dict[int, str], fallback_user: str | None, discord_user_id: int
) -> str | None:
    """Mapped HA user, else fallback HA user, else None (unrestricted Context)."""
    return user_map.get(discord_user_id) or fallback_user


@dataclass
class ConversationRouter:
    """Filters Discord messages and dispatches them to an HA conversation agent."""

    hass: HomeAssistant
    agent_id: str | None
    language: str | None
    channels: set[int]
    respond_dms: bool
    respond_mentions: bool
    allowlist: set[int]
    user_map: dict[int, str]
    fallback_user: str | None
    cache: ConversationCache

    def should_respond(
        self, *, is_dm: bool, was_mentioned: bool, channel_id: int, author_id: int
    ) -> bool:
        if self.allowlist and author_id not in self.allowlist:
            return False
        if is_dm:
            return self.respond_dms
        if channel_id in self.channels:
            return True
        if was_mentioned:
            return self.respond_mentions
        return False

    async def process(
        self, *, text: str, discord_user_id: int, conversation_key: str
    ) -> str:
        ha_user_id = resolve_ha_user_id(
            self.user_map, self.fallback_user, discord_user_id
        )
        context = Context(user_id=ha_user_id) if ha_user_id else Context()
        conversation_id = self.cache.get(conversation_key)
        result = await async_converse(
            self.hass,
            text,
            conversation_id,
            context,
            language=self.language,
            agent_id=self.agent_id,
        )
        self.cache.set(conversation_key, result.conversation_id)
        speech = result.response.speech or {}
        return (speech.get("plain") or {}).get("speech") or ""

    @classmethod
    def from_entry(
        cls, hass: HomeAssistant, entry: ConfigEntry
    ) -> "ConversationRouter":
        opts = entry.options
        return cls(
            hass=hass,
            agent_id=opts.get(CONF_AGENT_ID),
            language=opts.get(CONF_LANGUAGE) or None,
            channels={int(c) for c in opts.get(CONF_CHANNELS, [])},
            respond_dms=opts.get(CONF_RESPOND_DMS, DEFAULT_RESPOND_DMS),
            respond_mentions=opts.get(CONF_RESPOND_MENTIONS, DEFAULT_RESPOND_MENTIONS),
            allowlist={int(a) for a in opts.get(CONF_ALLOWLIST, [])},
            user_map={int(k): v for k, v in opts.get(CONF_USER_MAP, {}).items()},
            fallback_user=opts.get(CONF_FALLBACK_USER) or None,
            cache=ConversationCache(
                timedelta(minutes=opts.get(CONF_IDLE_MINUTES, DEFAULT_IDLE_MINUTES))
            ),
        )
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_router.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/discord_conversation/conversation_router.py tests/test_router.py
git commit -m "feat: add conversation router (scope, identity, agent dispatch)"
```

---

### Task 5: Discord REST helpers (`discord_api.py`)

**Files:**
- Create: `custom_components/discord_conversation/discord_api.py`
- Test: `tests/test_discord_api.py`

**Interfaces:**
- Produces: exceptions `InvalidAuth`, `CannotConnect`; `async validate_token(token: str) -> str` (returns bot user id as str); `async list_text_channels(token: str) -> list[tuple[str, str]]` (`(channel_id, "Guild / #name")`).

- [ ] **Step 1: Write the failing tests** (discord.py fully mocked)

```python
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
```

> Note: the `isinstance` patch keeps the test independent of `discord.TextChannel` internals; in real use the filter is `isinstance(ch, discord.TextChannel)`.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_discord_api.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `discord_api.py`**

```python
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
                    channels.append((str(channel.id), f"{guild.name} / #{channel.name}"))
    except discord.LoginFailure as err:
        raise InvalidAuth from err
    except discord.HTTPException as err:
        raise CannotConnect from err
    finally:
        await client.close()
    return channels
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_discord_api.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/discord_conversation/discord_api.py tests/test_discord_api.py
git commit -m "feat: add REST-only discord token validation and channel listing"
```

---

### Task 6: Config flow — user/config/reauth steps (`config_flow.py`)

**Files:**
- Create: `custom_components/discord_conversation/config_flow.py`
- Test: `tests/test_config_flow.py`

**Interfaces:**
- Consumes: `discord_api.validate_token` / `list_text_channels` / `InvalidAuth` / `CannotConnect`, `const`.
- Produces: `DiscordConversationConfigFlow(ConfigFlow, domain=DOMAIN)` with steps `user`, `config`, `reauth`, `reauth_confirm`; entry `data={token, bot_id}`, seeded `options`. (Options handler added in Task 7.)

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import AsyncMock, patch

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
        domain=DOMAIN, unique_id="botid-1", data={CONF_TOKEN: "old", "bot_id": "botid-1"}
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_config_flow.py -v`
Expected: FAIL — module not found / no config flow registered.

- [ ] **Step 3: Implement the config-flow portion of `config_flow.py`**

```python
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
    CONF_IDLE_MINUTES,
    CONF_LANGUAGE,
    CONF_RESPOND_DMS,
    CONF_RESPOND_MENTIONS,
    CONF_TOKEN,
    DEFAULT_IDLE_MINUTES,
    DEFAULT_RESPOND_DMS,
    DEFAULT_RESPOND_MENTIONS,
    DOMAIN,
)
from .discord_api import CannotConnect, InvalidAuth, list_text_channels, validate_token

STEP_USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))}
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
            vol.Optional(CONF_RESPOND_DMS, default=DEFAULT_RESPOND_DMS): BooleanSelector(),
            vol.Optional(
                CONF_RESPOND_MENTIONS, default=DEFAULT_RESPOND_MENTIONS
            ): BooleanSelector(),
            vol.Optional(CONF_IDLE_MINUTES, default=DEFAULT_IDLE_MINUTES): NumberSelector(
                NumberSelectorConfig(min=1, max=240, step=1, mode=NumberSelectorMode.BOX)
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
```

> Add the two missing imports to the top with the others: `from .const import CONF_FALLBACK_USER, CONF_USER_MAP`.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_config_flow.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/discord_conversation/config_flow.py tests/test_config_flow.py
git commit -m "feat: add config flow (token, settings, reauth)"
```

---

### Task 7: Options flow — settings + Discord→HA user mapping

**Files:**
- Modify: `custom_components/discord_conversation/config_flow.py` (add `async_get_options_flow` + `DiscordConversationOptionsFlow`)
- Test: `tests/test_options_flow.py`

**Interfaces:**
- Consumes: `build_config_schema`, `list_text_channels`, `const`, `hass.auth.async_get_users`.
- Produces: an `OptionsFlowWithReload` with steps `init` (menu), `settings`, `add_user_map`, `remove_user_map`. Each persists the **full** merged options via `async_create_entry(title="", data=<merged>)`.

- [ ] **Step 1: Write the failing tests**

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
    assert set(result["menu_options"]) == {"settings", "add_user_map", "remove_user_map"}


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
    with patch.object(hass.auth, "async_get_users", AsyncMock(return_value=[fake_user])):
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_options_flow.py -v`
Expected: FAIL — no options flow (`async_get_options_flow` missing).

- [ ] **Step 3: Implement the options flow** (append to `config_flow.py`)

Add imports at top:
```python
from homeassistant.config_entries import ConfigEntry, OptionsFlow, OptionsFlowWithReload
from homeassistant.core import HomeAssistant, callback
```

Add the registration hook inside `DiscordConversationConfigFlow`:
```python
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return DiscordConversationOptionsFlow()
```

Add helper + handler at module level:
```python
async def _ha_user_options(hass: HomeAssistant) -> list[SelectOptionDict]:
    users = await hass.auth.async_get_users()
    return [
        SelectOptionDict(value=user.id, label=user.name or user.id)
        for user in users
        if user.is_active and not user.system_generated
    ]


class DiscordConversationOptionsFlow(OptionsFlowWithReload):
    """Options: general settings and Discord→HA user mappings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "add_user_map", "remove_user_map"],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            merged = dict(self.config_entry.options)
            merged.update(user_input)
            merged[CONF_LANGUAGE] = merged.get(CONF_LANGUAGE) or None
            return self.async_create_entry(title="", data=merged)

        try:
            channels = await list_text_channels(self.config_entry.data[CONF_TOKEN])
        except (InvalidAuth, CannotConnect):
            channels = []
        channel_options = [
            SelectOptionDict(value=cid, label=label) for cid, label in channels
        ]
        user_options = await _ha_user_options(self.hass)
        schema = build_config_schema(channel_options).extend(
            {
                vol.Optional(CONF_FALLBACK_USER): SelectSelector(
                    SelectSelectorConfig(
                        options=user_options, mode=SelectSelectorMode.DROPDOWN
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="settings",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
        )

    async def async_step_add_user_map(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            merged = dict(self.config_entry.options)
            user_map = dict(merged.get(CONF_USER_MAP, {}))
            user_map[str(user_input["discord_user_id"])] = user_input[CONF_FALLBACK_USER]
            merged[CONF_USER_MAP] = user_map
            return self.async_create_entry(title="", data=merged)

        user_options = await _ha_user_options(self.hass)
        schema = vol.Schema(
            {
                vol.Required("discord_user_id"): TextSelector(),
                vol.Required(CONF_FALLBACK_USER): SelectSelector(
                    SelectSelectorConfig(
                        options=user_options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
            }
        )
        return self.async_show_form(step_id="add_user_map", data_schema=schema)

    async def async_step_remove_user_map(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        user_map = dict(self.config_entry.options.get(CONF_USER_MAP, {}))
        if user_input is not None:
            user_map.pop(str(user_input["discord_user_id"]), None)
            merged = dict(self.config_entry.options)
            merged[CONF_USER_MAP] = user_map
            return self.async_create_entry(title="", data=merged)

        schema = vol.Schema(
            {vol.Required("discord_user_id"): vol.In(sorted(user_map))}
        )
        return self.async_show_form(step_id="remove_user_map", data_schema=schema)
```

> The `add_user_map` step reuses the `CONF_FALLBACK_USER` schema key purely as the HA-user dropdown field name in that form; it is written into `user_map`, not into `fallback_ha_user`. (The general fallback user is set in the `settings` step.)

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_options_flow.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/discord_conversation/config_flow.py tests/test_options_flow.py
git commit -m "feat: add options flow with settings and user mapping"
```

---

### Task 8: Discord gateway client (`bot.py`)

**Files:**
- Create: `custom_components/discord_conversation/bot.py`
- Test: `tests/test_bot.py`

**Interfaces:**
- Consumes: `ConversationRouter`, `text_utils`, `conversation_router.make_conversation_key`.
- Produces: `DiscordConversationClient(hass, router)` (a `discord.Client` subclass) with `async on_message(message)` that filters, dispatches to `router.process(...)`, and sends the chunked reply with a typing indicator.

- [ ] **Step 1: Write the failing tests**

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from custom_components.discord_conversation.bot import DiscordConversationClient


def _message(content, *, author_bot=False, is_dm=False, mentions=None, channel_id=111):
    channel = MagicMock(spec=discord.DMChannel) if is_dm else MagicMock(spec=discord.TextChannel)
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


def _client(router):
    with patch("discord.Client.__init__", return_value=None):
        client = DiscordConversationClient(hass=object(), router=router)
    # discord.Client.user is normally read-only; stub it for tests
    type(client).user = property(lambda self: SimpleNamespace(id=999))
    return client


async def test_on_message_dispatches_and_replies():
    router = MagicMock()
    router.should_respond.return_value = True
    router.process = AsyncMock(return_value="The light is on.")
    client = _client(router)
    msg = _message("<@999> is the light on?", mentions=[SimpleNamespace(id=999)])
    await client.on_message(msg)
    router.process.assert_awaited_once()
    msg.channel.send.assert_awaited_once_with("The light is on.")


async def test_on_message_ignores_other_bots():
    router = MagicMock()
    client = _client(router)
    msg = _message("hi", author_bot=True)
    await client.on_message(msg)
    router.should_respond.assert_not_called()


async def test_on_message_skips_when_should_respond_false():
    router = MagicMock()
    router.should_respond.return_value = False
    router.process = AsyncMock()
    client = _client(router)
    await client.on_message(_message("random channel chatter"))
    router.process.assert_not_called()


async def test_on_message_posts_apology_on_error():
    router = MagicMock()
    router.should_respond.return_value = True
    router.process = AsyncMock(side_effect=RuntimeError("boom"))
    client = _client(router)
    msg = _message("<@999> hi", mentions=[SimpleNamespace(id=999)])
    await client.on_message(msg)
    sent = msg.channel.send.await_args.args[0]
    assert "error" in sent.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_bot.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `bot.py`**

```python
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
        async with message.channel.typing():
            try:
                reply = await self.router.process(
                    text=text, discord_user_id=message.author.id, conversation_key=key
                )
            except Exception:  # noqa: BLE001 - never let the gateway die
                _LOGGER.exception("Conversation processing failed")
                reply = ERROR_REPLY
            for part in chunk_message(reply or EMPTY_REPLY):
                await message.channel.send(part)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_bot.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/discord_conversation/bot.py tests/test_bot.py
git commit -m "feat: add discord gateway client with message dispatch"
```

---

### Task 9: Integration lifecycle (`__init__.py`)

**Files:**
- Modify: `custom_components/discord_conversation/__init__.py`
- Test: `tests/test_init.py`

**Interfaces:**
- Consumes: `ConversationRouter.from_entry`, `DiscordConversationClient`, `const`.
- Produces: `async_setup_entry(hass, entry) -> bool`, `async_unload_entry(hass, entry) -> bool`, `RuntimeData` dataclass on `entry.runtime_data`, and a background gateway task that triggers reauth on `discord.LoginFailure`.

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.discord_conversation.const import (
    CONF_AGENT_ID,
    CONF_BOT_ID,
    CONF_TOKEN,
    DOMAIN,
)


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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_init.py -v`
Expected: FAIL — `async_setup_entry` not defined.

- [ ] **Step 3: Implement `__init__.py`**

```python
"""The Discord Conversation integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import discord

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .bot import DiscordConversationClient
from .const import CONF_TOKEN, DOMAIN
from .conversation_router import ConversationRouter

_LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimeData:
    """Per-entry runtime objects."""

    client: DiscordConversationClient
    router: ConversationRouter


type DiscordConfigEntry = ConfigEntry[RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: DiscordConfigEntry) -> bool:
    """Set up Discord Conversation from a config entry."""
    router = ConversationRouter.from_entry(hass, entry)
    client = DiscordConversationClient(hass, router)
    entry.runtime_data = RuntimeData(client=client, router=router)

    async def _run() -> None:
        try:
            await client.start(entry.data[CONF_TOKEN])
        except discord.LoginFailure:
            _LOGGER.warning("Discord token rejected; starting reauth")
            entry.async_start_reauth(hass)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Discord gateway task failed")

    entry.async_create_background_task(
        hass, _run(), name=f"{DOMAIN}-gateway-{entry.entry_id}"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DiscordConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.client.close()
    return True
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_init.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: every test from Tasks 1–9 PASS.

- [ ] **Step 6: Commit**

```bash
git add custom_components/discord_conversation/__init__.py tests/test_init.py
git commit -m "feat: add integration lifecycle (setup, unload, reauth)"
```

---

### Task 10: UI strings, translations, packaging, CI

**Files:**
- Create: `custom_components/discord_conversation/strings.json`
- Create: `custom_components/discord_conversation/translations/en.json`
- Test: `tests/test_translations.py`
- Modify: `README.md`
- Create: `.gitlab-ci.yml`, `.github/workflows/validate.yaml`

**Interfaces:**
- Produces: all config/options/reauth/error UI text keyed to the step + field names used in Tasks 6–7.

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path


def _load(name):
    base = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "discord_conversation"
    )
    return json.loads((base / name).read_text())


def test_strings_and_en_translation_match():
    assert _load("strings.json") == _load("translations/en.json")


def test_config_steps_have_titles():
    strings = _load("strings.json")
    for step in ("user", "config", "reauth_confirm"):
        assert step in strings["config"]["step"]
    for step in ("init", "settings", "add_user_map", "remove_user_map"):
        assert step in strings["options"]["step"]
    assert "invalid_auth" in strings["config"]["error"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_translations.py -v`
Expected: FAIL — files missing.

- [ ] **Step 3: Write `strings.json`** (then copy verbatim to `translations/en.json`)

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Discord bot token",
        "description": "Paste the bot token from the Discord Developer Portal. Enable the Message Content privileged intent for the application before using channel listening.",
        "data": { "token": "Bot token" }
      },
      "config": {
        "title": "Conversation settings",
        "data": {
          "agent_id": "Conversation agent",
          "channels": "Channels to listen in",
          "respond_dms": "Respond to direct messages",
          "respond_mentions": "Respond to @mentions anywhere",
          "idle_minutes": "Reset a conversation after this many idle minutes",
          "language": "Language (blank = Home Assistant default)",
          "allowlist": "Allowed Discord user IDs (blank = everyone)"
        }
      },
      "reauth_confirm": {
        "title": "Re-enter Discord bot token",
        "data": { "token": "Bot token" }
      }
    },
    "error": {
      "invalid_auth": "The bot token was rejected by Discord.",
      "cannot_connect": "Could not reach Discord. Check connectivity and try again."
    },
    "abort": {
      "already_configured": "This Discord bot is already configured.",
      "reauth_successful": "Token updated."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Discord Conversation options",
        "menu_options": {
          "settings": "Conversation settings",
          "add_user_map": "Add a Discord-to-Home-Assistant user mapping",
          "remove_user_map": "Remove a user mapping"
        }
      },
      "settings": {
        "title": "Conversation settings",
        "data": {
          "agent_id": "Conversation agent",
          "channels": "Channels to listen in",
          "respond_dms": "Respond to direct messages",
          "respond_mentions": "Respond to @mentions anywhere",
          "idle_minutes": "Reset a conversation after this many idle minutes",
          "language": "Language (blank = Home Assistant default)",
          "allowlist": "Allowed Discord user IDs (blank = everyone)",
          "fallback_ha_user": "Fallback Home Assistant user for unmapped Discord users"
        }
      },
      "add_user_map": {
        "title": "Add user mapping",
        "data": {
          "discord_user_id": "Discord user ID",
          "fallback_ha_user": "Home Assistant user"
        }
      },
      "remove_user_map": {
        "title": "Remove user mapping",
        "data": { "discord_user_id": "Discord user ID" }
      }
    }
  }
}
```

- [ ] **Step 4: Copy to `translations/en.json`** (must be byte-identical to satisfy the parity test)

Run: `cp custom_components/discord_conversation/strings.json custom_components/discord_conversation/translations/en.json`

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_translations.py -v`
Expected: all PASS.

- [ ] **Step 6: Write `README.md`** (full)

Cover: what it does; install via HACS custom repository (point at the **GitHub mirror** `https://github.com/aarontc/home-assistant-discord-conversation`, type Integration); creating a Discord application + bot, **enabling the Message Content privileged intent**, inviting the bot with `applications.commands` + read/send-message permissions; setup (token → agent/channels/toggles); the **security warning** (channel + allowlist gate, agent can control the house, set a least-privilege `fallback_ha_user`); user-mapping instructions (enable Discord Developer Mode → copy user ID). Keep it concise with examples.

- [ ] **Step 7: Write `.gitlab-ci.yml`**

```yaml
stages: [lint, test]

default:
  image: python:3.14-slim
  before_script:
    - pip install uv
    - uv sync

ruff:
  stage: lint
  script:
    - uv run ruff check .

pytest:
  stage: test
  script:
    - uv run pytest -v
```

- [ ] **Step 8: Write `.github/workflows/validate.yaml`** (runs on the HACS GitHub mirror)

```yaml
name: Validate

on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master
```

- [ ] **Step 9: Run the full suite + lint**

Run: `uv run pytest -v && uv run ruff check .`
Expected: all tests PASS, ruff clean.

- [ ] **Step 10: Commit**

```bash
git add custom_components/discord_conversation/strings.json \
  custom_components/discord_conversation/translations/en.json \
  tests/test_translations.py README.md .gitlab-ci.yml .github/workflows/validate.yaml
git commit -m "feat: add UI strings, translations, docs, and CI"
```

---

## Self-Review

**Spec coverage** (each spec section → task):
- §3 in-process `async_converse` → Task 4. §3 agent picker `EntitySelector` → Task 6. §3 bot lifecycle → Tasks 8–9. §3 Message Content intent → Task 8 (`intents.message_content`) + Task 10 (README). §3 HACS GitHub-only → Task 10 (README + GitHub validate workflow). §4 decisions → Tasks 4/6/7/8. §5 naming → Task 1. §6 topology/modules → all. §7 config+options flow → Tasks 6–7. §8 message→reply flow → Task 8. §9 user mapping → Tasks 4 (resolve) + 7 (config). §10 state/cache → Task 3. §11 error handling → Tasks 5/8/9. §12 security (allowlist/fallback/intent/secret token) → Tasks 4/7/8/10. §13 testing harness → Task 1 + tests throughout. §14 packaging/CI → Tasks 1 + 10. **No gaps.**

**Placeholder scan:** no "TBD/TODO/handle edge cases"; every code/test step has concrete content. Two intentional implementation-time notes (pin `phcc`/`homeassistant` to deployed HA version; confirm LICENSE name) are explicit decisions, not vague placeholders.

**Type consistency:** `make_conversation_key`/`resolve_ha_user_id`/`ConversationRouter.{should_respond,process,from_entry}` signatures match between Task 4 (definition) and Tasks 8–9 (use). `validate_token`/`list_text_channels` signatures match between Task 5 and Tasks 6–7. `build_config_schema`/`_ha_user_options` shared between Tasks 6 and 7. `RuntimeData.client/.router` consistent across Tasks 8–9. CONF_* keys consistent from Task 1. ✅

**One known cross-task note:** Task 6 Step 3 references `CONF_USER_MAP`/`CONF_FALLBACK_USER` in `async_step_config`; the step explicitly instructs adding those two imports. Verified consistent.
