# Dashboard

The main Dashboard at `/` provides a real-time agent network graph and timeline view for monitoring all agents and their activities.

## How It Works

### Graph View (default)

1. Shows all agents as draggable nodes in a network graph (Vue Flow).
2. Node colors indicate status: running (green), stopped (gray).
3. Animated edges appear when agents communicate (3-second animation).
4. Each node displays the agent name, avatar, success rate bar, and status indicator.
5. Drag nodes to rearrange -- positions persist in localStorage.
6. Host telemetry (CPU/memory/disk) is displayed in the header.
7. Capacity meter shows parallel execution slot usage.

### Timeline View

1. Toggle between Graph and Timeline via the mode switch.
2. Timeline shows execution boxes per agent, arranged chronologically.
3. Color-coded by trigger type: manual (blue), schedule (purple), MCP (orange), chat (green).
4. Collaboration arrows connect related executions between agents.
5. Live streaming: running executions show progress in real-time.
6. Time range filter: 1h, 6h, 24h, 7d, or custom.
7. Quick tag filters for focusing on specific agent groups.
8. Filter persistence: time range and tag selections persist across sessions.

### Tag Clouds

Agents are grouped visually by tags on the Dashboard. Click a tag cloud to filter the view to that group.

### Activity Feed

A real-time WebSocket-driven activity stream showing agent collaborations, task starts/completions, schedule executions, and errors.

## For Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List all agents |
| `/api/agents/context-stats` | GET | Context and activity state for all agents |
| `/api/agents/autonomy-status` | GET | Autonomy status for all agents |
| `/api/activities/timeline` | GET | Cross-agent activity timeline (filterable) |
| `/api/telemetry/host` | GET | Host CPU/memory/disk |

## See Also

- [Agent Detail](../agents/agent-detail.md)
- [Schedules](./schedules.md)
