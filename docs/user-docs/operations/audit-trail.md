# Audit Trail

Append-only log of administrative actions across the platform. Records who did what for compliance, incident investigation, and security monitoring.

## Concepts

| Term | Description |
|------|-------------|
| **Event type** | Category of action (agent_lifecycle, authentication, etc.) |
| **Actor** | Who performed the action (user, agent, system) |
| **Target** | What was affected (agent, user, schedule, etc.) |
| **Source** | Where the action originated (api, mcp, scheduler) |

## What Gets Logged

| Event Type | Actions |
|------------|---------|
| `agent_lifecycle` | create, start, stop, delete |
| `authentication` | login_success, login_failure, logout |
| `authorization` | permission_granted, permission_denied |
| `configuration` | settings_changed, quota_updated |
| `credentials` | injected, exported, imported |
| `mcp_operation` | tool_called (Phase 3) |
| `git_operation` | sync, pull, push |
| `system` | startup, shutdown, migration |

## Querying the Audit Log

**Admin only**: Use the API to query audit entries.

### List Entries

```bash
GET /api/audit-log?event_type=agent_lifecycle&limit=50
```

**Query parameters:**
- `event_type` — Filter by event type
- `actor_type` — Filter by actor (user, agent, system)
- `actor_id` — Filter by specific actor
- `target_type` — Filter by target type
- `target_id` — Filter by specific target
- `source` — Filter by source (api, mcp, scheduler)
- `start_time` — ISO 8601 timestamp
- `end_time` — ISO 8601 timestamp
- `limit` — Max results (default 100, max 1000)
- `offset` — Pagination offset

### Get Single Entry

```bash
GET /api/audit-log/{event_id}
```

### Get Statistics

```bash
GET /api/audit-log/stats?start_time=2026-04-01T00:00:00Z
```

Returns aggregate counts by event type and actor type.

## Entry Format

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "agent_lifecycle",
  "event_action": "create",
  "actor_type": "user",
  "actor_id": "42",
  "actor_email": "admin@example.com",
  "target_type": "agent",
  "target_id": "my-agent",
  "timestamp": "2026-04-14T10:30:00Z",
  "source": "api",
  "endpoint": "/api/agents",
  "details": {
    "template": "github:Org/repo"
  }
}
```

## Data Integrity

The audit log is append-only at the database level:
- **No updates**: Entries cannot be modified after creation.
- **No deletes**: Entries cannot be deleted within 365 days.
- SQLite triggers enforce these constraints.

## Limitations

- **No UI yet**: Query via API or Swagger (`/docs`).
- **Phase 1 coverage**: Agent lifecycle is fully logged. Other event types are being added progressively.
- **MCP logging**: TypeScript MCP tools will log in Phase 3.

## See Also

- [Monitoring](monitoring.md) — Health checks and system metrics
- [Executions](executions.md) — Task execution history
- [Authentication](../api-reference/authentication.md) — Auth flow details
