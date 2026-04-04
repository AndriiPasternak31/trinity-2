# Scenario: Deploy an Agent via CLI

**Persona**: Developer with a local Claude Code agent directory (has CLAUDE.md, skills, etc.)
**Goal**: Package the local directory and deploy it as a running agent on Trinity
**Interface**: CLI
**Prerequisites**:
- CLI installed and authenticated (`trinity status` shows "Connected")
- A local agent directory with at least a `CLAUDE.md` file
- The Trinity instance is running with Docker available

---

## Steps

### 1. Navigate to the agent directory

**Action**: cd into the agent repo
```bash
cd ~/my-agent
```

**Expected result**: You're in the root of the agent directory

**Notes**: The directory name becomes the default agent name (unless overridden or a `template.yaml` with a `name` field exists)

### 2. Deploy

**Action**: Run the deploy command
```bash
trinity deploy .
```

**Expected result**: The CLI packages the directory, uploads it, and creates the agent:
```
Packaging 'my-agent'...
Archive: 0.3 MB
Deploying 'my-agent'...
Agent 'my-agent' deployed (status: running)
Tracking file written: .trinity-remote.yaml
```

**Notes**:
- The archive excludes `.git`, `node_modules`, `__pycache__`, `.venv`, `.env` files, and anything in `.gitignore`
- Maximum archive size is 50 MB
- A `.trinity-remote.yaml` tracking file is written (auto-added to `.gitignore`)
- To override the agent name: `trinity deploy . --name custom-name`
- To deploy from a GitHub repo instead: `trinity deploy --repo user/repo`

### 3. Verify the agent is running

**Action**: Check the agent status
```bash
trinity agents list
trinity agents get my-agent
```

**Expected result**: The agent appears in the list with status "running"

### 4. Redeploy after changes

**Action**: Make changes to the agent code and redeploy
```bash
# Edit files...
trinity deploy .
```

**Expected result**: The CLI detects `.trinity-remote.yaml` and redeploys to the same agent:
```
Packaging 'my-agent'...
Archive: 0.3 MB
Redeploying 'my-agent'...
Agent 'my-agent' deployed (status: running)
  Previous version: my-agent-v1 (stopped: True)
  Version: my-agent-v2
```

**Notes**: The tracking file links this directory to a specific agent and instance, so subsequent deploys update the same agent automatically

---

## Success Criteria

- Agent appears in `trinity agents list` with status "running"
- `.trinity-remote.yaml` exists in the agent directory
- The agent is accessible via chat: `trinity chat my-agent "hello"`

## Error Scenarios

| Problem | Symptom | Resolution |
|---------|---------|------------|
| Not authenticated | HTTP 401 error | Run `trinity login` or `trinity init` |
| Archive too large | "Archive exceeds 50 MB limit" | Add large files to `.gitignore` or clean up the directory |
| Instance mismatch on redeploy | Warning about different instance | Confirm to deploy to current profile, or switch profiles with `trinity profile use <name>` |
| Docker not running on server | Deploy fails with container error | Ensure Docker is running on the Trinity instance |

## Related

- [User docs: Creating Agents](../../user-docs/agents/creating-agents.md)
- [Scenario: First-Time Setup](first-time-setup.md)
- CLI source: `src/cli/trinity_cli/commands/deploy.py`
