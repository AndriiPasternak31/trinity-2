# Scenario: First-Time CLI Setup

**Persona**: New user who has access to a Trinity instance (self-hosted or shared)
**Goal**: Install the CLI, authenticate, and verify the connection works
**Interface**: CLI
**Prerequisites**:
- Python 3.10+ installed
- A running Trinity instance (URL known)
- An email address whitelisted on that instance

---

## Steps

### 1. Install the CLI

**Action**: Install trinity-cli from PyPI
```bash
pip install trinity-cli
```

**Expected result**: `trinity` command is available in PATH

**Notes**: Also available via Homebrew: `brew install abilityai/tap/trinity`

### 2. Initialize and authenticate

**Action**: Run the init command and follow the prompts
```bash
trinity init
```

**Expected result**: The CLI prompts for three things in sequence:
1. **Trinity instance URL** — enter the instance URL (defaults to `http://localhost:8000`)
2. **Email** — enter your whitelisted email address
3. **6-digit code** — check your email for the verification code and enter it

On success, the CLI prints:
```
Connected to <url>
Access granted
Verification code sent to <email>
Logged in as <name> [profile: <hostname>]
MCP API key provisioned and saved to profile
MCP server config written to .mcp.json
Trinity CLI is ready. Try 'trinity agents list'.
```

**Notes**:
- `init` also requests access (auto-approved if email is whitelisted), so it works for brand-new users
- A profile is created automatically, named after the instance hostname
- An MCP API key is provisioned and `.mcp.json` is written to the current directory
- `.mcp.json` is auto-added to `.gitignore` (contains the API key)
- If the instance is unreachable, you get 3 retry attempts to correct the URL

### 3. Verify connection

**Action**: Check status and list agents
```bash
trinity status
trinity agents list
```

**Expected result**:
- `status` shows profile name, instance URL, user email, role, and "Connected"
- `agents list` returns a table of agents (or empty table if none exist yet)

---

## Success Criteria

- `trinity status` shows "Connected" and correct user info
- `trinity agents list` returns without error
- `~/.config/trinity/config.json` contains the saved profile

## Error Scenarios

| Problem | Symptom | Resolution |
|---------|---------|------------|
| Instance unreachable | "Cannot reach <url>" after 3 attempts | Verify the URL and that the instance is running |
| Email not whitelisted | "Access request failed" | Ask the instance admin to whitelist your email |
| Wrong verification code | "Verification failed" | Re-run `trinity login` to request a new code |
| Already initialized | Profile already exists | Use `trinity login` to re-authenticate, or `trinity profile use <name>` to switch |

## Related

- [User docs: Setup](../../user-docs/getting-started/setup.md)
- [User docs: Quick Start](../../user-docs/getting-started/quick-start.md)
- CLI source: `src/cli/trinity_cli/commands/auth.py`
