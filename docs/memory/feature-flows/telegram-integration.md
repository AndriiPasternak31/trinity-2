# Feature: Telegram Bot Integration (TELEGRAM-001)

## Overview
Per-agent Telegram bots with 1:1 agent-to-bot mapping, enabling users to chat with Trinity agents via Telegram text, photos, and documents. Agents are shareable via `t.me/BotUsername` links.

## User Story
As an agent owner, I want to connect a Telegram bot to my agent so that external users can interact with it via Telegram without needing a Trinity account.

## Entry Points
- **API (configure)**: `PUT /api/agents/{name}/telegram` — bind a bot token to an agent
- **API (webhook)**: `POST /api/telegram/webhook/{webhook_secret}` — receive Telegram updates (public, no JWT)
- **API (status)**: `GET /api/agents/{name}/telegram` — check binding status
- **API (delete)**: `DELETE /api/agents/{name}/telegram` — remove bot binding
- **API (test)**: `POST /api/agents/{name}/telegram/test` — send test message or verify bot

## Architecture

### Phase 0: Adapter Generalization

Before Telegram was added, the message router had 6 Slack-specific hardcodings. These were replaced with abstract adapter methods on the `ChannelAdapter` base class:

- `src/backend/adapters/base.py` — Added abstract methods:
  - `channel_type` (property) — `"slack"` or `"telegram"`
  - `get_rate_key(message)` — rate-limit key per sender
  - `get_session_identifier(message)` — session key for conversation persistence
  - `get_source_identifier(message)` — audit trail identifier
  - `get_bot_token(message)` — resolve the bot/app token for responses
- `src/backend/adapters/message_router.py` — All 6 hardcodings replaced with `adapter.channel_type`, `adapter.get_rate_key()`, etc.
- `src/backend/adapters/slack_adapter.py` — Added backward-compatible overrides of the new methods

### Layer Diagram

```
Telegram Bot API
    |
    v (HTTP POST)
FastAPI: POST /api/telegram/webhook/{webhook_secret}
    |
    v
routers/telegram.py:55 → handle_telegram_webhook()
    |
    v
TelegramWebhookTransport.handle_webhook()
    |  - Resolve binding by webhook_secret
    |  - Validate X-Telegram-Bot-Api-Secret-Token header
    |  - Dedup by update_id
    |  - Inject _bot_id + _agent_name into update dict
    v (asyncio.create_task — returns 200 immediately)
TelegramWebhookTransport._process_update()
    |  - Commands (/start, /help, /reset) → direct response
    |  - Regular messages → on_event(update)
    v
ChannelTransport.on_event() (base.py:52)
    |
    v
TelegramAdapter.parse_message(update)
    |  - Extract text, media context, user/chat IDs
    |  - Build NormalizedMessage with metadata
    v
ChannelMessageRouter.handle_message(adapter, message)
    |  - Resolve agent, bot token, rate limit
    |  - Check container status
    |  - Get/create session
    |  - Build context prompt
    |  - Send typing indicator
    |  - Execute via TaskExecutionService
    |  - Persist messages
    v
TelegramAdapter.send_response()
    |  - Convert markdown → Telegram HTML
    |  - Split at 4096 char limit
    |  - POST sendMessage to Telegram Bot API
    v
User receives response in Telegram
```

## Backend Layer

### Router: `src/backend/routers/telegram.py`

Two routers are registered in `main.py:523-524`:

**Public router** (`/api/telegram`):
- `POST /webhook/{webhook_secret}` (line 54) — Receives Telegram updates. No JWT auth; validated by webhook secret in URL + `X-Telegram-Bot-Api-Secret-Token` header. Always returns 200 to prevent Telegram retries.

