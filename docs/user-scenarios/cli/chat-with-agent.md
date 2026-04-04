# Scenario: Chat with an Agent via CLI

**Persona**: User with at least one running agent on Trinity
**Goal**: Send messages to an agent, view responses, and check conversation history
**Interface**: CLI
**Prerequisites**:
- CLI installed and authenticated (`trinity status` shows "Connected")
- At least one agent running (`trinity agents list` shows status "running")

---

## Steps

### 1. Find the agent name

**Action**: List available agents
```bash
trinity agents list
```

**Expected result**: A table showing agent names, status, template, and type

### 2. Send a message

**Action**: Chat with the agent
```bash
trinity chat my-agent "What can you help me with?"
```

**Expected result**: The agent's response is printed to stdout as plain text

**Notes**:
- The message must be quoted if it contains spaces
- For JSON output: `trinity chat my-agent "hello" --format json`
- This is a synchronous call — it waits for the agent to respond

### 3. View conversation history

**Action**: Check past messages
```bash
trinity history my-agent
```

**Expected result**: A table of previous messages and responses for this agent

### 4. Check agent logs

**Action**: View the agent's container logs for debugging
```bash
trinity logs my-agent
trinity logs my-agent --tail 100
```

**Expected result**: Recent container log output (default: last 50 lines)

**Notes**: Useful for debugging when the agent isn't responding as expected

---

## Success Criteria

- `trinity chat <agent> "message"` returns a coherent response
- `trinity history <agent>` shows the conversation

## Error Scenarios

| Problem | Symptom | Resolution |
|---------|---------|------------|
| Agent not running | Connection error or empty response | Start the agent: `trinity agents start my-agent` |
| Agent name wrong | 404 error | Check exact name with `trinity agents list` |
| Agent unresponsive | Timeout or error | Check `trinity logs my-agent` for errors, verify agent has credentials configured |
| Not authenticated | HTTP 401 error | Run `trinity login` |

## Related

- [User docs: Agent Chat](../../user-docs/agents/agent-chat.md)
- [Scenario: Deploy Agent](deploy-agent.md) (to get an agent running first)
- CLI source: `src/cli/trinity_cli/commands/chat.py`
