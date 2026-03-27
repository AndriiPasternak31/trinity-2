# Scheduling

Cron-based automation for agents using APScheduler. Schedule recurring tasks with timezone support, execution history, and manual triggers.

## Concepts

- **Schedule** -- A cron expression paired with a message or task sent to an agent at the specified times.
- **Execution** -- Each time a schedule fires, it creates an execution record with status, duration, response, cost, and model used.
- **Autonomy Mode** -- Master toggle that enables or disables all schedules for an agent. Schedules will not fire if autonomy is off.
- **Scheduler Service** -- Standalone service with Redis distributed locks. Uses async fire-and-forget dispatch with DB polling for status.
- **Misfire Handling** -- If the scheduler restarts, missed jobs within a 1-hour grace window are caught up and fired immediately (`misfire_grace_time=3600`, `coalesce=True`, `max_instances=1`).

## How It Works

1. Open the agent detail page and go to the scheduling section.
2. Click **Create Schedule**.
3. Configure: name, cron expression (e.g., `0 9 * * 1-5` for weekdays at 9 AM), message/task, timezone, and description.
4. Optionally select a model override (Opus, Sonnet, Haiku, or custom).
5. Enable or disable individual schedules with the toggle.
6. View execution history with status, duration, and cost.
7. Click **Run Now** to trigger a schedule immediately.
8. Use the autonomy toggle to control all schedules at once.

### Execution Flow

1. Scheduler fires and sends a POST to `/api/internal/execute-task` with `async_mode=True`.
2. Backend spawns a background task and returns immediately.
3. Scheduler polls the database every 10 seconds until execution completes.
4. Execution record is updated with response, cost, and duration.

## For Agents

### MCP Tools

| Tool | Description |
|------|-------------|
| `list_agent_schedules(name)` | List schedules |
| `create_agent_schedule(name, ...)` | Create schedule |
| `get_agent_schedule(name, id)` | Get schedule details |
| `update_agent_schedule(name, id, ...)` | Update schedule |
| `delete_agent_schedule(name, id)` | Delete schedule |
| `toggle_agent_schedule(name, id)` | Enable or disable |
| `trigger_agent_schedule(name, id)` | Manual trigger |
| `get_schedule_executions(name, id)` | Execution history |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/schedules` | GET | List schedules |
| `/api/agents/{name}/schedules` | POST | Create schedule |
| `/api/agents/{name}/schedules/{id}` | GET/PUT/DELETE | CRUD operations |
| `/api/agents/{name}/schedules/{id}/enable` | POST | Enable schedule |
| `/api/agents/{name}/schedules/{id}/disable` | POST | Disable schedule |
| `/api/agents/{name}/schedules/{id}/trigger` | POST | Manual trigger |
| `/api/agents/{name}/schedules/{id}/executions` | GET | Execution history |

## Limitations

- Execution timeout is per-agent configurable (default 15 minutes, max 2 hours).
- Parallel execution is controlled by per-agent capacity slots (default 3).
- Missed jobs are only caught up within the 1-hour grace window.

## See Also

- [Agent Lifecycle](../agents/lifecycle.md)
- [Autonomy Mode](../agents/autonomy.md)