**Authenticated router** (`/api/agents`):
- `GET /{agent_name}/telegram` (line 95) — Returns binding status (bot_username, bot_id, webhook_url, bot_link, configured flag). No token decryption.
- `PUT /{agent_name}/telegram` (line 116) — Configure bot. Validates token format (`id:secret`), calls `getMe` API, checks bot_id uniqueness across agents, creates encrypted binding, registers webhook if `public_chat_url` is set.
- `DELETE /{agent_name}/telegram` (line 190) — Calls Telegram `deleteWebhook`, then deletes binding + chat links from DB.
- `POST /{agent_name}/telegram/test` (line 211) — Without `chat_id`: verifies bot via `getMe`. With `chat_id`: sends test message.

### Transport: `src/backend/adapters/transports/telegram_webhook.py`

`TelegramWebhookTransport` extends `ChannelTransport`:
- `start()` / `stop()` (lines 25-32) — No-ops; transport is passive (FastAPI endpoint handles requests).
- `handle_webhook(request, webhook_secret)` (line 34) — Core inbound handler:
  1. Resolve binding by `webhook_secret` via DB
  2. Validate `X-Telegram-Bot-Api-Secret-Token` header
  3. Parse JSON body
  4. Dedup by `update_id` (skip if <= `last_update_id`)
  5. Update `last_update_id` in DB
  6. Inject `_bot_id` and `_agent_name` into update dict
  7. `asyncio.create_task(_process_update(...))` — returns 200 immediately
- `_process_update(update, binding)` (line 79) — Commands are handled directly; regular messages go through `on_event()` → adapter → router pipeline.

**Webhook lifecycle functions** (module-level):
- `register_webhook(agent_name, public_url)` (line 120) — Calls Telegram `setWebhook` with URL + secret_token + `allowed_updates: ["message"]`. Updates `webhook_url` in DB on success.
- `delete_webhook(agent_name)` (line 165) — Calls Telegram `deleteWebhook`.

### Adapter: `src/backend/adapters/telegram_adapter.py`

`TelegramAdapter` implements `ChannelAdapter`:

**Identity and routing** (used by message_router):
- `channel_type` → `"telegram"`
- `get_rate_key()` → `telegram:{bot_id}:{sender_id}`
- `get_session_identifier()` → `{bot_id}:{sender_id}:{chat_id}`
- `get_source_identifier()` → `telegram:{bot_id}:{sender_id}`
- `get_bot_token()` → decrypts from DB via `db.get_telegram_bot_token(agent_name)`

**Message processing**:
- `parse_message(raw_event)` (line 66) — Extracts text + media context from Telegram Update. Skips bot messages. Returns `NormalizedMessage` with metadata including `bot_id`, `agent_name`, `username`, media flags.
- `send_response(channel_id, response, thread_id)` (line 123) — Converts markdown to HTML, splits at 4096 chars, sends via `sendMessage`. Falls back to plain text if HTML parsing fails (line 247).
- `indicate_processing(message)` (line 158) — Sends `typing` chat action.

**Bot commands** (line 168):
- `/start` — Welcome message with agent name
- `/help` — Capabilities list (text, photos, documents)
- `/reset` — Clears conversation session via `db.clear_public_chat_session()`

**Message formatting**:
- `_markdown_to_html()` (line 274) — Converts `**bold**`, `*italic*`, `` `code` ``, `~~strike~~` to Telegram HTML tags
- `_split_message()` (line 298) — Splits at paragraph/sentence/word boundaries within 4096 char limit
- `_extract_media_context()` (line 327) — Generates descriptive context for photos, documents, stickers, locations, voice, video

### Media Service: `src/backend/services/telegram_media.py`

- `download_telegram_file(bot_token, file_id)` (line 29) — Two-step download: `getFile` → download from file path. **SSRF prevention**: hostname must be `api.telegram.org` (line 71). **Size limit**: 20MB (line 58).
- `process_photo(bot_token, photo_sizes)` (line 93) — Downloads largest photo, saves to temp file, returns size description. Temp file always cleaned up.
- `process_document(bot_token, document)` (line 127) — Downloads and extracts text from plain text files (.txt, .md, .csv, .json, .py, etc.). Truncates at 10,000 chars. Non-text files get metadata-only description.

