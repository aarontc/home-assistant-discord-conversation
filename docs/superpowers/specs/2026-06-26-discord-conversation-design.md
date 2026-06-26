# Design: `discord_conversation` — Home Assistant custom component

**Date:** 2026-06-26
**Status:** Approved (pre-implementation)
**Repo (primary):** `https://gitlab.idleengineers.com/aaron/home-assistant-discord-conversation`
**Repo (HACS mirror):** `https://github.com/aarontc/home-assistant-discord-conversation` (public, push-mirrored from GitLab)

## 1. Goal

Expose Home Assistant's conversation (Assist) capability through a Discord bot. A
designated Discord channel becomes an ongoing conversation with HA; users can also
`@mention` the bot in any channel it can see, or DM it. Each inbound message is routed
to a configured HA conversation agent and the agent's text reply is posted back to
Discord.

This is the text-chat equivalent of the Assist dialog in the HA UI — same conversation
agents, same exposed entities, same tools, same system-prompt scoping — reached over
Discord instead of the frontend.

The component is generic and HACS-installable: the target agent is selectable, so it
works for any HA user, not just the author's local `ollama-shim`/llama-server stack.

## 2. Why a custom component (not a standalone bot)

A standalone container would have to call HA's REST conversation API with a long-lived
token. Running **in-process** as a custom component is cleaner:

- Calls the conversation agent directly via `conversation.async_converse(...)` — no HTTP,
  no token to manage or rotate.
- Native config-flow setup UX (add integration → token → channels/agent), reusing HA's
  config-entry framework (we write our own `config_flow.py`; we do **not** extend the
  core `discord` notify integration's flow).
- The Discord gateway connection is owned by the config-entry lifecycle.

Going through HA's conversation agent (rather than talking to `ollama-shim`/llama-server
directly) is deliberate: it reuses the agent's exposed-entity set, MCP tool wiring, and
the safety-scoped system prompt. Bypassing HA would lose all of that.

## 3. Confirmed technical facts (primary sources)

Verified against current `home-assistant/core` (`dev`) and HACS docs, 2026-06-26:

- **In-process conversation call** (`homeassistant/components/conversation/agent_manager.py`):
  ```python
  async def async_converse(
      hass, text, conversation_id, context,
      language=None, agent_id=None, device_id=None,
      satellite_id=None, extra_system_prompt=None,
  ) -> ConversationResult
  ```
  `text`, `conversation_id`, `context` are positional (`conversation_id=None` starts a
  fresh conversation; `context` is a `homeassistant.core.Context`). Reply text:
  `result.response.speech["plain"]["speech"]`. Persist `result.conversation_id` and pass
  it back to continue. `result.continue_conversation` indicates the agent expects a
  follow-up. `agent_id` accepts a `conversation.*` entity_id (any `agent_id` containing a
  `.` is resolved as a conversation entity), so a specific configured agent (e.g. an
  Ollama subentry) can be targeted.
- **Agent picker:** `EntitySelector(EntitySelectorConfig(filter=EntityFilterSelectorConfig(domain="conversation")))`
  lists all configured conversation agents and returns the chosen entity_id.
- **discord.py inside HA:** start via
  `entry.async_create_background_task(hass, client.start(token), name=...)` (auto-cancelled
  on unload); store the client in `entry.runtime_data`; `await client.close()` in
  `async_unload_entry`. Use `client.start()` (coroutine on `hass.loop`), never
  `client.run()`/`asyncio.run` (those try to own the loop). Pin `discord.py` in
  `manifest.json` `requirements`.
- **Message Content privileged intent:** reading arbitrary message text in guild channels
  requires Discord's Message Content privileged intent (Developer Portal **and**
  `intents.message_content = True` in code). DMs, `@mention`s, and replies to the bot are
  exempt — but our broad listen scope reads full channel messages, so the intent is
  **mandatory**.
