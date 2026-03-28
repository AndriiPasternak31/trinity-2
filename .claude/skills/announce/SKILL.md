---
name: announce
description: Send an announcement message to a Discord channel (or other platforms in future) via webhook
allowed-tools: [Bash, Read]
user-invocable: true
metadata:
  version: "1.0"
  created: 2026-03-28
  author: trinity
---

# Announce

## Purpose

Send an arbitrary message to a configured announcement channel. Currently supports Discord via webhooks. Designed to be extensible to Slack and other platforms.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Env file | `.env` | Yes | | Webhook URLs and channel config |

## Channel Registry

Channels are configured in `.env` using the naming convention:

```bash
# Discord channels
ANNOUNCE_DISCORD_<NAME>_WEBHOOK=https://discord.com/api/webhooks/...

# Default channel (used when no channel is specified)
ANNOUNCE_DEFAULT_CHANNEL=discord:updates
```

### Currently configured channels

| Name | Platform | Purpose |
|------|----------|---------|
| `updates` | Discord | Trinity community updates channel |

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
- Look up `ANNOUNCE_DISCORD_UPDATES_WEBHOOK` (uppercased name)
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

### Future: Slack

When Slack support is added, the pattern extends to:

```bash
ANNOUNCE_SLACK_GENERAL_WEBHOOK=https://hooks.slack.com/services/...
```

And usage: `/announce slack:general Your message here`
