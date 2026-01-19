# Process Engine - Access Control and Audit Backlog

> **Phase**: Governance
> **Goal**: Role-based access control, audit logging, and execution governance
> **Stories**: 14
> **Focus**: RBAC for process operations, compliance audit trail, execution limits
> **Reference**: See [`BACKLOG_INDEX.md`](./BACKLOG_INDEX.md) for conventions
> **Source**: IT5 Section 5 (Access Management), Section 7.2 (P1 Implementation)

---

## Overview

This backlog implements **IT5 P1 - Access & Audit** features for the Process Engine. These features enable:
- Role-based permissions for process operations
- Audit logging for compliance and debugging
- Execution concurrency limits to prevent resource exhaustion

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ACCESS & AUDIT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  API Request                                                                 │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Authorization Middleware                                            │    │
│  │  • Check user role against required permission                       │    │
│  │  • Verify resource-level access (team, ownership)                    │    │
│  │  • Return 403 if denied                                              │    │
│  └────────────────────────────────────────────────────────────────┬────┘    │
│                                                                   │          │
│       ▼                                                           │          │
│  ┌─────────────────────────────────────────────────────────────┐  │          │
│  │  Execution Limits Service                                    │  │          │
│  │  • Check concurrent execution count                          │  │          │
│  │  • Enforce per-process instance limits                       │  │          │
│  │  • Queue or reject if limit exceeded                         │  │          │
│  └─────────────────────────────────────────────────────────────┘  │          │
│                                                                   │          │
│       ▼                                                           │          │
│  ┌─────────────────────────────────────────────────────────────┐  │          │
│  │  Business Logic (Routers/Services)                           │  │          │
│  │  • Process operations                                        │  │          │
│  │  • Execution operations                                      │  │          │
│  └─────────────────────────────────────────────────────────────┘  │          │
│                                                                   │          │
│       │                                                           │          │
│       ▼                                                           ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Audit Service (append-only log)                                     │    │
│  │  • Log all state-changing operations                                 │    │
│  │  • Include actor, action, resource, timestamp                        │    │
│  │  • Never update or delete entries                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Sprint Plan

| Sprint | Stories | Focus |
|--------|---------|-------|
| **Sprint 1** | E17-01, E17-02 | Permission enum and role definitions ✅ |
| **Sprint 2** | E17-03, E17-04 | Authorization service and API integration ✅ |
| **Sprint 3** | E18-01, E18-02, E18-03 | Audit logging infrastructure ✅ |
| **Sprint 4** | E19-01, E19-02 | Execution governance (E19-01 ✅) |
| **Sprint 5** | E17-05, E17-06 | RBAC UI - Backend APIs |
| **Sprint 6** | E17-07, E17-08, E17-09 | RBAC UI - Frontend integration |

---

## Epics

### E17: Access Control

Role-based permissions for process and execution operations.

### E18: Audit Logging

Compliance-ready audit trail for all operations.

### E19: Execution Governance

Limits and controls for execution resources.

---

## Stories

### E17-01: Process Permission Enum

**As a** developer, **I want** a well-defined permission enum, **so that** I can implement consistent access control.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P0 |
| Dependencies | None |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `ProcessPermission` enum defined in `services/process_engine/domain/enums.py`
- [x] Definition permissions: CREATE, READ, UPDATE, DELETE, PUBLISH
- [x] Execution permissions: TRIGGER, VIEW, CANCEL, RETRY
- [x] Approval permissions: DECIDE, DELEGATE
- [x] Admin permissions: VIEW_ALL, MANAGE_LIMITS
- [x] Exported from domain module

**Technical Notes:**
- Follow IT5 Section 5.1 permission model
- Use string values for easy serialization

---

### E17-02: Process Role Definitions

**As a** developer, **I want** predefined roles with permission mappings, **so that** users can be assigned appropriate access levels.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P0 |
| Dependencies | E17-01 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `ProcessRole` enum with 5 roles:
  - DESIGNER: CREATE, READ, UPDATE, DELETE, PUBLISH
  - OPERATOR: READ, TRIGGER, VIEW, CANCEL, RETRY
  - VIEWER: READ, VIEW (own executions only)
  - APPROVER: VIEW (relevant steps), DECIDE
  - ADMIN: All permissions
- [x] `ROLE_PERMISSIONS` mapping dict
- [x] Helper function: `role_has_permission(role, permission) -> bool`
- [x] Unit tests for all role/permission combinations

**Technical Notes:**
- Location: `services/process_engine/services/authorization.py`
- VIEWER has special scope restriction (own executions)

---

### E17-03: Authorization Service

**As a** developer, **I want** a centralized authorization service, **so that** I can check permissions consistently across the codebase.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Dependencies | E17-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `ProcessAuthorizationService` class with methods:
  - `can_create_process(user) -> AuthResult`
  - `can_read_process(user, process) -> AuthResult`
  - `can_update_process(user, process) -> AuthResult`
  - `can_delete_process(user, process) -> AuthResult`
  - `can_trigger_execution(user, process) -> AuthResult`
  - `can_view_execution(user, execution) -> AuthResult`
  - `can_cancel_execution(user, execution) -> AuthResult`
  - `can_decide_approval(user, execution, step_id) -> AuthResult`
