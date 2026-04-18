# Fan-Out (Parallel Task Dispatch)

Dispatch multiple independent tasks to an agent in parallel and collect all results. Useful for batch processing, parallel analysis, or ensemble methods.

## How It Works

Fan-out sends N tasks to an agent concurrently (up to a configurable limit), waits for all to complete or timeout, and returns aggregated results.

```
┌─────────────┐
│  Fan-Out    │
│  Request    │
└──────┬──────┘
       │
   ┌───┴───┬───────┬───────┐
   ▼       ▼       ▼       ▼
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│Task1│ │Task2│ │Task3│ │Task4│  (parallel, up to max_concurrency)
└──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
   │       │       │       │
   └───────┴───────┴───────┘
           │
     ┌─────┴─────┐
     │ Aggregate │
     │  Results  │
     └───────────┘
```

## For Agents

Fan-out is API/MCP-only — no UI. Agents use it to parallelize their own work.

### MCP Tool

```typescript
mcp__trinity__fan_out({
  agent_name: "my-agent",
  tasks: [
    { id: "q1", message: "Analyze Q1 revenue" },
    { id: "q2", message: "Analyze Q2 revenue" },
    { id: "q3", message: "Analyze Q3 revenue" }
  ],
  max_concurrency: 3,
  timeout_seconds: 300,
  model: "sonnet"
})
```

### REST API

```bash
POST /api/agents/my-agent/fan-out
```

**Request:**
```json
{
  "tasks": [
    {"id": "task-1", "message": "Analyze Q1 revenue"},
    {"id": "task-2", "message": "Analyze Q2 revenue"}
  ],
  "max_concurrency": 3,
  "timeout_seconds": 300,
  "model": "sonnet"
}
```

**Response:**
```json
{
  "fan_out_id": "fo_abc123def456",
  "status": "completed",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "results": [
    {
      "id": "task-1",
      "status": "completed",
      "response": "Q1 revenue was...",
      "execution_id": "exec_xyz",
      "cost": 0.05,
      "duration_ms": 8500
    },
    {
      "id": "task-2",
      "status": "completed",
      "response": "Q2 revenue was...",
      "execution_id": "exec_abc",
      "cost": 0.04,
      "duration_ms": 7200
    }
  ]
}
```

## Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `tasks` | — | 1-50 | Array of `{id, message}` objects |
| `max_concurrency` | 3 | 1-10 | Max parallel tasks |
| `timeout_seconds` | 600 | 10-3600 | Overall deadline |
| `model` | agent default | — | LLM model override |
| `policy` | best-effort | — | Only `best-effort` supported |

## Task IDs

Each task needs a unique ID (1-64 alphanumeric characters, dashes, underscores). Results are returned in input order with matching IDs.

## Timeout Handling

If the overall deadline is exceeded:
- `status` becomes `"deadline_exceeded"`
- Completed tasks have their results
- Unfinished tasks show `error_code: "timeout"`

## Observability

Each subtask creates its own execution record with:
- `triggered_by: "fan_out"`
- `fan_out_id: "fo_..."` (shared across all subtasks)

View in the Executions page or query via API.

## Limitations

- **Self-only**: Currently fan-out only works on the calling agent itself. Cross-agent fan-out is planned.
- **No UI**: API and MCP access only.
- **Capacity slots**: Each subtask consumes a parallel execution slot.

## See Also

- [Scheduling](scheduling.md) — Cron-based task automation
- [Executions](../operations/executions.md) — Viewing execution history
