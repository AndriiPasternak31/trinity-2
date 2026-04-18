# Agent Sharing

Share agents with team members via email. Shared users get access to interact with the agent but cannot modify its configuration.

## How It Works

1. Open the agent detail page and click the **Sharing** tab (visible to the owner only).
2. Enter the email address of the person you want to share with.
3. Click **Share**. The email is automatically added to the platform whitelist.
4. The shared user can now see and interact with the agent (chat, tasks, view files).

### Proactive Messaging

Enable agents to send proactive messages (via Telegram, Slack, or web) to shared users:

1. In the Sharing tab, find the user in the shared list.
2. Toggle **Allow Proactive** to enable/disable proactive messaging for that user.
3. When enabled, the agent can initiate contact with that user without waiting for them to message first.

## Access Levels

| Level | Permissions |
|-------|-------------|
| **Owner** | Full control -- create, delete, configure, share, manage credentials and schedules. |
| **Shared** | Interact only -- chat, run tasks, view files and logs. Cannot modify config, credentials, or permissions. |
| **Admin** | Full access to all agents regardless of ownership. |

### Access Control Enforcement

- All API endpoints check ownership or sharing status before granting access.
- Shared users see only their own chat messages. Admins see all messages.
- Deleting an agent cascades to remove all associated sharing records.

## For Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/share` | POST | Share agent with an email address |
| `/api/agents/{name}/share/{email}` | DELETE | Remove a share |
| `/api/agents/{name}/shares` | GET | List all shares for an agent |

## See Also

- [Email Whitelist](../settings/email-whitelist.md) -- manage which emails can access the platform.
