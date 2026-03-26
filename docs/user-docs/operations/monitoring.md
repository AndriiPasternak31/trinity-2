# Monitoring

Multi-layer health monitoring for the agent fleet with real-time alerts, automatic cleanup of stuck resources, and a fleet-wide health dashboard.

## Concepts

**Health Levels** (ordered by severity):

| Level | Meaning |
|-------|---------|
| healthy | All checks passing |
| degraded | Minor issues detected |
| unhealthy | Significant problems |
| critical | Immediate attention required |
| unknown | Unable to determine status |

**Three Monitoring Layers:**

1. **Docker layer** -- Container status, CPU/memory usage, restart count, OOM detection.
2. **Network layer** -- Agent HTTP reachability with latency tracking.
3. **Business layer** -- Runtime availability, context usage, error rates.

**Alert Cooldowns:** Repeated alerts for the same condition are throttled to prevent notification spam.

## How It Works

### Fleet Health Dashboard

The fleet health dashboard is an admin-only view that summarizes the health of all agents in the system. It is accessible from the admin area of the UI.

- Real-time WebSocket updates push health state changes as they occur.
- Individual agent health is visible in both the agent header and the Agents listing page.

### Cleanup Service

A background service that automatically recovers stuck resources:

- **Stale executions** -- Any execution with `status='running'` for longer than 120 minutes is marked `failed`.
- **Stale activities** -- Any activity with `activity_state='started'` for longer than 120 minutes is marked `failed`.
- **Stale Redis slots** -- Orphaned slot reservations are released.
- **Run frequency** -- Every 5 minutes, plus a one-shot sweep on backend restart.
- **Startup recovery** -- Orphaned executions (container down, not in process registry) are marked `failed` immediately and their slots are released.

## For Agents

Agents can query monitoring data through these MCP tools:

| Tool | Description |
|------|-------------|
| `get_fleet_health()` | Fleet-wide health summary |
| `get_agent_health(name)` | Individual agent health |
| `trigger_health_check()` | Force an immediate health check |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/monitoring/fleet-health` | GET | Fleet health summary |
| `/api/monitoring/cleanup-status` | GET | Cleanup service status (admin) |
| `/api/monitoring/cleanup-trigger` | POST | Force a cleanup run (admin) |

## See Also

- [Dashboard](dashboard.md) -- Admin dashboard overview
- [Operating Room](operating-room.md) -- Real-time operations view
