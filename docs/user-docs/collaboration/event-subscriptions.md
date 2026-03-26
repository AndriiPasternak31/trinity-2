# Event Subscriptions

Lightweight pub/sub system for inter-agent event pipelines. Agents emit named events, and subscribing agents receive async tasks with the payload.

## Concepts

- **Event** -- A named occurrence emitted by an agent with a structured JSON payload. Stored in the `agent_events` table.
- **Subscription** -- A rule that says "when agent X emits event type Y, send agent Z an async task with message template M". Stored in the `agent_event_subscriptions` table.
- **Message Template** -- Supports `{{payload.field}}` interpolation. The subscriber's task message is built from the event payload.
- **Permission-Gated** -- Uses existing `agent_permissions`. The subscribing agent must have permission to call the source agent.

## How It Works

1. Agent A emits an event: `emit_event(event_type="report_ready", payload={"url": "...", "summary": "..."})`
2. Trinity checks all subscriptions matching agent A + event type `report_ready`.
3. For each matching subscription, an async task is dispatched to the subscribing agent.
4. The task message is built from the subscription's template with payload fields interpolated.
5. Events are persisted and visible via API.
6. WebSocket broadcast provides real-time event visibility.

## For Agents

### MCP Tools

| Tool | Description |
|------|-------------|
| `emit_event(event_type, payload)` | Emit a named event with data |
| `subscribe_to_event(source_agent, event_type, message_template)` | Create a subscription |
| `list_event_subscriptions(agent_name)` | List subscriptions |
| `delete_event_subscription(subscription_id)` | Remove a subscription |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/event-subscriptions` | POST | Create subscription |
| `/api/agents/{name}/event-subscriptions` | GET | List subscriptions |
| `/api/event-subscriptions/{id}` | GET | Get by ID |
| `/api/event-subscriptions/{id}` | PUT | Update |
| `/api/event-subscriptions/{id}` | DELETE | Delete |
| `/api/events` | POST | Emit event (agent-scoped) |
| `/api/agents/{name}/emit-event` | POST | Emit for specific agent |
| `/api/agents/{name}/events` | GET | Event history |
| `/api/events` | GET | All events |

## See Also

- [Agent Permissions](agent-permissions.md)
- [Agent Network](agent-network.md)
