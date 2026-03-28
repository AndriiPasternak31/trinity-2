---
name: announce
description: Send an announcement message to Discord, Slack, and/or Telegram channels
allowed-tools: [Bash, Read]
user-invocable: true
metadata:
  version: "1.4"
  created: 2026-03-28
  updated: 2026-03-28
  author: trinity
  changelog:
    - "1.4: Add Telegram support via Bot API + sendMessage with topic threading"
    - "1.3: Save each announcement to docs/user-docs/dev-announcements/ with timestamped filename"
    - "1.2: Add message style rule — dense, no-filler announcements"
    - "1.1: Add Slack support via Bot OAuth Token + chat.postMessage API"
    - "1.0: Initial version — Discord webhook support"
---

# Announce

## Purpose

Send an arbitrary message to a configured announcement channel. Supports Discord (webhooks), Slack (Bot OAuth Token + chat.postMessage API), and Telegram (Bot API + sendMessage with topic threading).

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Env file | `.env` | Yes | | Webhook URLs and channel config |
| Announcements | `docs/user-docs/dev-announcements/` | | Yes | Timestamped announcement records |

## Channel Registry

Channels are configured in `.env` using the naming convention:

```bash
# Discord channels
ANNOUNCE_DISCORD_<NAME>_WEBHOOK=https://discord.com/api/webhooks/...

# Slack channels (Bot OAuth Token + channel IDs)
ANNOUNCE_SLACK_TOKEN=xoxb-...
ANNOUNCE_SLACK_<NAME>_CHANNEL=C0123456789

# Telegram channels (Bot API token + chat IDs)
ANNOUNCE_TELEGRAM_TOKEN=<bot-token-from-botfather>
ANNOUNCE_TELEGRAM_<NAME>_CHANNEL=<chat_id>            # channel or group
ANNOUNCE_TELEGRAM_<NAME>_CHANNEL=<chat_id>:<thread_id> # group with topic

# Default channel (used when no channel is specified)
ANNOUNCE_DEFAULT_CHANNEL=discord:updates
```

### Currently configured channels

| Name | Platform | Purpose |
|------|----------|---------|
| `updates` | Discord | Trinity community updates channel |
| `updates` | Slack | Slack updates channel (C06MCLZ966Q) |
| `updates` | Telegram | Telegram group topic (-1001722567447, thread 7491) |

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
- For Telegram: look up `ANNOUNCE_TELEGRAM_UPDATES_CHANNEL` (uppercased name) and `ANNOUNCE_TELEGRAM_TOKEN`. If the channel value contains `:`, split into `chat_id:thread_id` for topic threading.
- If not found, stop and show available channels

### Step 3: Send Message

#### Message Style

Keep announcements dense and information-rich. No filler, no preamble, no "we're excited to announce". Lead with what changed, then why it matters. One sentence per fact. If the update fits in one line, use plain `content`. Only use embeds for multi-fact updates.

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

#### Telegram

Post via Bot API `sendMessage`:

```bash
# Parse chat_id and optional thread_id from channel value
CHANNEL_VALUE="$ANNOUNCE_TELEGRAM_UPDATES_CHANNEL"
if [[ "$CHANNEL_VALUE" == *":"* ]]; then
  CHAT_ID="${CHANNEL_VALUE%%:*}"
  THREAD_ID="${CHANNEL_VALUE##*:}"
  THREAD_PARAM="\"message_thread_id\": $THREAD_ID,"
else
  CHAT_ID="$CHANNEL_VALUE"
  THREAD_PARAM=""
fi

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${ANNOUNCE_TELEGRAM_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{
    \"chat_id\": \"$CHAT_ID\",
    ${THREAD_PARAM}
    \"text\": \"<message>\",
    \"parse_mode\": \"HTML\"
  }")
```

- Check `echo $RESPONSE | python3 -c "import sys,json; r=json.load(sys.stdin); print('ok' if r['ok'] else r['description'])"` — `ok` = success
- Common errors: `Forbidden: bot is not a member of the channel chat` (bot must be admin), `Bad Request: message thread not found` (wrong thread ID)
- HTML formatting: `<b>bold</b>`, `<i>italic</i>`, `<code>code</code>`, `<pre>block</pre>`, `<a href="url">link</a>`
- Max message length: 4096 characters

### Step 4: Confirm

Report the result:

```
Sent to discord:updates (HTTP 204)
```

### Step 5: Save Announcement Record

Save every announcement to `docs/user-docs/dev-announcements/` with a timestamped filename:

```bash
mkdir -p docs/user-docs/dev-announcements
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
FILENAME="docs/user-docs/dev-announcements/${TIMESTAMP}.md"
```

Write the file with frontmatter and the message content:

```markdown
---
date: <ISO 8601 timestamp, e.g. 2026-03-28T14:30:00>
channel: <platform:name, e.g. discord:updates>
---

<message content as sent>
```

Report the saved path:

```
Saved to docs/user-docs/dev-announcements/2026-03-28-143000.md
```

## Outputs

- Message posted to the target channel
- Confirmation of delivery status
- Announcement record saved to `docs/user-docs/dev-announcements/<timestamp>.md`

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

### Telegram Setup

1. Message `@BotFather` on Telegram → `/newbot` → pick a name and username (must end in `bot`)
2. Copy the API token BotFather gives you
3. Add the bot as an **administrator** of your channel/group (must have "Post Messages" permission)
4. For groups with Topics: get the topic thread ID from the topic link (e.g., `https://t.me/c/1722567447/7491` → thread ID is `7491`, chat ID is `-1001722567447`)

Add to `.env`:

```bash
# Announce skill - Telegram
ANNOUNCE_TELEGRAM_TOKEN=<bot-token-from-botfather>
ANNOUNCE_TELEGRAM_UPDATES_CHANNEL=-100XXXXXXXXXX:7491  # chat_id:thread_id for topics
# Without topic: ANNOUNCE_TELEGRAM_GENERAL_CHANNEL=-100XXXXXXXXXX
```

Usage: `/announce telegram:updates Your message here`