### Message Router: `src/backend/adapters/message_router.py`

The `ChannelMessageRouter` is channel-agnostic. For Telegram messages it follows the same 13-step pipeline as Slack:

1. Resolve agent via `adapter.get_agent_name()`
2. Resolve bot token via `adapter.get_bot_token()`
3. Rate limit via `adapter.get_rate_key()` (30 msgs / 60s default)
4. Check agent container status
5. Handle verification (default: always verified for Telegram)
6. Get/create session via `adapter.get_session_identifier()`
7. Build context prompt from session history
8. Show typing indicator via `adapter.indicate_processing()`
9. Execute via `TaskExecutionService` with restricted tools (default: `WebSearch,WebFetch` only)
10. Show completion indicator
11. Persist user + assistant messages in session
12. Send response via `adapter.send_response()`
13. Post-response hook via `adapter.on_response_sent()`

### Startup: `src/backend/main.py:355-385`

On backend startup:
1. Create `TelegramAdapter` and `TelegramWebhookTransport` instances
2. Call `transport.start()` (no-op for webhook transport)
3. Set transport reference on router module via `set_webhook_transport()`
4. Store transport on `app.state.telegram_transport`
5. **Webhook reconciliation**: If `public_chat_url` is set, iterate all bindings and call `register_webhook()` for each. This ensures webhooks are re-registered after backend restarts or URL changes.

On shutdown (`main.py:432-437`): calls `transport.stop()`.

## Data Layer

### Database Tables

Created by migration `telegram_bindings` in `src/backend/db/migrations.py:913-958`:

**`telegram_bindings`** — one bot per agent (1:1 mapping):
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| agent_name | TEXT UNIQUE | Links to agent |
| bot_token_encrypted | TEXT | AES-256-GCM via `CredentialEncryptionService` |
| bot_username | TEXT | e.g. `MyAgentBot` |
| bot_id | TEXT UNIQUE | Telegram bot user ID |
| webhook_secret | TEXT | `secrets.token_urlsafe(32)` — URL path component |
| webhook_url | TEXT | Full registered webhook URL |
| telegram_secret_token | TEXT | `secrets.token_urlsafe(32)` — header validation |
| last_update_id | INTEGER | For dedup (skip updates <= this) |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |

Indexes: `agent_name`, `bot_id`, `webhook_secret`

**`telegram_chat_links`** — tracks Telegram users per bot:
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| binding_id | INTEGER FK | References `telegram_bindings(id)` |
| telegram_user_id | TEXT | Telegram user ID |
| telegram_username | TEXT | Optional @username |
| session_id | TEXT | Public chat session reference |
| message_count | INTEGER | Incremented per message |
| created_at | TEXT | ISO timestamp |
| last_active | TEXT | ISO timestamp |

Unique constraint: `(binding_id, telegram_user_id)`

### Database Operations: `src/backend/db/telegram_channels.py`

`TelegramChannelOperations` class with methods:
- `create_binding()` — UPSERT with encrypted token, generates webhook_secret + telegram_secret_token
- `get_binding_by_agent()` / `get_binding_by_bot_id()` / `get_binding_by_webhook_secret()` — Lookups (token NOT decrypted)
- `get_decrypted_bot_token()` — Decrypts via `CredentialEncryptionService`
- `get_all_bindings()` — For webhook reconciliation on startup
- `update_webhook_url()` / `update_last_update_id()` — Field updates
- `delete_binding()` — Cascading delete of chat links + binding
- `get_or_create_chat_link()` — Upsert for Telegram user tracking
- `increment_message_count()` — Stats tracking

### Delegation: `src/backend/database.py:1296-1330`

