# Development Workflow

> **For developers and AI assistants** working on this project.
> This guide explains how to use the project's tools, agents, and documentation effectively.

---

## The Development Cycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEVELOPMENT CYCLE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   1. CONTEXT LOADING                                                │
│      ↓                                                              │
│   /read-docs → Load requirements, architecture, roadmap             │
│      ↓                                                              │
│   Read relevant feature-flows/* for the area you'll work on         │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   2. DEVELOPMENT                                                    │
│      ↓                                                              │
│   /implement <source> → End-to-end automated implementation         │
│      ↓    OR                                                        │
│   Manual implementation following existing patterns                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   3. TESTING                                                        │
│      ↓                                                              │
│   test-runner agent → Run test suite (required)                     │
│      ↓                                                              │
│   Manual verification → UI/API tests (recommended)                  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   4. DOCUMENTATION                                                  │
│      ↓                                                              │
│   /sync-feature-flows → Update affected feature flows               │
│      ↓                                                              │
│   /update-docs → Update changelog, architecture, requirements       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   5. COMMIT & REVIEW                                                │
│      ↓                                                              │
│   /security-check → Pre-commit security validation                  │
│      ↓                                                              │
│   /commit → Stage, commit, push, link issues                        │
│      ↓                                                              │
│   /validate-pr → Validate PR meets all methodology requirements     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Context Loading

**Always start a development session by loading context.**

### Option A: Full Context Load (New Session)

Use the `/read-docs` skill:

```
/read-docs
```

This loads:
- `docs/memory/requirements.md` - Feature requirements (source of truth)
- `docs/memory/architecture.md` - System design
- GitHub Issues - Current priorities (P0/P1)
- `docs/memory/changelog.md` - Recent changes

### Option B: Targeted Context (Specific Feature Work)

If you know what you're working on, load the relevant feature flow directly:

```
# Example: Working on user authentication
@docs/memory/feature-flows/user-login.md

# Example: Working on data export
@docs/memory/feature-flows/data-export.md
```

### Available Feature Flows

See `docs/memory/feature-flows.md` for the complete index.

---

## Phase 2: Development

### Option A: Automated Implementation

Use `/implement` for end-to-end feature development:

```
/implement #42
/implement docs/requirements/new-feature.md
/implement "Add a user profile page with avatar upload"
```

This automatically:
1. Parses requirements
2. Studies existing patterns
3. Implements the feature
4. Creates and runs tests
5. Updates documentation

### Option B: Manual Development

#### Before Writing Code

1. **Check requirements**: Does `requirements.md` cover this feature?
2. **Check roadmap**: Is this the current priority? (`/roadmap`)
3. **Read feature flow**: Understand existing data flow before modifying

#### During Development

- Follow patterns established in existing code
- Reference feature flows for:
  - API endpoint locations
  - Database operations
  - Event handling
  - Error handling patterns

---

## Phase 3: Testing

**Every development session must include testing.**

### Run Test Suite

Use the `test-runner` agent:

```
Run the tests
```

This runs the test suite and reports:
- Pass/fail counts
- Failure analysis
- Recommendations

**Test Tiers:**
- **Smoke tests** (~1min): Quick validation
- **Core tests** (~5-15min): Standard validation (default)
- **Full suite** (~15+min): Comprehensive coverage

### Manual Verification

For quick checks during development:

```bash
# Application running?
curl http://localhost:8000/health

# Test specific endpoint
curl http://localhost:8000/api/endpoint
```

---

## Phase 4: Documentation

**After tests pass, update documentation.**

### If You Modified Feature Behavior

Use `/sync-feature-flows` to batch-update affected flows:

```
/sync-feature-flows recent
```

Or analyze a specific feature:

```
/feature-flow-analysis user-login
```

### For All Changes

Use `/update-docs`:

```
/update-docs
```

This determines which documents need updates:

| Document | When to Update |
|----------|----------------|
| `changelog.md` | Always - add timestamped entry |
| `architecture.md` | API changes, schema changes, new integrations |
| `requirements.md` | New features, scope changes |
| `feature-flows/*.md` | Behavior changes |

---

## Phase 5: Commit & Review

### Pre-Commit Security Check

```
/security-check
```

Scans staged files for:
- API keys and tokens
- Email addresses and IPs
- Hardcoded secrets
- Credential files

### Commit with Issue Linking

```
/commit closes #17
```

This stages files, creates a commit with proper formatting, pushes, and updates the GitHub issue status.

### PR Validation

```
/validate-pr 42
```

Validates:

| Category | Validation |
|----------|------------|
| **Changelog** | Entry exists with timestamp and emoji |
| **Requirements** | Updated if new feature or scope change |
| **Architecture** | Updated if API/schema/integration changes |
| **Feature Flows** | Created/updated for behavior changes, correct format |
| **Security** | No secrets, keys, emails, IPs in diff |
| **Code Quality** | Minimal changes, follows patterns |
| **Traceability** | Links to requirements |

---

## Skills Reference

### Core Workflow

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| `/read-docs` | Load project context | Start of session |
| `/update-docs` | Update documentation | After changes |
| `/commit [msg]` | Commit, push, link issues | When ready to commit |
| `/validate-pr <n>` | Validate PR against methodology | Before merging PRs |

### Feature Development

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| `/implement <source>` | End-to-end implementation | New features |
| `/feature-flow-analysis <name>` | Document feature flow | After modifying features |
| `/sync-feature-flows [range]` | Batch update flows | After code changes |
| `/add-testing <name>` | Add tests to flow | Improving coverage |

### Code Quality & Security

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| `/security-check` | Pre-commit secret scan | Before every commit |
| `/security-analysis [scope]` | Full OWASP audit | Periodic reviews |
| `/refactor-audit [scope]` | Complexity analysis | Code quality reviews |
| `/tidy [scope]` | Repository cleanup | Periodic maintenance |

### Project Management

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| `/roadmap [cmd]` | Query GitHub Issues | Check priorities |

---

## Sub-Agents Reference

### When to Use Each Agent

| Agent | Use When |
|-------|----------|
| `test-runner` | After development to validate changes |
| `feature-flow-analyzer` | After modifying feature behavior |
| `security-analyzer` | Before commits touching auth, credentials, or APIs |

### Invoking Agents

Agents are invoked automatically by Claude Code when appropriate, or you can request them:

```
# Run tests
Use the test-runner agent to run the tests

# Analyze a feature
Use the feature-flow-analyzer to document the user-login feature

# Security check
Use the security-analyzer to review the auth code
```

---

## Memory Files Explained

The `docs/memory/` directory contains persistent project state:

```
docs/memory/
├── requirements.md      ← SINGLE SOURCE OF TRUTH for features
├── architecture.md      ← Current system design (~1000 lines max)
├── roadmap.md           ← Prioritized task queue (optional, can use GitHub Issues)
├── changelog.md         ← Timestamped history (~500 lines)
├── feature-flows.md     ← Index of all feature flow documents
└── feature-flows/       ← Individual feature documentation
    ├── user-login.md
    ├── data-export.md
    └── ... (more flows)
```

### How They Work Together

```
requirements.md  ──defines──►  What features exist
       │
       ▼
GitHub Issues    ──prioritizes──►  What to work on next
       │
       ▼
feature-flows/*  ──documents──►  How features work
       │
       ▼
changelog.md     ──records──►  What changed and when
       │
       ▼
architecture.md  ──maintains──►  Current system state
```

---

## Example Development Sessions

### Scenario: Implement a New Feature

```
# 1. CONTEXT LOADING
You: /read-docs

# 2. DEVELOPMENT (automated)
You: /implement #42

# Claude automatically:
# - Reads the issue requirements
# - Studies existing patterns
# - Implements the feature
# - Runs tests
# - Updates documentation
# - Reports completion

# 3. COMMIT
You: /commit closes #42
```

### Scenario: Fix a Bug

```
# 1. CONTEXT LOADING
You: @docs/memory/feature-flows/data-export.md
You: The CSV export isn't including timestamps

# 2. DEVELOPMENT
Claude: [Reads flow, traces issue, implements fix]

# 3. TESTING
You: Test it
Claude: [Runs relevant tests, verifies fix]

# 4. DOCUMENTATION
You: /update-docs

# 5. COMMIT
You: /commit fixes #23 - timestamp column in CSV export
```

### Scenario: Code Quality Review

```
# Run complexity analysis
You: /refactor-audit backend

# Run security audit
You: /security-analysis

# Clean up repository
You: /tidy --report-only
```

---

## Best Practices

### DO

- ✅ Always load context before starting work
- ✅ Read feature flows before modifying features
- ✅ Run tests after every significant change
- ✅ Update feature flows when behavior changes
- ✅ Use sub-agents for specialized tasks
- ✅ Keep changelog entries concise but informative
- ✅ Run `/security-check` before every commit
- ✅ Run `/validate-pr` before approving any PR
- ✅ Use `/commit` for consistent commit messages
- ✅ Use `/implement` for new features

### DON'T

- ❌ Skip context loading ("I remember from last time")
- ❌ Modify features without reading their flow
- ❌ Commit without running tests
- ❌ Leave feature flows outdated after changes
- ❌ Write new documentation files without being asked
- ❌ Over-document - keep it minimal and useful
- ❌ Merge PRs without running validation
- ❌ Commit secrets or credentials

---

## Quick Start Checklist

For every development session:

- [ ] Load context (`/read-docs` or read relevant feature flows)
- [ ] Understand what you're modifying (read the feature flow)
- [ ] Implement changes
- [ ] Run tests (`test-runner` agent)
- [ ] Update feature flow if behavior changed (`/sync-feature-flows`)
- [ ] Update documentation (`/update-docs`)
- [ ] Run security check before commit (`/security-check`)
- [ ] Commit with issue link (`/commit`)

For PR reviews:

- [ ] Run `/validate-pr <number>` before approving
- [ ] Verify all Critical issues resolved
- [ ] Review Warnings with human judgment
- [ ] Approve only when report shows all ✅
