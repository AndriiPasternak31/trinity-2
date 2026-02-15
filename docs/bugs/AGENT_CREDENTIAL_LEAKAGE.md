# Security Bug: Environment Variable Exposure via Agent Tools

**Severity**: High
**Status**: Open
**Created**: 2026-02-13
**Affected Components**: Agent Execution, Logging, Database Persistence

## Description

Sensitive environment variables (including `TRINITY_MCP_API_KEY`, `OPENAI_API_KEY`, and custom credentials from `.env`) are being exposed in the `execution_log` stored in the database.

There are two exposure vectors:
1.  **Command Leak**: Agent executes `env` or `printenv` via Bash, dumping all secrets to stdout.
2.  **Direct Retrieval**: User asks "What is my API key?", and the agent reads the environment and outputs the secret in the conversation response.

In both cases, the secret is:
1.  Returned to the LLM (leaking secrets to the model provider).
2.  Persisted in the `execution_log` or `response` columns in the database (permanent internal leak).
3.  Displayed in the UI history.

## Evidence

**Verified on Production (2026-02-15):**
1.  **Vector 1 (env dump)**: Running "Check environment variables" resulted in a full dump of `.env` including `TRINITY_MCP_API_KEY`.
2.  **Vector 2 (Direct Ask)**: Execution `gr3Gv07...` showed the agent successfully retrieving and displaying a Fibery API token upon request.

Example leaked pattern:
```text
TRINITY_MCP_API_KEY=trinity_mcp_...
TRINITY_MCP_URL=http://mcp-server:8080/mcp
OPENAI_API_KEY=sk-...
```

## Impact

- **Credential Leak**: All agent credentials (API keys, tokens, secrets) are exposed to anyone with access to execution logs.
- **Model Exposure**: Keys are sent to the LLM provider as part of conversation history.
- **Persistent Risk**: Secrets remain in the database history even after rotation, unless logs are scrubbed.

## Reproduction Steps

### Vector 1: Command Leak
1.  **Start an Agent**: Run any agent.
2.  **Execute Command**: Instruct the agent to run a command that prints environment variables.
    *   Example: "Run `env`."
3.  **Check Result**: Secrets are visible in the tool output and database logs.

### Vector 2: Direct Retrieval
1.  **Ask Agent**: "What is my [CREDENTIAL_NAME]?" (e.g., "What is my Fibery token?").
2.  **Check Result**: Agent outputs the raw secret in the chat response.

## Remediation Plan (Suggestions)

1.  **Output Filtering (Primary Fix)**: Implement a filter in the Bash tool and Agent Client to detect and redact values matching known secrets. This must catch both tool output (stdout) and agent responses.
2. **Command Restriction**: Block or intercept `env`/`printenv` commands unless specifically allowed for debugging (hard to enforce perfectly).
3. **Log Sanitization**: Scrub sensitive patterns from `execution_log` before persistence.
4. **Secret Management**: Ensure secrets are injected only where needed, though environment variables are the standard 12-factor app pattern.

## QA Checklist & Verification

Use this checklist to verify the fix:

- [ ] **Vector 1 (env)**: Run "Run `env`".
  - [ ] Verify `TRINITY_MCP_API_KEY` is redacted in the logs (`***`).
- [ ] **Vector 2 (ask)**: Ask "What is my TRINITY_MCP_API_KEY?".
  - [ ] Verify the agent either refuses or the output is redacted in the logs/UI.
- [ ] **Database Check**: `SELECT execution_log FROM schedule_executions...` should not contain raw secrets.
- [ ] **Regression**: Ensure normal agent operations (which use these env vars internally) still work.
