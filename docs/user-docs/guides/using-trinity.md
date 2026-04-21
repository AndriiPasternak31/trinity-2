# Using the Trinity Interface

A quick tour of the web UI — dashboard, agent management, chat, and day-to-day operations.

## Logging In

- **Admin login** — Enter username `admin` and the password set via `ADMIN_PASSWORD` in `.env` before first boot (self-hosted) or the one chosen at signup (cloud). There is no first-visit password wizard.
- **Email login** — Enter your email to receive a 6-digit code (requires email service configuration).

## Dashboard

The dashboard gives you a bird's-eye view of your agent fleet:

- **Network graph** — Visualizes agent-to-agent relationships and delegation flows.
- **Timeline** — Shows recent executions and agent activity.
- **Tag cloud** — Quick filtering by agent tags.
- **Quick actions** — Create agent, access Operating Room, view monitoring.

## Agent Management

Click any agent to open its detail page with tabs for:

| Tab | Purpose |
|-----|---------|
| **Chat** | Talk to your agent, view conversation history |
| **Schedules** | Cron jobs, trigger history, next run times |
| **Files** | Browse agent workspace, download files |
| **Config** | Credentials, permissions, autonomy settings |

Key actions:

- **Start/Stop** — Toggle agent container state.
- **Autonomy mode** — Enable/disable scheduled operations.
- **Terminal** — SSH-style access to the agent container.

## Creating Agents from the UI

Click **Create Agent** on the Dashboard or Agents page:

1. **Choose a source** — GitHub template, GitHub URL, or from scratch.
2. **Enter a name** — Lowercase with hyphens (e.g., `my-research-agent`).
3. **Create** — Trinity clones, builds, and starts the container.

## Operating Room

The Operating Room is your control center for real-time oversight:

- **Operator queue** — Actions waiting for human approval.
- **Notifications** — Agent alerts and status changes.
- **Cost tracking** — Per-agent API usage and spend alerts.

## Monitoring

The Monitoring page shows fleet health at a glance:

- **Health status** — Container state, last activity, resource usage.
- **Execution history** — Recent runs, success/failure rates.
- **Cleanup service** — Automatic orphan container cleanup.

## Settings (Admin Only)

The Settings page lets the admin configure:

- **Email whitelist** — Who can log in
- **GitHub templates** — Agent repos
- **API keys** — Platform access
- **Slack integration** — Workspace connection

## Next Steps

- [Building Agents](building-agents.md) — Create agents with Claude Code
- [Deploying Trinity](deploying-trinity.md) — Cloud and self-hosted setup

## See Also

- [Dashboard](../operations/dashboard.md) — Dashboard reference
- [Operating Room](../operations/operating-room.md) — Operator queue details
- [Monitoring](../operations/monitoring.md) — Health check configuration
