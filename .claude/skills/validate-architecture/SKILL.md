---
name: validate-architecture
description: Validate codebase against the 16 architectural invariants defined in architecture.md. Produces a pass/fail report.
allowed-tools: [Read, Grep, Glob, Bash, Agent]
user-invocable: true
---

# Validate Architecture

## Purpose

Check the codebase against the 16 Architectural Invariants in @docs/memory/architecture.md. Report violations with file paths and specific details. No changes are made — this is read-only analysis.

## Process

### Step 1: Load Invariants

Read the "Architectural Invariants" section from `docs/memory/architecture.md` to get the current list.

### Step 2: Validate Each Invariant

Run the checks below. For each invariant, record PASS or FAIL with evidence.

**1. Three-Layer Backend: Router → Service → DB**
- Grep `routers/*.py` for raw SQL (`execute(`, `cursor`, `SELECT`, `INSERT`, `UPDATE`, `DELETE`) — routers must not contain SQL
- Grep `routers/*.py` for business logic patterns (complex conditionals, loops over data) beyond simple request/response handling
- Grep `db/*.py` for HTTP-specific imports (`fastapi`, `Request`, `Response`) — db layer must not know about HTTP

**2. DB Layer: Class-per-domain with Mixin Composition**
- Glob `src/backend/db/*.py` and verify each defines an `*Operations` class
- Glob `src/backend/db/agent_settings/*.py` and verify each defines a `*Mixin` class
- Check that `AgentOperations` in `db/agents.py` uses mixin inheritance

**3. Schema in `db/schema.py`, Migrations in `db/migrations.py`**
- Grep all `src/backend/` files (excluding `schema.py` and `migrations.py`) for `CREATE TABLE` — should find none
- Verify `db/schema.py` and `db/migrations.py` both exist

**4. Router Registration Order**
- Read `src/backend/main.py` and find the `include_router` block
- Check that static agent routes (`context-stats`, `autonomy-status`) are registered before the main `agents` router with `/{name}` params

**5. Agent Server Mirrors Backend (Subset)**
- Glob `docker/base-image/agent_server/routers/*.py` and list them
- For each agent-server router, verify a corresponding backend router exists in `src/backend/routers/`
- Flag any agent-server router that has no backend counterpart

**6. Frontend: Store = Domain, View = Page**
- Grep `src/frontend/src/views/*.vue` for direct `api.get(`, `api.post(`, `api.put(`, `api.delete(` calls — views should go through stores
- Grep `src/frontend/src/views/*.vue` for `import api` or `import { api` — views should not import the API client directly

**7. Single API Client (`api.js`)**
- Grep `src/frontend/src/` for `new axios` or `axios.create` — should only be in `api.js`
- Grep `src/frontend/src/` for raw `fetch(` calls — should find none (except in non-API contexts like file downloads)

**8. Auth Pattern: `Depends(get_current_user)` + `AuthorizedAgent`**
- Grep `src/backend/routers/*.py` for route handlers (decorated with `@router.get`, `@router.post`, etc.)
- For each router file (except `internal.py`, `setup.py`, `auth.py`, `public.py`), verify at least one endpoint uses `get_current_user` or `AuthorizedAgent` or `OwnedAgentByName`
- Check that `internal.py` does NOT use `get_current_user`

**9. Channel Adapter ABC**
- Verify `src/backend/adapters/base.py` exists and defines `ChannelAdapter` class
- Check that adapter implementations (`slack_adapter.py`, etc.) inherit from `ChannelAdapter`

**10. Process Engine: DDD Isolation**
- Grep `src/backend/services/` (excluding `process_engine/`) for imports from `process_engine.domain` — should find none
- Grep `src/backend/routers/` for imports from `process_engine.domain` — should find none (routers should go through services)
- Verify step handlers in `process_engine/engine/handlers/` inherit from a base handler

**11. WebSocket Events for Real-Time**
- Grep `src/frontend/src/` for `setInterval` or `setTimeout` patterns that poll API endpoints — flag as potential violations (should use WebSocket instead)
- Verify `src/frontend/src/utils/websocket.js` exists

**12. Docker as Source of Truth**
- Grep `src/backend/` for container state stored in global variables or module-level dicts (e.g., `running_agents = {}`, `container_cache = {}`) — should not exist
- Verify `docker_service.py` exists as the Docker interaction point

**13. Credentials: File Injection, Never Stored in DB**
- Grep `db/schema.py` for any table that stores credential values (not references/metadata) — should find none
- Grep `src/backend/` for patterns that write credential values to SQLite

**14. MCP Server = Third Surface in Sync**
- Glob `src/mcp-server/src/tools/*.ts` and list tool modules
- Compare tool coverage against backend router domains — flag backend domains with no MCP tool coverage (informational, not all need MCP tools)

**15. Pydantic Models Centralized in `models.py`**
- Grep `src/backend/routers/*.py` for `class.*BaseModel` or `class.*Model(` definitions — models should be in `models.py`, not routers
- Count models in `models.py` vs scattered across other files

**16. API URL Nesting Convention**
- Grep `src/backend/routers/*.py` for `APIRouter(prefix=` and list all prefixes
- Flag any agent-scoped resource that doesn't nest under `/api/agents/{name}/`
- Flag any platform-wide resource that incorrectly nests under `/api/agents/`

### Step 3: Generate Report

Output a summary table:

```
## Architecture Validation Report

| # | Invariant | Status | Details |
|---|-----------|--------|---------|
| 1 | Three-Layer Backend | PASS/FAIL | ... |
| 2 | DB Mixin Composition | PASS/FAIL | ... |
...

**Result: X/16 PASS, Y/16 FAIL**

### Violations

#### [Invariant Name]
- **File**: path/to/file.py:line
- **Issue**: Description of violation
- **Fix**: Suggested remediation
```

## Outputs

- Markdown report printed to conversation
- No files created or modified
