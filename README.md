# Discord Conversation

A Home Assistant custom integration that exposes the Assist conversation agent over a Discord bot. Users can send messages in configured channels or DMs, and the bot replies using whichever conversation agent you select (e.g. a local LLM, OpenAI, or the built-in Home Assistant Assist agent).

## Features

- Responds in configured guild text channels
- Responds to direct messages (optional)
- Responds to @mentions in any channel the bot can see (optional)
- Per-conversation context window with configurable idle timeout
- Allowlist to restrict which Discord users can interact with the bot
- Maps Discord user IDs to Home Assistant users so commands run as the right person

## Security warning

**The conversation agent can control your home.** Anyone who can send messages to the bot can issue commands that Home Assistant will execute. Before deploying:

- Configure `channels` to limit which channels the bot reads.
- Set `allowlist` to restrict access to specific Discord user IDs. With an empty allowlist, any Discord user who can reach the bot can control your home.
- Set a `fallback_ha_user` with the minimum privileges needed. Do not leave this pointing at a Home Assistant admin account for general users.
- Revoke any Discord channel permissions that would let untrusted users DM the bot or add it to servers you do not control.

## Installation

### Prerequisites

- Home Assistant 2024.1.0 or later
- [HACS](https://hacs.xyz) installed

### Install via HACS

1. Open HACS in Home Assistant.
2. Click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/aarontc/home-assistant-discord-conversation` with category **Integration**.
4. Find **Discord Conversation** in the HACS integration list and install it.
5. Restart Home Assistant.

## Discord setup

### Create a Discord application and bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Name the application (e.g. "Home Assistant") and click **Create**.
3. In the left sidebar, click **Bot**.
4. Click **Add Bot** → **Yes, do it!**
5. Under **Token**, click **Reset Token** and copy the token — you will need it during integration setup.
6. Under **Privileged Gateway Intents**, enable **Message Content Intent**. Without this, the bot cannot read message text in guild channels.

### Invite the bot to your server

1. In the Developer Portal, go to **OAuth2 → URL Generator**.
2. Under **Scopes**, select `bot` and `applications.commands`.
3. Under **Bot Permissions**, select **Read Messages/View Channels**, **Send Messages**, and **Read Message History**.
4. Copy the generated URL, open it in your browser, and invite the bot to your server.

## Configuration

1. In Home Assistant, go to **Settings → Devices & Services → Add Integration** and search for **Discord Conversation**.
2. Enter the bot token.
3. Select a conversation agent (e.g. `conversation.home_assistant`).
4. Select the channels the bot should read. Only text channels the bot can see are listed.
5. Adjust the remaining options:

| Option | Default | Description |
|--------|---------|-------------|
| Channels to listen in | (none) | Guild text channels where the bot responds to all messages |
| Respond to direct messages | Yes | Whether to respond when users DM the bot |
| Respond to @mentions anywhere | Yes | Whether to respond when the bot is @mentioned in any channel |
| Idle minutes | 30 | Minutes of inactivity before conversation context resets |
| Language | (HA default) | BCP-47 language tag passed to the conversation agent |
| Allowed Discord user IDs | (everyone) | Comma-separated Discord user IDs; leave blank to allow all |

## User mapping

Map a Discord user ID to a specific Home Assistant user so commands run with that user's permissions.

### Find a Discord user ID

1. In Discord, open **User Settings → Advanced** and enable **Developer Mode**.
2. Right-click any user and click **Copy User ID**.

### Add a mapping

1. Go to **Settings → Devices & Services**, find the Discord Conversation entry, and click **Configure**.
2. Choose **Add a Discord-to-Home-Assistant user mapping**.
3. Enter the Discord user ID and select the Home Assistant user.

### Fallback user

Set **Fallback Home Assistant user** in options to control which HA user is used for Discord users who have no explicit mapping. Use a dedicated, least-privilege account for this.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).
