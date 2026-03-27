# System Manifest

Recipe-based multi-agent deployment via YAML manifest files. Deploy entire agent teams with pre-configured permissions, shared folders, schedules, and auto-start.

## Concepts

- **System Manifest** -- A YAML file defining a set of agents, their templates, permissions, shared folders, and schedules. All agents in a manifest are deployed as a single unit.
- **System View** -- A saved filter/view in the UI that groups related agents by tags. Use system views to monitor and manage agents that belong to the same manifest.

## How It Works

1. Create a system manifest YAML file defining agents and their relationships.
2. Deploy via the `deploy_system` MCP tool or the REST API.
3. All agents are created, configured, and started according to the manifest.
4. Agents appear on the Dashboard with appropriate tags for grouping.

A manifest describes:

- A list of agents with name, template, and configuration.
- Permission presets (which agents can call which).
- Shared folder configuration for inter-agent file access.
- Schedule definitions for autonomous execution.
- Auto-start settings controlling which agents launch on deploy.

## For Agents

### MCP Tools

| Tool | Description |
|------|-------------|
| `deploy_system(manifest)` | Deploy a system from a manifest |
| `list_systems()` | List all deployed systems |
| `restart_system(name)` | Restart all agents in a system |
| `get_system_manifest(name)` | Retrieve the manifest for a deployed system |

### API Endpoints

See the [Backend API Docs](http://localhost:8000/docs) for full request/response schemas.

## See Also

- [Agent Network](agent-network.md) -- direct agent-to-agent communication
- [Agent Permissions](agent-permissions.md) -- controlling inter-agent access
