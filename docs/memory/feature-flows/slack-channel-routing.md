# Channel Adapter Message Routing (SLACK-002)

> **Status**: Complete
> **Created**: 2026-03-23
> **Extends**: SLACK-001

## Overview

Pluggable channel adapter abstraction for external messaging platforms. Any incoming message follows the same pipeline: message → adapter → router → agent → response. Currently implemented for Slack; designed for Telegram, Discord, etc.

## Message Flow

```
External Platform (Slack, Telegram, etc.)
       │
       ▼
Transport Layer (Socket Mode / Webhook)
       │  Receives raw event, acknowledges immediately
       ▼
ChannelAdapter.parse_message(raw_event)
       │  Returns NormalizedMessage (sender, text, channel, thread, metadata)
       │  Returns None to skip (bot messages, unsupported types)
       ▼
ChannelMessageRouter.handle_message(adapter, message)
       │
       ├─ 1. adapter.get_agent_name(message)     → resolve which agent handles this
       ├─ 2. adapter.get_bot_token(team_id)       → get credentials for responses
       ├─ 3. _check_rate_limit(key)               → sliding window rate limit
       ├─ 4. get_agent_container(agent_name)       → verify agent is running
       ├─ 5. adapter.handle_verification(message)  → sender authorization
       ├─ 6. db.get_or_create_public_chat_session  → session persistence
       ├─ 7. db.build_public_chat_context           → chat history context
       ├─ 8. adapter.indicate_processing(message)   → ⏳ reaction (Slack)
       ├─ 9. TaskExecutionService.execute_task       → agent execution
       ├─ 10. adapter.indicate_done(message)         → ✅ reaction (Slack)
       ├─ 11. db.add_public_chat_message (x2)        → persist user + assistant msgs
       ├─ 12. adapter.send_response(channel, response) → deliver to channel
       └─ 13. adapter.on_response_sent(message, agent) → post-response hook
```

## Agent Resolution (Slack)

Priority order in `SlackAdapter.get_agent_name()`:

1. **Channel binding** — `slack_channel_agents` lookup by (team_id, channel_id)
2. **Active thread** — `slack_active_threads` lookup (reply-without-mention in existing thread)
3. **DM default** — `slack_channel_agents` where `is_dm_default = 1`
4. **Single agent** — If workspace has exactly one connected agent, use it
5. **Legacy fallback** — `slack_link_connections` from SLACK-001

## Rate Limiting

- In-memory sliding window per key (e.g., `slack:{team_id}:{sender_id}`)
- Configurable via `settings_service`:
  - `channel_rate_limit_max` (default: 30 messages)
  - `channel_rate_limit_window` (default: 60 seconds)
- Stale buckets pruned every 5 minutes to prevent memory leaks

## Security

- Public channel users restricted to configurable tool set (default: `WebSearch`, `WebFetch`)
- No file access (Read exposes .env/credentials), no Bash, no Write/Edit
- Execution timeout configurable via `channel_timeout_seconds` (default: 120s)
- Slack signature verification (HMAC-SHA256) on webhook transport
- Email verification for Slack users (auto-verify via profile or code)

## Configurable Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `channel_rate_limit_max` | 30 | Messages per rate limit window |
| `channel_rate_limit_window` | 60 | Window duration in seconds |
| `channel_timeout_seconds` | 120 | Max execution time per message |
| `channel_allowed_tools` | WebSearch,WebFetch | Comma-separated allowed tools for public users |

## Database Tables

- `slack_workspaces` — One row per connected workspace (team_id → bot_token)
- `slack_channel_agents` — Channel-to-agent bindings (supports multi-agent per workspace)
- `slack_active_threads` — Tracks threads where bot has responded (enables reply-without-mention)
- `public_chat_sessions` — Reused from web public chat (identifier_type = "slack")

## Entry Points

- **Transport**: `adapters/transports/slack_socket.py` — Socket Mode WebSocket
- **Adapter**: `adapters/slack_adapter.py` — Slack message parsing and response
- **Router**: `adapters/message_router.py` — Unified message pipeline
- **API**: `routers/slack.py` — OAuth, events webhook, connection management

## Related Flows

- [slack-integration.md](slack-integration.md) — SLACK-001: Original Slack DM integration
- [task-execution-service.md](task-execution-service.md) — EXEC-024: Unified execution lifecycle
- [public-agent-links.md](public-agent-links.md) — Public chat session persistence
