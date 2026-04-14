# Feature: Execution Context Injection (#171)

## Overview
Every agent invocation receives a dynamic `## Execution Context` block in its
system prompt so it can self-calibrate behavior — knowing its mode (chat vs
headless task), trigger source, model, timeout budget, own name, permitted
collaborators, schedule metadata, and current timestamp. Implemented 2026-04-14
as an extension of the Trinity Prompt pipeline
([system-wide-trinity-prompt.md](system-wide-trinity-prompt.md)).

## Problem
Agents ran blind to operational metadata: they didn't know whether they were
in an interactive chat (where clarifying questions are fine) or an autonomous
task (where they should execute to completion), didn't know their timeout
budget, and didn't know who triggered them. This made it impossible for agents
to calibrate reasoning depth, plan work within a budget, or adjust behavior for
scheduled vs human-initiated runs.

## User Story
As an agent operator, I want the platform to tell each agent exactly which
mode and budget it is running in, so agents can behave correctly without
per-agent prompt engineering.

## Entry Points
- **Backend — chat (interactive)**: `src/backend/routers/chat.py` `/api/agents/{name}/chat`
- **Backend — task / schedule / mcp / agent / fan-out / paid / public**: `src/backend/services/task_execution_service.py` `execute_task()`
- **Backend — scheduler plumb-through**: `src/backend/routers/internal.py` `/api/internal/execute-task` (`InternalTaskExecutionRequest`)

## Context Block Format

```
## Execution Context

- **Mode**: chat | task
- **Triggered by**: schedule (source agent: 'orchestrator-1', user: 'alice@example.com')
- **Schedule**: 'daily-report' (cron: 0 9 * * *, next: 2026-04-15T09:00:00Z)
- **Attempt**: 1
- **Model**: claude-sonnet-4-6
- **Timeout**: 900s — plan to finish well within this budget
- **Agent**: oracle-1
- **Collaborators**: researcher-1, writer-1
- **Timestamp**: 2026-04-14T09:00:00Z
- **Platform**: https://your-domain.com

Autonomous execution. Do not ask clarifying questions — execute to completion
and return your results. Plan your work to finish well within the timeout budget.
```

Fields that don't apply are omitted (chat mode has no timeout; non-scheduled
runs have no schedule block; empty collaborators list is omitted entirely).

## Backend Layer

### Service: `services/platform_prompt_service.py`

