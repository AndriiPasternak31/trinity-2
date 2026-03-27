# Credential Management

Add, edit, and hot-reload credentials on agents without restarting them.

## Concepts

- **Credential Injection (CRED-002)** -- Direct file injection system. Credentials are written as `.env` (KEY=VALUE) and `.mcp.json` (generated from template) directly to the agent container.
- **Credential Requirements** -- Extracted from `.mcp.json.template`. The UI shows each credential as configured (green) or missing (red).
- **Encrypted Storage** -- Credentials can be exported to `.credentials.enc` files (AES-256-GCM encryption) for backup and import.

## How It Works

1. Open the agent detail page and click the **Credentials** tab.
2. View required credentials extracted from the agent's `.mcp.json.template`.
3. Status shows **configured** or **missing** per credential.
4. Add credentials using one of three methods:
   - **Manual entry** -- Name, value, and service fields.
   - **Bulk import** -- Paste `.env`-style KEY=VALUE pairs.
   - **From encrypted backup** -- Import a `.credentials.enc` file.
5. **Hot-reload** -- Paste or edit credentials on a running agent. The `.env` file is updated and `.mcp.json` is regenerated immediately. No restart needed.

### Credential Pattern in the Agent

```
.env                    # Source of truth (KEY=VALUE)
.mcp.json.template      # Template with ${VAR} placeholders
.mcp.json               # Generated at runtime from template + .env
```

### Export and Import

- **Export** creates an encrypted `.credentials.enc` file for backup.
- **Import** decrypts and injects credentials from an encrypted file.
- **Auto-import** runs on agent startup via `POST /api/internal/decrypt-and-inject`.

### Security

Credential values are never logged. All operations use structured logging with values masked.

## For Agents

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/credentials/status` | GET | Check credential files |
| `/api/agents/{name}/credentials/inject` | POST | Inject files directly |
| `/api/agents/{name}/credentials/export` | POST | Export to `.credentials.enc` |
| `/api/agents/{name}/credentials/import` | POST | Import from encrypted file |

### MCP Tools

- `get_credential_status(name)` -- Check credential file status.
- `inject_credentials(name, credentials)` -- Inject credentials into the agent.
- `export_credentials(name)` -- Export credentials to encrypted file.
- `import_credentials(name)` -- Import credentials from encrypted file.
- `get_credential_encryption_key()` -- Retrieve the encryption key.

## See Also

- [Agent Detail Page](../agents/agent-detail.md)
- [CRED-002 Feature Flow](../../memory/feature-flows/credential-injection.md)
