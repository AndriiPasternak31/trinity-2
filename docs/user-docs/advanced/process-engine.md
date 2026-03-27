# Process Engine

BPMN-inspired workflow orchestration for multi-agent processes with approval gates, conditional branching, and analytics.

## Concepts

- **Process Definition** -- A YAML file defining steps, agents, and flow.
- **Process Execution** -- A running instance of a process definition.
- **Step Types** -- `agent_task`, `human_approval`, `gateway` (conditional), `timer`, `notification`, `sub_process`.
- **EMI Roles** -- Executor (performs work), Monitor (can intervene), Informed (notified).
- **Execution State Machine** -- `PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED` / `CANCELLED`, with `PAUSED` for approvals.

## How It Works (UI)

1. **Process List** (`/processes`) -- Browse and create process definitions.
2. **Process Wizard** -- Guided creation of process YAML.
3. **Process Editor** -- Edit process definition YAML directly.
4. **Execute** -- Publish a process, then start execution.
5. **Monitor** -- Real-time WebSocket events: `process_started`, `step_started`, `step_completed`, `step_failed`, `approval_required`.
6. **Process Dashboard** (`/process-dashboard`) -- Analytics, metrics, cost tracking, trends.
7. **Execution List** (`/executions`) -- All process executions.
8. **Approvals Inbox** -- Pending human approvals.

## Sub-Processes

Processes can call other processes. Parent-child linking is tracked with breadcrumbs in the UI.

## Process Templates

Bundled templates for common patterns are provided out of the box. Users can also create and save their own templates.

## API Endpoints

### CRUD

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/processes` | GET | List process definitions |
| `/api/processes` | POST | Create process definition |
| `/api/processes/{id}` | GET | Get process definition |
| `/api/processes/{id}` | PUT | Update process definition |
| `/api/processes/{id}` | DELETE | Delete process definition |

### Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/processes/{id}/publish` | POST | Publish a process definition |
| `/api/processes/{id}/execute` | POST | Start a new execution |

### Executions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/executions` | GET | List all executions |
| `/api/executions/{id}` | GET | Get execution details |
| `/api/executions/{id}/cancel` | POST | Cancel a running execution |

### Approvals

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/approvals` | GET | List pending approvals |
| `/api/approvals/{id}/decide` | POST | Approve or reject |

### Templates

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/process-templates` | GET | List process templates |
| `/api/process-templates` | POST | Create a process template |

### Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/processes/{id}/analytics` | GET | Process analytics and metrics |
| `/api/processes/{id}/trends` | GET | Process execution trends |

## See Also

- [Approvals](../automation/approvals.md)
- [Scheduling](../automation/scheduling.md)
- [Executions](../operations/executions.md)
