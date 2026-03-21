# SUB-003: Automatic Subscription Switching on Rate Limit

> **Requirement ID**: SUB-003
> **Extends**: SUB-002 (Subscription Management)
> **Priority**: HIGH
> **Status**: ⏳ Not Started

---

## Problem

When an agent hits a Claude subscription usage limit ("out of extra usage"), all scheduled and interactive executions fail with HTTP 429 until the subscription resets (often hours/days away). The user must manually notice the error, go to Settings, and reassign a different subscription. This is disruptive for autonomous agents that run on schedules.

## Requirements

### Preconditions (ALL must be true for auto-switch to trigger)

1. **Repeated failure**: The agent has encountered a subscription rate-limit error in **2 or more consecutive executions** (not just a single transient hit)
2. **Multiple subscriptions available**: There are **≥2 subscription credentials** registered in the system
3. **Setting enabled**: A system-level setting **"Allow automatic subscription switching"** is checked (opt-in, default OFF)

### Behavior

When all three preconditions are met:

1. **Select next subscription**: Pick an available subscription that is NOT the currently-assigned one. Selection strategy:
   - Prefer subscriptions with **fewer assigned agents** (load-balance)
   - Skip subscriptions that have **themselves been rate-limited recently** (within last 2 hours) to avoid cascading failures
   - If all alternatives are also rate-limited, do NOT switch — keep current and report the situation

2. **Switch subscription**: Call the existing `assign_subscription` flow (DB update + container restart with new `CLAUDE_CODE_OAUTH_TOKEN`)

3. **Log the switch**: Create a structured log entry and agent activity event:
   ```
   [SUB-003] Auto-switched agent "{agent_name}" from subscription "{old_sub}" to "{new_sub}"
   after {n} consecutive rate-limit errors
   ```

4. **Notify**: Send a notification (via existing notification system) to the agent owner so they're aware of the automatic switch

5. **Retry the failed execution**: After the switch, automatically retry the execution that triggered the switch (once only — no retry loops)

### Rate-Limit Tracking

- Track per-subscription rate-limit timestamps in the database (new table or column)
- Fields: `subscription_id`, `agent_name`, `error_message`, `occurred_at`
- A subscription is considered "rate-limited" if it has a rate-limit event within the last 2 hours
- Clean up tracking records older than 24 hours

### Settings UI

- Add a checkbox to **Settings → Subscriptions** section: **"Automatically switch subscriptions when usage limits are reached"**
- Below the checkbox, show helper text: _"When enabled, agents will automatically try a different subscription after 2 consecutive rate-limit errors. Requires at least 2 registered subscriptions."_
- Store as system setting: `auto_switch_subscriptions` (boolean, default `false`)

### Dashboard Visibility

- When an auto-switch occurs, show it in the agent's activity stream
- The agent header subscription badge should update to reflect the new subscription (already happens via existing WebSocket refresh)

---

## Technical Design Notes

### Where detection happens

Rate-limit errors are currently detected in **two places**:

1. **Agent container** (`docker/base-image/agent_server/services/claude_code.py`): `_is_rate_limit_message()` detects the error during execution and returns HTTP 429
2. **Backend** receives the 429 from agent container (or via schedule execution results)

The auto-switch logic should live in the **backend** since it needs access to the subscription registry and can coordinate across agents.

### Suggested flow

```
Agent container detects rate limit → returns 429 to caller
    ↓
Backend receives 429 (via schedule executor or chat proxy)
    ↓
Backend increments consecutive rate-limit counter for (agent, subscription)
    ↓
If counter ≥ 2 AND auto_switch enabled AND alternatives exist:
    ↓
Backend selects best alternative subscription
    ↓
Backend calls assign_subscription (existing flow — DB + container restart)
    ↓
Backend logs event, sends notification, retries execution
```

### Files likely to change

| Layer | File | Change |
|-------|------|--------|
| DB | `src/backend/db/subscriptions.py` | Add rate-limit tracking table/queries |
| DB | `src/backend/db/migrations.py` | New migration for tracking table + system setting |
| Service | `src/backend/services/subscription_service.py` | Auto-switch orchestration logic |
| Router | `src/backend/routers/subscriptions.py` | Setting endpoint, rate-limit tracking |
| Schedule | `src/backend/services/agent_service/schedule.py` | Hook into schedule execution failure path |
| Chat | Agent chat proxy (wherever 429 is received) | Hook into chat failure path |
| Frontend | `src/frontend/src/views/Settings.vue` | Add checkbox to Subscriptions section |
| MCP | `src/mcp-server/src/tools/subscriptions.ts` | Optional: expose setting via MCP |

### Edge cases

- **All subscriptions exhausted**: Log warning, do not switch, surface error to user as today
- **Agent has ANTHROPIC_API_KEY (not subscription)**: Auto-switch does not apply — only for subscription-based agents
- **Concurrent switches**: Use DB-level locking to prevent two agents from switching to the same subscription simultaneously
- **Rapid flip-flopping**: If an agent switches and the new subscription also hits a limit, the 2-consecutive-error requirement prevents immediate re-switch — it needs 2 more failures first, giving time for the original to reset

---

## Acceptance Criteria

- [ ] System setting `auto_switch_subscriptions` exists and defaults to OFF
- [ ] Settings UI shows checkbox with helper text in Subscriptions section
- [ ] Rate-limit errors are tracked per (agent, subscription) with timestamps
- [ ] After 2+ consecutive rate-limit errors, agent is auto-switched to a different subscription
- [ ] Rate-limited subscriptions (last 2 hours) are skipped during selection
- [ ] Auto-switch is logged as an activity event on the agent
- [ ] Notification is sent to agent owner on auto-switch
- [ ] Failed execution is retried once after successful switch
- [ ] No switch occurs if setting is disabled, only 1 subscription exists, or all alternatives are rate-limited
- [ ] Subscription badge in agent header updates after auto-switch