The `Database` singleton delegates all Telegram operations to `TelegramChannelOperations`:
- `db.create_telegram_binding()` → `_telegram_channel_ops.create_binding()`
- `db.get_telegram_binding()` → `_telegram_channel_ops.get_binding_by_agent()`
- `db.get_telegram_binding_by_bot_id()` → `_telegram_channel_ops.get_binding_by_bot_id()`
- `db.get_telegram_binding_by_webhook_secret()` → `_telegram_channel_ops.get_binding_by_webhook_secret()`
- `db.get_telegram_bot_token()` → `_telegram_channel_ops.get_decrypted_bot_token()`
- `db.get_all_telegram_bindings()` → `_telegram_channel_ops.get_all_bindings()`
- `db.update_telegram_webhook_url()` → `_telegram_channel_ops.update_webhook_url()`
- `db.update_telegram_last_update_id()` → `_telegram_channel_ops.update_last_update_id()`
- `db.delete_telegram_binding()` → `_telegram_channel_ops.delete_binding()`
- `db.get_or_create_telegram_chat_link()` → `_telegram_channel_ops.get_or_create_chat_link()`
- `db.increment_telegram_message_count()` → `_telegram_channel_ops.increment_message_count()`

## Security

### Token Encryption
Bot tokens are encrypted at rest using AES-256-GCM via `CredentialEncryptionService` (same pattern as Slack tokens). The `_encrypt_token()` / `_decrypt_token()` methods in `TelegramChannelOperations` wrap the token in `{"bot_token": token}` before encryption.

### Webhook Authentication (dual layer)
1. **URL secret**: `webhook_secret` (32-byte URL-safe token) in the webhook URL path prevents enumeration
2. **Header secret**: `X-Telegram-Bot-Api-Secret-Token` header (separate 32-byte token) — Telegram sends this header with every update; transport validates it matches the stored `telegram_secret_token`

### SSRF Prevention
`telegram_media.py:71` — File download URLs are validated: `parsed.hostname` must equal `api.telegram.org`. This prevents a malicious file_path from redirecting downloads to internal services.

### Tool Restrictions
The message router restricts public channel users to `WebSearch,WebFetch` by default (configurable via `channel_allowed_tools` setting). No `Read`, `Bash`, `Write`, or `Edit` tools — prevents credential exfiltration from agent containers.

### Update Deduplication
`last_update_id` column prevents replay attacks. Updates with `update_id <= last_update_id` are silently dropped (`telegram_webhook.py:62-65`).

### Bot-Agent Uniqueness
- `agent_name` is UNIQUE in `telegram_bindings` — one bot per agent
- `bot_id` is UNIQUE — one agent per bot (checked at `routers/telegram.py:154`)

## Error Handling

| Error Case | HTTP Status | Message | Location |
|------------|-------------|---------|----------|
| Invalid token format | 400 | Invalid bot token format | `telegram.py:132` |
| Token fails getMe | 400 | Invalid bot token: {description} | `telegram.py:142` |
| Telegram API unreachable | 502 | Could not reach Telegram API | `telegram.py:151` |
| Bot bound to other agent | 409 | This bot is already bound to agent '{name}' | `telegram.py:157` |
| No binding found (DELETE) | 404 | No Telegram binding found | `telegram.py:198` |
| No binding found (test) | 404 | No Telegram binding found or token decryption failed | `telegram.py:220` |
| Unknown webhook_secret | 200* | `{"ok": false}` | `telegram_webhook.py:43` |
| Invalid header token | 200* | `{"ok": false}` | `telegram_webhook.py:49` |
| Rate limited by Telegram | Retry | Waits `retry_after` seconds (max 30s) | `telegram_adapter.py:236` |
| HTML parse failure | Retry | Falls back to plain text | `telegram_adapter.py:247` |
| Agent container not running | 200 | "I'm not available right now" | `message_router.py:143` |
| Task execution timeout | 200 | "That took too long" | `message_router.py:201` |

*Webhook always returns 200 to Telegram to prevent automatic retries.

## Testing

### Prerequisites
- Backend running (`./scripts/deploy/start.sh`)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- `public_chat_url` setting configured (Settings page → Platform section, or `PUT /api/settings/public_chat_url`)
- At least one agent running

