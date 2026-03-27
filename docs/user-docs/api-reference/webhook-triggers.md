# Webhook Triggers

External event triggers and internal execution endpoints for programmatic agent invocation.

**Note:** All endpoints require JWT Bearer token unless noted. See [Authentication](authentication.md) for details. Full request/response schemas available at [Backend API Docs](http://localhost:8000/docs).

## Endpoints

### Internal Execution (no auth -- internal network only)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/internal/execute-task` | POST | Execute task (used by scheduler, supports async_mode) |
| `/api/internal/decrypt-and-inject` | POST | Auto-import credentials on agent startup |

### Process Triggers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/processes/{id}/execute` | POST | Start process execution |

### Slack Events

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/public/slack/events` | POST | Slack event receiver |

### Event Emission

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/events` | POST | Emit event (triggers subscriptions) |
| `/api/agents/{name}/emit-event` | POST | Emit for specific agent |

**Note:** The `/api/internal/*` endpoints are not authenticated and should only be accessible within the Docker network. They are used by the scheduler service and agent containers.

## See Also

- [Authentication](authentication.md) -- JWT token usage and login flow
- [Agent API](agent-api.md) -- Agent lifecycle and configuration endpoints
- [Chat API](chat-api.md) -- Chat, voice, and streaming endpoints
- [Backend API Docs](http://localhost:8000/docs) -- Interactive Swagger documentation
