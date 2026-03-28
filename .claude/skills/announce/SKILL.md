---
name: announce
description: Send an announcement message to Discord and/or Slack channels
allowed-tools: [Bash, Read]
user-invocable: true
metadata:
  version: "1.1"
  created: 2026-03-28
  updated: 2026-03-28
  author: trinity
  changelog:
    - "1.1: Add Slack support via Bot OAuth Token + chat.postMessage API"
    - "1.0: Initial version — Discord webhook support"
---

# Announce

## Purpose

Send an arbitrary message to a configured announcement channel. Supports Discord (webhooks) and Slack (Bot OAuth Token + chat.postMessage API).

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Env file | `.env` | Yes | | Webhook URLs and channel config |

## Channel Registry

Channels are configured in `.env` using the naming convention:

```bash
# Discord channels
ANNOUNCE_DISCORD_<NAME>_WEBHOOK=https://discord.com/api/webhooks/...

# Slack channels (Bot OAuth Token + channel IDs)
ANNOUNCE_SLACK_TOKEN=xoxb-...
ANNOUNCE_SLACK_<NAME>_CHANNEL=C0123456789

# Default channel (used when no channel is specified)
ANNOUNCE_DEFAULT_CHANNEL=discord:updates
```

### Currently configured channels

| Name | Platform | Purpose |
|------|----------|---------|
| `updates` | Discord | Trinity community updates channel |
| `updates` | Slack | Slack updates channel (C06MCLZ966Q) |

## Prerequisites

- Webhook URL configured in `.env` (see Setup section)

## Process

### Step 1: Parse Arguments

The skill is invoked as:

```
/announce [message]
/announce [channel] [message]
```

- If no channel is specified, use the default from `ANNOUNCE_DEFAULT_CHANNEL`
- Channel format: `platform:name` (e.g., `discord:updates`)
- If just a name is given, assume `discord:` prefix

### Step 2: Load Configuration

```bash
source .env
```

Resolve the webhook URL from the channel name:

- Parse the channel argument (e.g., `discord:updates` -> platform=`discord`, name=`updates`)
- For Discord: look up `ANNOUNCE_DISCORD_UPDATES_WEBHOOK` (uppercased name)
- For Slack: look up `ANNOUNCE_SLACK_UPDATES_CHANNEL` (uppercased name) and `ANNOUNCE_SLACK_TOKEN`
- If not found, stop and show available channels

### Step 3: Send Message

#### Discord

Post via webhook using curl:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d '{"content": "<message>"}' \
  "$WEBHOOK_URL"
```

- HTTP 204 = success
- Any other status = error, show response body

For multi-line or formatted messages, Discord webhooks support markdown natively.

#### Embedding support

If the message warrants richer formatting, use Discord's embed structure:

```bash
curl -s -H "Content-Type: application/json" \
  -d '{
    "embeds": [{
      "title": "<title>",
      "description": "<body>",
      "color": 5814783
    }]
  }' \
  "$WEBHOOK_URL"
```

Use embeds when the operator provides a title + body, or when the message is long. Use plain `content` for short announcements.

#### Slack

Post via `chat.postMessage` API using Bot OAuth Token:

```bash
RESPONSE=$(curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $ANNOUNCE_SLACK_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"channel\": \"$CHANNEL_ID\", \"text\": \"<message>\"}")
```

- Check `echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['ok'])"` — `True` = success
- If `False`, extract error: `echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','unknown'))"`
- Common errors: `channel_not_found`, `not_in_channel` (bot must be invited to the channel first)

For rich formatting, Slack supports [mrkdwn](https://api.slack.com/reference/surfaces/formatting): `*bold*`, `_italic_`, `` `code` ``, `>` blockquote.

### Step 4: Confirm

Report the result:

```
Sent to discord:updates (HTTP 204)
```

## Outputs

- Message posted to the target channel
- Confirmation of delivery status

---

## Setup

### Discord Webhook Setup

1. Open the Discord channel settings (gear icon)
2. Go to **Integrations** -> **Webhooks**
3. Click **New Webhook**, name it (e.g., "Trinity Announcements")
4. Copy the webhook URL

### Environment Configuration

Add to `.env` (gitignored — never committed):

```bash
# Announce skill - Discord webhooks
ANNOUNCE_DISCORD_UPDATES_WEBHOOK=https://discord.com/api/webhooks/...

# Default channel for /announce without a channel argument
ANNOUNCE_DEFAULT_CHANNEL=discord:updates
```

### Adding More Channels

To add another Discord channel:

```bash
ANNOUNCE_DISCORD_GENERAL_WEBHOOK=https://discord.com/api/webhooks/...
```

Then use: `/announce discord:general Your message here`

### Slack Setup

1. Go to your Slack app's **OAuth & Permissions** page
2. Ensure the bot has `chat:write` scope (and `chat:write.public` if posting to channels the bot isn't in)
3. Copy the **Bot User OAuth Token** (`xoxb-...`)
4. Invite the bot to the target channel: `/invite @YourBotName`
5. Get the channel ID (right-click channel → View channel details → ID at bottom)

Add to `.env`:

```bash
# Announce skill - Slack
ANNOUNCE_SLACK_TOKEN=xoxb-your-bot-token
ANNOUNCE_SLACK_UPDATES_CHANNEL=C06MCLZ966Q

# To add more Slack channels:
# ANNOUNCE_SLACK_GENERAL_CHANNEL=C0123456789
```

Usage: `/announce slack:updates Your message here`