### Test Steps

1. **Configure bot**
   **Action**: `PUT /api/agents/{agent}/telegram` with `{"bot_token": "123:ABC"}`
   **Expected**: 200 with `configured: true`, `bot_link: "https://t.me/..."`, webhook registered
   **Verify**: `GET /api/agents/{agent}/telegram` returns binding info

2. **Test bot connectivity**
   **Action**: `POST /api/agents/{agent}/telegram/test` with `{}`
   **Expected**: `{"ok": true, "bot_info": {...}}`

3. **Send message via Telegram**
   **Action**: Open `t.me/BotUsername`, send a text message
   **Expected**: Bot shows typing indicator, then responds with agent output
   **Verify**: Check backend logs for `[ROUTER:telegram]` entries

4. **Bot commands**
   **Action**: Send `/start`, `/help`, `/reset` in Telegram
   **Expected**: Each returns its formatted HTML response

5. **Duplicate bot prevention**
   **Action**: Try to bind the same bot to a different agent
   **Expected**: 409 Conflict

6. **Remove bot**
   **Action**: `DELETE /api/agents/{agent}/telegram`
   **Expected**: Webhook deleted from Telegram, binding removed from DB
   **Verify**: `GET /api/agents/{agent}/telegram` returns `configured: false`

## Frontend Layer

### Component: `src/frontend/src/components/TelegramChannelPanel.vue`

Self-contained panel rendered in the Agent Detail → Sharing tab via `SharingPanel.vue`. Mirrors the `SlackChannelPanel.vue` pattern.

**Props**: `agentName` (String, required)

**States**: `loading`, `connecting`, `disconnecting`, `verifying`, `accessDenied`

**Data model**:
```javascript
binding = {
  configured: boolean,
  bot_username: string,
  bot_id: string,
  webhook_url: string | null,
  bot_link: string | null
}
```

**UI States**:

| State | Display |
|-------|---------|
| Loading | Spinner |
| Access denied (403) | "Only the agent owner can manage..." |
| Disconnected | Token input (`type="password"`) + "Connect Bot" button + BotFather link |
| Connected | Green dot, `@bot_username`, t.me link, Verify + Disconnect buttons |
| Connected (no webhook) | Yellow warning: "Bot connected but webhook not registered..." with `router-link` to `/settings` |

**API calls** (via `api.js` — Invariant #7):
- `GET /api/agents/{name}/telegram` → load binding status
- `PUT /api/agents/{name}/telegram` → connect bot (sends `{ bot_token }`)
- `DELETE /api/agents/{name}/telegram` → disconnect bot
- `POST /api/agents/{name}/telegram/test` → verify bot (calls getMe)

**Security**:
- Token input is `type="password"` (masked in DOM)
- `botToken` ref cleared to `''` immediately on successful connect
- No `console.error(e)` that could leak token via axios error object
- Backend never returns token in GET response

**Error handling**:
- 409 → "This bot is already bound to agent '{name}'" (surfaces agent name from backend)
- 400 → Invalid token format or failed getMe validation
- 502 → Telegram API unreachable
- Generic fallback for unexpected errors

### Integration: `src/frontend/src/components/SharingPanel.vue`

TelegramChannelPanel is imported and rendered between the Slack and Public Links sections:

```vue
<SlackChannelPanel :agent-name="agentName" />
<div class="border-t ..."></div>
<TelegramChannelPanel :agent-name="agentName" />
<div class="border-t ..."></div>
<PublicLinksPanel :agent-name="agentName" />
```

## Related Flows
- [slack-integration.md](slack-integration.md) — Slack equivalent (SLACK-001)
- [slack-channel-routing.md](slack-channel-routing.md) — Channel adapter abstraction (SLACK-002)
- [public-agent-links.md](public-agent-links.md) — Web-based public chat (shares session/execution infrastructure)
- [task-execution-service.md](task-execution-service.md) — Unified execution path (EXEC-024)
