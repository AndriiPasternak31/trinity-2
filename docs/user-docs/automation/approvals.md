# Approvals

Human-in-the-loop approval gates for process engine workflows. Processes pause at approval steps and wait for human decisions before continuing.

## How It Works

1. A process execution reaches a `human_approval` step.
2. The step pauses the process (status: `PAUSED`).
3. An approval request appears in the **Approvals** inbox (accessible from the navigation bar).
4. The approver sees the process name, step description, context, and who requested it.
5. The approver can **Approve** or **Reject**, with an optional comment.
6. On approval, the process continues to the next step.
7. On rejection, the process execution is cancelled or follows the rejection path.
8. Approvals can have configurable timeouts.

A `approval_required` WebSocket event is fired when a process needs human approval.

## For Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/approvals` | GET | List pending approvals |
| `/api/approvals/{id}` | GET | Get approval details |
| `/api/approvals/{id}/decide` | POST | Submit decision (approve/reject) |

## See Also

- [Scheduling](scheduling.md) -- automated process triggers
- Approvals only apply to processes with `human_approval` step types defined in the process YAML.