Single source of truth for system prompt assembly (invariant #15). New surface:

| Symbol | Purpose |
|---|---|
| `ExecutionContext` (dataclass) | Typed per-invocation metadata. All fields optional. |
| `ExecutionContext.derive_mode(triggered_by)` | Maps trigger label → `"chat"` or `"task"`. |
| `build_execution_context(ctx) -> str` | Renders the markdown block. Returns `""` on any internal error so callers can fall back. |
| `compose_system_prompt(execution_context, caller_prompt, include_execution_context=True)` | Single composition entry point. Order: static platform instructions → execution context → caller prompt. |
| `is_execution_context_enabled()` | Operator kill-switch via `trinity_execution_context_enabled` setting (default true). |
| `_sanitize_field(value, max_len)` | Strips control chars, backticks, `##`, `---`; truncates. Applied to every user-controlled string before rendering. |

### Mode derivation

| `triggered_by` value | Mode |
|---|---|
| `chat`, `user`, `public`, `paid` | `chat` (interactive — agent may ask clarifying questions) |
| `schedule`, `mcp`, `agent`, `manual`, `fan_out`, other | `task` (autonomous — agent should execute and return) |

### Wiring

**`routers/chat.py` — interactive UI chat (mode=chat):**
```python
exec_ctx = ExecutionContext(
    agent_name=name,
    mode="chat",
    triggered_by=triggered_by,            # "chat" | "mcp" | "agent"
    source_user_email=current_user.email or current_user.username,
    source_agent_name=x_source_agent,
    source_mcp_key_name=x_mcp_key_name,
    model=request.model,
)
payload["system_prompt"] = compose_system_prompt(
    execution_context=exec_ctx,
    include_execution_context=is_execution_context_enabled(),
)
```

**`services/task_execution_service.py` — all headless execution paths:**
```python
exec_ctx = ExecutionContext(
    agent_name=agent_name,
    mode=ExecutionContext.derive_mode(triggered_by),
    triggered_by=triggered_by,
    source_user_email=source_user_email,
    source_agent_name=source_agent_name,
    source_mcp_key_name=source_mcp_key_name,
    model=model,
    timeout_seconds=timeout_seconds,
    attempt=attempt,
    schedule_name=(schedule_context or {}).get("name"),
    schedule_cron=(schedule_context or {}).get("cron"),
    schedule_next_run=(schedule_context or {}).get("next_run"),
)
effective_system_prompt = compose_system_prompt(
    execution_context=exec_ctx,
    caller_prompt=system_prompt,          # e.g. per-user memory block from public.py
    include_execution_context=is_execution_context_enabled(),
)
```

**`routers/internal.py` — scheduler plumb-through:**
`InternalTaskExecutionRequest` gained optional fields `schedule_name`,
`schedule_cron`, `schedule_next_run`, `attempt`. The dedicated scheduler may
pass them; when absent the schedule block is simply omitted (backwards
compatible — no scheduler update required to ship this).

### Auto-resolved fields

`compose_system_prompt` fills two fields from the DB when the caller leaves
them `None`, without mutating the caller's dataclass:

- `collaborators` → `db.get_permitted_agents(agent_name)` (from `agent_permissions` table)
- `platform_url` → `db.get_setting_value("public_chat_url")`

Both lookups are wrapped in try/except and degrade to empty / omitted on failure.

### Prompt Injection Defense

Schedule names and MCP key names are user-controlled and land verbatim in the
system prompt. Every rendered user-controlled string flows through
`_sanitize_field`, which:

1. Replaces control characters (`\x00–\x1f`, `\x7f`) — including newlines and tabs — with spaces
2. Replaces backticks with single quotes
3. Collapses `##` → `#` and `---` → `-` (neutralizes markdown heading injection)
4. Truncates to a per-field cap (80 chars default, 60 for collaborator names, 40 for timestamps, 200 for platform URL)

Covered by unit tests:
- `test_schedule_name_injection_attempt_neutralized`
- `test_mcp_key_name_injection_attempt_neutralized`
- `test_sanitize_field_neutralizes_markdown_injection`

### Failure Semantics

Every call site wraps context building in try/except and falls back to the
existing `get_platform_system_prompt()` alone on failure. Rendering errors
return an empty block. **The context builder never fails a request.**

## Operator Kill-Switch

Setting: `trinity_execution_context_enabled` (default `"true"`). Setting to
`"false"` / `"0"` / `"off"` disables the context block globally without a
redeploy. Lives alongside the existing `trinity_prompt` operator setting.

## Database

No schema changes. Reads from existing:
- `agent_permissions` (collaborators)
- `settings` (`public_chat_url`, `trinity_execution_context_enabled`)

## Out of Scope (Deferred)

- Context window size in prompt (needs agent-server cooperation)
- Parent execution chain for delegation trees (needs execution-tree query)
- Execution history summary for scheduled tasks
- Scheduler-side plumb-through of `schedule_name`/`cron`/`next_run` (separate PR; DB fallback ships today)

## Testing

`tests/test_platform_prompt_unit.py` — 41 unit tests covering:
- Sanitization (control chars, markdown heading injection, backticks, length cap, None/empty)
- Mode derivation for every trigger label
- Field rendering for chat/task/scheduled/agent/mcp/user triggers
- Collaborators (rendered / empty-omitted / truncated at MAX_COLLABORATORS)
- Prompt injection defense against adversarial schedule and MCP key names
- Builder error fallback (empty string on internal failure)
- `compose_system_prompt` ordering, collaborator auto-fill, kill-switch flag
- Operator kill-switch parsing for truthy/falsy setting values

Run: `.venv/bin/python -m pytest tests/test_platform_prompt_unit.py -v`

## Related Flows
- [system-wide-trinity-prompt.md](system-wide-trinity-prompt.md) — parent feature (admin-configurable platform instructions)
- [task-execution-service.md](task-execution-service.md) — primary wiring site
- [parallel-headless-execution.md](parallel-headless-execution.md) — headless task path
