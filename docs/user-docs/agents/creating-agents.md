# Creating Agents

Agents are created from templates or from scratch. Each agent runs as an isolated Docker container with its own filesystem, credentials, and MCP server configuration.

## Concepts

**Template sources** define where agent blueprints come from:

- **GitHub Template** -- A repository in `github:Org/repo` format. Supports branch selection with `github:Org/repo@branch`. Private repos require a GitHub PAT.
- **Admin-Configured Templates** -- GitHub repos configured by an admin in Settings. Metadata (name, description, resources, MCP servers) is fetched from each repo's `template.yaml` via the GitHub API and cached for 10 minutes. These appear as cards on the Templates page (`/templates`).
- **Local Templates** -- Auto-discovered from the `config/agent-templates/` directory.
- **From Scratch** -- Creates a minimal agent with a default `CLAUDE.md`.

**Template structure** follows a standard layout:

| File | Purpose |
|------|---------|
| `template.yaml` | Agent metadata: `display_name`, `description`, `resources`, `credentials`, `runtime` |
| `CLAUDE.md` | Agent instructions and system prompt |
| `.mcp.json.template` | MCP config template with `${VAR}` placeholders for credential injection |
| `.env.example` | Example credentials file listing required environment variables |

**Runtime options** control which CLI the agent uses:

- `claude-code` (default)
- `gemini-cli` (set via `runtime.type` in `template.yaml`)

## How It Works

When you create an agent, Trinity performs these steps in order:

1. Template is cloned (GitHub) or copied (local/from-scratch).
2. `base_image` is validated against the allowlist. By default only `trinity-agent-base:*` is permitted. Admins can configure additional allowed images.
3. A Docker container is built from the base image.
4. Template files are copied into `/home/developer/` inside the container.
5. Credential requirements are extracted from `.mcp.json.template`.
6. If API subscriptions exist, one is auto-assigned via round-robin (fewest agents first).
7. The agent starts automatically.
8. The container is labeled for fleet management: `trinity.platform=agent`, `trinity.agent-name`, `trinity.agent-type`, `trinity.template`.

### UI Flow

1. Click **Create Agent** on the Dashboard or Agents page.
2. Select a template source. GitHub templates display as cards with metadata from `template.yaml`.
3. Enter an agent name (lowercase, hyphens only).
4. Click **Create**.

### API

```
POST /api/agents
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "my-agent",
  "template": "github:Org/repo@branch"
}
```

### MCP

```
create_agent(name="my-agent", template="github:Org/repo@branch")
```

## For Agents

Agents created from templates inherit:

- The `CLAUDE.md` from the template as their system prompt.
- MCP server configuration from `.mcp.json.template`, with `${VAR}` placeholders resolved at runtime from injected credentials.
- Any files in the template repository, copied to `/home/developer/`.

The agent's container is labeled so it can be discovered and managed by the platform. After creation, credentials can be injected and the agent can be started, stopped, or scheduled independently.

## Limitations

- Agent names must be unique, lowercase, with hyphens allowed. No spaces or special characters.
- The `base_image` must match the configured allowlist. Requests for blocked images return HTTP 403.
- Private GitHub repositories require a GitHub PAT to be configured before use as a template source.
- Template metadata from GitHub is cached for 10 minutes. Changes to `template.yaml` may not appear immediately.

## See Also

- [Credential Injection](../credentials/injecting-credentials.md) -- How credentials are supplied to agents
- [Agent Templates](../getting-started/templates.md) -- Browsing and managing templates
- [Scheduling](../automation/schedules.md) -- Running agents on a schedule