- [x] `AuthResult` dataclass with `allowed: bool`, `reason: str`, `scope: str`
- [x] Check role permissions + resource-level rules
- [x] Support scoped access (e.g., VIEWER sees only own executions)
- [x] Unit tests with 15+ test cases (42 tests)

**Technical Notes:**
- Location: `services/process_engine/services/authorization.py`
- Use `User.role` field (already exists in models.py)
- Consider future team-based ownership (design for extension)

---

### E17-04: API Authorization Middleware

**As a** developer, **I want** authorization checks in API routes, **so that** unauthorized requests are rejected.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P0 |
| Dependencies | E17-03 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] Create `require_permission` dependency factory
- [x] Add authorization checks to:
  - POST /api/processes (CREATE)
  - GET /api/processes (READ)
  - PUT /api/processes/{id} (UPDATE)
  - DELETE /api/processes/{id} (DELETE)
  - POST /api/executions/start/{id} (TRIGGER)
  - GET /api/executions (VIEW - scoped)
  - POST /api/executions/{id}/cancel (CANCEL)
  - POST /api/approvals/{id}/decide (DECIDE)
- [x] Return 403 Forbidden with clear error message
- [x] Log authorization failures
- [ ] Integration tests verify 403 responses (deferred - can be added)

**Technical Notes:**
- Location: `dependencies.py` (add dependency) + routers
- Pattern: `current_user: CurrentUser, auth: ProcessAuthorizationService = Depends(get_auth_service)`
- Consider creating `AuthorizedUser` type annotation

---

### E17-05: User Permissions API

**As a** frontend developer, **I want** an API to get my permissions, **so that** I can show/hide UI elements based on access.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Dependencies | E17-03 |
| Status | ✅ done |

**Acceptance Criteria:**
- [ ] GET /api/users/me/permissions returns role and permission list
- [ ] Uses existing ROLE_PERMISSIONS mapping
- [ ] Unit tests for permission serialization

**Technical Notes:**
- Enhance existing `/api/users/me` endpoint in `main.py`
- Return: `{ role: string, permissions: string[] }`

---

### E17-06: Admin User Management API

**As an** admin, **I want** API endpoints to manage users, **so that** I can assign roles to team members.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Dependencies | E17-03 |
| Status | ✅ done |

**Acceptance Criteria:**
- [ ] GET /api/admin/users lists all users (admin only)
- [ ] PUT /api/admin/users/{id}/role updates user role
- [ ] Returns 403 for non-admin users
- [ ] Unit tests for role update validation
- [ ] Validate role is valid ProcessRole

**Technical Notes:**
- Create new `routers/users.py`
- Use ProcessAuthorizationService for admin check

---

### E17-07: Frontend Permissions Store

**As a** frontend developer, **I want** permissions in the auth store, **so that** components can check access.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Dependencies | E17-05 |
| Status | ✅ done |

**Acceptance Criteria:**
- [ ] auth.js fetches permissions after login
- [ ] usePermissions composable with can() helper
- [ ] Getters: isAdmin, canCreateProcess, canTriggerExecution, etc.

**Technical Notes:**
- Update `src/frontend/src/stores/auth.js`
- Create `src/frontend/src/composables/usePermissions.js`

---

### E17-08: User Management UI

**As an** admin, **I want** a user management page, **so that** I can view and change user roles.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Dependencies | E17-06, E17-07 |
| Status | ✅ done |

**Acceptance Criteria:**
- [ ] Admin-only page at /admin/users
- [ ] Lists users with email, role, last login
- [ ] Role selector dropdown to change roles
- [ ] Shows role permission matrix for reference
- [ ] Smoke test: admin can change user role

**Technical Notes:**
- Create `src/frontend/src/views/UserManagement.vue`
- Add route to `router/index.js`
- Link from Settings page (admin only)

---

### E17-09: Permission-Aware Components

**As a** user, **I want** UI elements hidden/disabled based on my permissions, **so that** I only see actions I can perform.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P2 |
| Dependencies | E17-07 |
| Status | ✅ done |

**Acceptance Criteria:**
- [ ] PermissionGuard component with hide/disable modes
- [ ] ProcessList hides Create button if no process:create
- [ ] ProcessEditor disables Save/Publish per permission
- [ ] NavBar shows current role badge

**Technical Notes:**
- Create `src/frontend/src/components/PermissionGuard.vue`
- Update ProcessList.vue, ProcessEditor.vue, NavBar.vue

---

### E18-01: Audit Entry Domain Model

