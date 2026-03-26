# Agent Terminal

Browser-based xterm.js terminal providing direct access to the agent's Claude Code TUI, with mode switching between Claude, Gemini, and Bash.

## How It Works

1. Open the agent detail page and click the **Terminal** tab.
2. The terminal connects via WebSocket to the agent container's PTY.
3. The default mode is the Claude Code TUI (interactive AI assistant).
4. A mode toggle in the terminal header switches between **Claude**, **Gemini**, and **Bash**:
   - **Claude** -- Claude Code interactive mode.
   - **Gemini** -- Gemini CLI (requires `GEMINI_API_KEY` credential).
   - **Bash** -- Raw shell access to the agent container.
5. The terminal supports resize and adapts to the browser window dimensions.
6. Per-agent API key control: toggle between the platform API key and your own Claude subscription in the Terminal tab.

### SSH Access

- Generate ephemeral SSH credentials via the API or MCP.
- ED25519 keys with configurable TTL, controlled by ops settings.
- API: `POST /api/agents/{name}/ssh-access`
- MCP: `get_agent_ssh_access(name)`
- SSH ports: 2222-2262 (incrementing per agent).

### System Agent Terminal

- Admin-only browser terminal for the system agent (`trinity-system`).
- Accessible via the System Agent page.

## For Agents

Each agent container runs an SSH server and a PTY multiplexer. The browser terminal connects through the backend's WebSocket proxy -- agents do not need to expose ports directly. Mode switching restarts the PTY process inside the container without dropping the WebSocket connection.

## See Also

- [Creating Agents](creating-agents.md)
- [Managing Agents](managing-agents.md)
- [Agent Chat](agent-chat.md)