- **HACS is GitHub-only:** *"Only public repositories on GitHub will work with HACS"*
  (hacs.xyz/docs/publish/start). HACS is built on the GitHub API. GitLab cannot be the
  install source. Hence GitLab-primary + public-GitHub-mirror.
- **Options reload:** subclass `OptionsFlowWithReload` so option changes auto-reload the
  entry (reconnect the bot with new settings).

## 4. Approved decisions

| Decision | Choice |
|---|---|
| Listen scope | Selected channels (respond to all messages) **+** `@mention` anywhere **+** DMs |
| Context scope | Per channel / per DM; idle reset (default 15 min) |
| Reply UX | Typing indicator + single reply (HA's converse returns the full response) |
| Agent targeting | Generic — user picks any `conversation.*` agent (defaults to first available) |
| Discord→HA user mapping | Included; unmapped users handled gracefully (optional fallback HA user, else plain `Context()`) |
| Transport | In-process `async_converse` |
| Voice/STT/TTS | Out of scope for v1 (text only) |
| Hosting | GitLab primary + public GitHub mirror for HACS |

## 5. Naming

- **Domain:** `discord_conversation` (cannot be `discord` — collides with the core notify
  integration).
- **Friendly name:** "Discord Conversation".
- **GitLab repo:** `home-assistant-discord-conversation` (one-repo-per-component, matching
  `home-assistant-area-lighting`). Vendored into `haconf/custom_components/` on install
  like other HACS components.
- **`codeowners`:** `["@aarontc"]`.

## 6. Architecture / topology

One config entry = one Discord bot identity (one token). The bot may serve multiple
guilds; the channel list spans whichever guilds the bot has been invited to.

```
Discord gateway ──▶ on_message ──▶ should_respond? ──▶ resolve identity ──▶ async_converse ──▶ reply
   (cloud_push)      (in HA loop)   scope + allowlist    Discord→HA user      (HA agent)        (chunked,
                                                          mapping                                 typing shown)
```

Module layout inside the component:

```
custom_components/discord_conversation/
├─ __init__.py            # async_setup_entry / async_unload_entry, runtime_data, background task
├─ config_flow.py         # token step, config step, OptionsFlowWithReload (incl. user-mapping menu)
├─ bot.py                 # discord.Client subclass/factory + on_message → dispatch
├─ conversation_router.py # should_respond(), conversation_id cache w/ TTL, identity resolution, async_converse call, reply chunking
├─ const.py               # DOMAIN, CONF_* keys, defaults
├─ manifest.json          # config_flow:true, iot_class:cloud_push, requirements:[discord.py], version, codeowners
├─ strings.json           # config/options flow UI strings + error keys
└─ translations/en.json   # mirror of strings.json
```

Boundaries: `bot.py` owns Discord I/O (gateway, message receive, reply send, typing).
`conversation_router.py` owns the decision logic and HA-side calls (pure-ish, testable
without a live gateway). `config_flow.py` owns setup/options. `__init__.py` is lifecycle
glue. Each is independently testable.

## 7. Config flow & options flow

### 7.1 Initial config flow
- **Step `user`:** bot token (`TextSelector`, password mode). Validate with a throwaway
  `discord.Client.login(token)` (no gateway connect); on success, enumerate the bot's
  guild text channels to populate step 2. Invalid token → form error (`invalid_auth`).
- **Step `config`:**
  - **Agent:** `EntitySelector(domain="conversation")`, default = first available agent.
  - **Channels:** `SelectSelector(multiple=True)`, options labelled `guild / #channel`.
    If the bot is in no guilds yet, allow finishing with zero channels (invite the bot,
    then add channels via options).
  - **Respond to DMs:** boolean (default on).
  - **Respond to @mentions anywhere:** boolean (default on).
  - **Idle reset (minutes):** number (default 15).
  - **Language:** optional text (default: HA's configured language → `None`).
  - **User allowlist:** optional list of Discord user IDs (empty = everyone). Security gate.

Token persisted in `entry.data`; everything else in `entry.options` so it's editable.

### 7.2 Options flow (`OptionsFlowWithReload`)
A menu (`async_show_menu`):
- **General settings:** re-edit the step-`config` form above.
- **User mappings:** manage Discord→HA user mappings (see §9). Add-one / remove-selected
  sub-steps.

Changing options reloads the entry, which reconnects the bot with the new settings.

## 8. Message → reply flow (`on_message`)

1. Ignore messages authored by the bot itself or by other bots (`message.author.bot`).
2. **Decide to respond** (`should_respond`):
   - DM and *respond-to-DMs* enabled, **or**
   - bot is `@mention`ed and *respond-to-mentions* enabled, **or**
   - message is in a configured channel.
   Otherwise ignore.
3. **Allowlist check:** if a user allowlist is set and the author's ID is not in it,
   ignore.
4. **Resolve HA identity** (§9): mapped HA user → fallback HA user → none.
5. **Conversation key:** `channel.id` for guild channels; `("dm", author.id)` for DMs.
   Look up `{key: (conversation_id, last_ts)}`. If `now - last_ts > ttl`, reset
   (`conversation_id = None`). (Time obtained via HA's clock, e.g.
   `homeassistant.util.dt.utcnow()`.)
6. Strip the bot mention from the message text; ignore empty/whitespace-only results.
7. `async with channel.typing():` →
   `async_converse(hass, text, conversation_id, context, language=language, agent_id=agent_id)`
   where `context = Context(user_id=ha_user_id)` (or `Context()` if unmapped & no fallback).
8. `reply = result.response.speech["plain"]["speech"]`. Post it, chunked to Discord's
   2000-char limit (split on paragraph/line boundaries where possible). Empty reply →
   post a small placeholder (e.g. "(no response)").
9. Save `result.conversation_id` + current timestamp under the key. If
   `result.continue_conversation` is `False`, the conversation may be expired immediately
   (next message starts fresh) — v1 keeps it until TTL for simplicity; revisit if it
   causes stale-context confusion.

## 9. Discord → HA user mapping

**Purpose:** run `async_converse` under a real HA user's `Context`, so actions are
attributed to that user and respect their permissions.

**Storage:** `entry.options`:
- `user_map: { "<discord_user_id>": "<ha_user_id>", ... }` — per-user mappings.
- `fallback_ha_user: "<ha_user_id>" | None` — identity for unmapped Discord users.

**HA user choices:** built dynamically from `await hass.auth.async_get_users()`, filtering
out `system_generated` and inactive users, as `SelectSelector` options
`{value: user.id, label: user.name}`. (HA has no built-in user selector.)

**Resolution at message time:**
1. `user_map[discord_user_id]` if present, else
2. `fallback_ha_user` if set, else
3. `None` → plain `Context()`.

**Graceful unmapped handling:** unmapped users are still served (per the user's
requirement). The reply path never errors on a missing mapping.

**Security nuance (documented in README + §11):** a plain `Context()` has *no* user_id and
therefore no per-user permission restriction — it is effectively unrestricted. So:
- The **user allowlist** remains the real security gate for *who* may talk to the bot.
- Setting a **least-privilege `fallback_ha_user`** is the recommended way to constrain
  unmapped callers' *capabilities*, rather than leaving them on a bare `Context()`.

## 10. State management

A per-entry in-memory dict (`{conversation_key: (conversation_id, last_ts)}`) with lazy
TTL eviction on access. No persistence: HA owns the real conversation history keyed by
`conversation_id`; a fresh start after an HA restart is acceptable and intentional. The
dict lives on the entry runtime (e.g. a small `RuntimeData` dataclass in
`entry.runtime_data` holding the client, router, and cache).

## 11. Error handling

- **Invalid/revoked token at runtime** → raise `ConfigEntryAuthFailed` to trigger HA's
  reauth flow.
- **`async_converse` raises** → post a short apology to the channel and log the exception;
  never let it kill the gateway task.
- **Gateway disconnect** → discord.py's built-in reconnect handles it; we do not
  reimplement reconnection.
- **Overlong reply** → chunk to ≤2000 chars.
- **Typing indicator failure** → wrapped so it never blocks the actual reply.
- **Unload** → `await client.close()` for a clean gateway disconnect (the background task
  is also auto-cancelled), plus any `entry.async_on_unload` teardown.

## 12. Security

- **Channel list + scope toggles** are the primary scoping mechanism (only respond where
  configured).
- **User allowlist** (optional but strongly recommended) gates *who* may use the bot —
  this agent can control the house. README warns against exposing it on public servers.
- **`fallback_ha_user`** constrains unmapped users' capabilities (see §9).
- **Message Content privileged intent** is required and documented (Developer Portal +
  code).
- **Token** stored in `entry.data`, rendered as a secret (password field) in the UI; never
  logged.

## 13. Testing strategy

Mirror `home-assistant-area-lighting`'s harness: `pytest-homeassistant-custom-component`
with a component-local `conftest.py` that (a) puts the repo root on `sys.path`, (b) loads
the `pytest_homeassistant_custom_component` plugin, and (c) symlinks the component into the
harness's `testing_config/custom_components/`.

Test layers:
- **Unit** (`conversation_router`): `should_respond` truth table (DM/mention/channel ×
  toggles), allowlist filtering, conversation_id cache + TTL reset, identity resolution
  (mapped / fallback / none), reply chunking, mention stripping. Discord and
  `async_converse` mocked.
- **Config/options flow:** token validation (mocked `login`), channel enumeration, schema,
  user-mapping add/remove, options reload. Use HA's flow test helpers.
- **Integration:** `async_setup_entry` / `async_unload_entry` start and stop the background
  task and register/close a mocked client.
- **Translations:** `strings.json` ↔ `translations/en.json` parity (as `area_lighting`
  does).

`async_converse` and `discord.Client` are mocked throughout — no live Discord or LLM in
tests.

## 14. Packaging, tooling, CI, distribution

- **`manifest.json`:** `domain: discord_conversation`, `name: "Discord Conversation"`,
  `config_flow: true`, `iot_class: "cloud_push"`, `requirements: ["discord.py==<current stable 2.x>"]`
  (exact pin resolved against the latest stable discord.py 2.x release at implementation
  time), `codeowners: ["@aarontc"]`, `documentation`/`issue_tracker` → the GitLab repo,
  `version` (kept in sync with release tags).
- **`hacs.json`** (repo root): `{ "name": "Discord Conversation" }`.
- **Repo files:** `README.md` (setup, privileged intent, security warnings, HACS custom-repo
  instructions pointing at the GitHub mirror), `LICENSE`, `mise.toml` (Python 3.14, uv) with
  a `.tool-versions` mirror kept in sync, `.gitlab-ci.yml` (ruff + pytest).
- **HACS validation** (hassfest / HACS Action) runs on the **GitHub** side (GitHub Actions);
  optional, added post-mirror.
- **Distribution:** GitLab primary; push-mirror to the public GitHub repo (configured in
  GitLab repo settings during implementation). Tag releases matching `manifest.version`.
  Users install by adding the GitHub mirror as a HACS custom repository (type: Integration);
  default-store submission is a possible later step.
- **CI security rule:** any executable downloaded in CI must be integrity-verified; the
  pipeline uses uv/python provisioned via mise, so no `curl | sh`.

## 15. Out of scope (v1) / future

- Voice (STT/TTS, voice-channel audio) — text only for now.
- Streaming/incremental reply edits — single reply with typing indicator.
- Slash commands — natural-language messages only.
- Discord threads as conversations — per-channel/per-DM context only.
- Per-message attachments/images to the agent.
- Default-store HACS submission (custom-repo install first).

## 16. Open questions

None blocking. Deferred-by-design items are listed in §15.