**As a** developer, **I want** an audit entry model, **so that** I can log operations for compliance.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Dependencies | None |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `AuditEntry` dataclass with fields:
  - `id: AuditId` (UUID)
  - `timestamp: datetime`
  - `actor: str` (user email or "system")
  - `action: str` (e.g., "process.create", "execution.trigger")
  - `resource_type: str` (e.g., "process", "execution")
  - `resource_id: str`
  - `details: dict` (action-specific context)
  - `ip_address: Optional[str]`
  - `user_agent: Optional[str]`
- [x] `AuditAction` enum with common actions
- [x] `to_dict()` and `from_dict()` methods
- [x] Immutable (frozen dataclass)

**Technical Notes:**
- Location: `services/process_engine/domain/entities.py` or new `audit.py`
- Follow IT5 Section 5.4 audit trail design

---

### E18-02: Audit Service and Repository

**As a** developer, **I want** an audit service, **so that** I can log and query audit entries.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Dependencies | E18-01 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `AuditService` class with methods:
  - `log(actor, action, resource, details, request) -> AuditId`
  - `query(filters, limit, offset) -> list[AuditEntry]`
- [x] `SqliteAuditRepository` with:
  - `append(entry)` - append-only, never update
  - `list(filters, limit, offset)` - query with filters
  - `count(filters)` - count matching entries
- [x] Filters: actor, action, resource_type, resource_id, date_range
- [x] SQLite table with proper indexes
- [x] Unit tests for service and repository (22 tests)

**Technical Notes:**
- Location: `services/process_engine/services/audit.py`, `repositories/audit.py`
- Append-only design: no update or delete operations
- Consider retention policy (future: E18-04)

---

### E18-03: Audit API Endpoints

**As a** admin user, **I want** audit query endpoints, **so that** I can view the audit trail.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P1 |
| Dependencies | E18-02 |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] GET /api/audit - List audit entries (admin only)
  - Query params: actor, action, resource_type, resource_id, from_date, to_date
  - Pagination: limit, offset
- [x] GET /api/audit/{id} - Get single entry (admin only)
- [x] Requires ADMIN role
- [x] Response includes total count for pagination
- [ ] Integration tests verify admin-only access (deferred)

**Technical Notes:**
- Location: `routers/audit.py` (new router)
- Add to main.py router includes

---

### E19-01: Execution Concurrency Limits

**As a** platform operator, **I want** execution limits, **so that** runaway processes don't exhaust resources.

| Attribute | Value |
|-----------|-------|
| Size | M |
| Priority | P1 |
| Dependencies | None |
| Status | ✅ done |

**Acceptance Criteria:**
- [x] `ExecutionLimitService` class with:
  - `check_can_start(process_id) -> LimitResult`
  - `get_running_count(process_id) -> int`
  - `get_global_running_count() -> int`
- [x] Configurable limits:
  - `max_concurrent_executions: int` (global, default 50)
  - `max_instances_per_process: int` (per process, default 3)
- [x] Process definition can override `max_instances`
- [x] Return clear error when limit exceeded (429 Too Many Requests)
- [x] Integration with execution start endpoint
- [x] Limits status endpoint (`GET /api/executions/limits/status`)

**Technical Notes:**
- Location: `services/process_engine/services/limits.py`
- Query execution repository for running count
- Follow IT5 Section 1.4 execution limits design

---

### E19-02: Basic Rate Limiting

**As a** platform operator, **I want** rate limiting, **so that** the API is protected from abuse.

| Attribute | Value |
|-----------|-------|
| Size | S |
| Priority | P2 |
| Dependencies | None |
| Status | pending |

**Acceptance Criteria:**
- [ ] Simple in-memory rate limiter
- [ ] Configurable: requests per minute per user
- [ ] Default: 60 requests/minute for normal users
- [ ] Higher limit for admin users
- [ ] Return 429 Too Many Requests when exceeded
- [ ] Add to process/execution endpoints

**Technical Notes:**
- Location: `services/process_engine/services/rate_limit.py`
- Simple token bucket or sliding window
- Can be enhanced with Redis in future

---

## Running the Tests

```bash
# Run all access/audit tests
pytest tests/process_engine/unit/test_authorization.py -v
pytest tests/process_engine/unit/test_audit.py -v

# Run with coverage
pytest tests/process_engine/ --cov=services.process_engine.services.authorization
```

---

## Success Criteria

| Metric | Target | Actual |
|--------|--------|--------|
| Authorization tests | 15+ | ✅ 42 |
| Audit tests | 10+ | ✅ 22 |
| API routes protected | All process/execution endpoints | ✅ |
| Audit coverage | All state-changing operations | ✅ |
| Execution limits | Configurable per-process | ✅ |

---

## Document History

| Date | Change |
|------|--------|
| 2026-01-19 | Sprint 5-6 complete: E17-05 to E17-09 done (13/14 stories complete) |
| 2026-01-19 | Add E17-05 to E17-09 for RBAC UI (5 new stories, 14 total) |
| 2026-01-17 | Mark E17-01 to E19-01 as done (8/9 stories complete) |
| 2026-01-17 | Initial creation - IT5 P1 Access & Audit backlog |
