# Development Workflow

> **For developers and AI assistants** working on this project.
> This guide defines Trinity's Software Development Lifecycle (SDLC) and explains how to use the project's tools, agents, and documentation effectively.

---

## Software Development Lifecycle (SDLC)

Trinity follows a 4-stage lifecycle that maps 1:1 to the **Trinity Roadmap** GitHub Project board columns.

```
 Todo → In Progress → Review → Done
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TRINITY SDLC                                     │
├──────────┬──────────────────────────────────────────────────────────┤
│          │                                                          │
│ TODO     │  Issue created, triaged with priority + type labels      │
│          │  Acceptance criteria defined before work begins           │
│          │  GitHub Project: Todo                                    │
│          │                                                          │
├──────────┼──────────────────────────────────────────────────────────┤
│          │                                                          │
│ IN       │  Developer assigned, feature branch created              │
│ PROGRESS │  Label: status-in-progress                               │
│          │  GitHub Project: In Progress                             │
│          │                                                          │
├──────────┼──────────────────────────────────────────────────────────┤
│          │                                                          │
│ REVIEW   │  PR opened, /validate-pr passes                          │
│          │  Code review approved, ready to merge                    │
│          │  GitHub Project: In Progress                             │
│          │                                                          │
├──────────┼──────────────────────────────────────────────────────────┤
│          │                                                          │
│ DONE     │  PR merged to main, issue closed                         │
│          │  Docs up to date                                         │
│          │  GitHub Project: Done                                    │
│          │                                                          │
└──────────┴──────────────────────────────────────────────────────────┘
```

### Prioritization

| Priority | Label | Meaning |
|----------|-------|---------|
| **P0** | `priority-p0` | Blocking/urgent — drop everything |
| **P1** | `priority-p1` | Critical path — current focus |
| **P2** | `priority-p2` | Important — next up |
| **P3** | `priority-p3` | Nice-to-have — when time allows |

Within P1, the **Tier** field on the project board provides sub-prioritization: **P1a** (highest) → **P1b** → **P1c**.

**Rule**: Work P0 first, then P1 by Tier (P1a → P1b → P1c), then by issue number (oldest first).

### Issue Types

| Label | Purpose |
|-------|---------|
| `type-feature` | New functionality |
| `type-bug` | Bug fix |
| `type-refactor` | Code improvement |
| `type-docs` | Documentation |

### Key Rules

- **All work on feature branches** — direct pushes to `main` are blocked (branch protection)
- **Every PR links to an issue** — use `Fixes #N` in the PR description
- **Assign yourself** when you start work on an issue
- **No merge without passing `/validate-pr`**

---

## Stage Details

### 1. Todo

Issues are created via GitHub issue templates (bug report or feature request). On creation:

1. Apply **priority** label (P0-P3)
2. Apply **type** label (feature/bug/refactor/docs)
3. Add to **Trinity Roadmap** project board (lands in Todo)
4. Add description with enough context to understand the problem
5. Define acceptance criteria (how do we know it's done?)

An issue is ready to pick up when it has a clear description, acceptance criteria, and no unresolved blockers (if blocked, apply `status-blocked` label).

### 2. In Progress

When picking up work:

1. **Assign yourself** to the issue
2. Apply `status-in-progress` label
3. Move to **In Progress** on the project board
4. Create a feature branch from `main`

#### Branch Convention

All work happens on feature branches. Direct pushes to `main` are blocked by branch protection.

**Naming**: `feature/<issue-number>-<short-slug>`
- Example: `feature/68-live-execution-output`

**Merge strategy**: Squash merge via PR with `Fixes #N`.

Then follow the development cycle:

#### Context Loading

Always start by loading context.

```
/read-docs
```

This loads requirements, architecture, and changelog. For targeted work, read the relevant feature flow directly:

```
@docs/memory/feature-flows/user-login.md
```

See `docs/memory/feature-flows.md` for the complete index.

#### Development

1. **Check requirements**: Does `requirements.md` cover this feature?
2. **Read feature flow**: Understand existing data flow before modifying
3. **Implement**: Follow patterns established in existing code
4. **Local testing**: Run tests and verify locally

```bash
# Health check
curl http://localhost:8000/health

# Run tests
# Use the test-runner agent
```

#### Documentation

After tests pass, update documentation:

```
/update-docs
```

| Change Type | Required Docs |
|-------------|---------------|
| Bug fix | `changelog.md` only |
| Feature / API change | `changelog.md` + `architecture.md` or `feature-flows/*.md` as needed |
| New capability | `changelog.md` + `requirements.md` + `feature-flows/*.md` |

### 3. Review

When local development is complete:

1. **Open a PR** — reference the issue with `Fixes #N`
2. **Verify locally** — test the feature on localhost
3. **For P0/P1 features** (recommended): deploy to dev server for additional validation

Run PR validation:

```
/validate-pr 42
```

**What gets validated:**

| Category | Check |
|----------|-------|
| **Changelog** | Entry exists with timestamp and emoji |
| **Requirements** | Updated if new feature or scope change |
| **Architecture** | Updated if API/schema/integration changes |
| **Feature Flows** | Created/updated for behavior changes |
| **Security** | No secrets, keys, emails, IPs in diff |
| **Code Quality** | Minimal changes, follows patterns |
| **Traceability** | Links to requirements and issue |

The validator produces a report with a recommendation: **APPROVE**, **REQUEST CHANGES**, or **NEEDS DISCUSSION**.

If changes are requested, the developer fixes and re-requests review. The reviewer runs `/validate-pr` again.

### 4. Done

When the PR is approved and merged:

1. Issue is **auto-closed** via `Fixes #N`
2. Move to **Done** on the project board
3. Remove status labels

---

## GitHub Project Board

**Trinity Roadmap** (GitHub Project #6) is the single view of all work.

| Column | Meaning |
|--------|---------|
| **Todo** | Backlog + Ready issues |
| **In Progress** | Actively being worked on |
| **Done** | Merged and shipped |

### Label ↔ Board Sync

Keep these in sync at all times:

| Stage | Label | Board Column |
|-------|-------|--------------|
| Todo | *(none)* | Todo |
| In Progress | `status-in-progress` | In Progress |
| Blocked | `status-blocked` | In Progress |
| Review | *(PR open)* | In Progress |
| Done | *(none)* | Done |

---

## Environments

| Environment | URL | Purpose |
|-------------|-----|---------|
| **Local** | `http://localhost` | Development and primary testing |
| **Dev Server** | *(configured separately)* | Optional pre-merge validation for P0/P1 features |

---

## Sub-Agents Reference

| Agent | Use When |
|-------|----------|
| `test-runner` | After development to validate changes |
| `feature-flow-analyzer` | After modifying feature behavior |
| `security-analyzer` | Before commits touching auth, credentials, or APIs |

Agents are invoked automatically by Claude Code when appropriate, or you can request them directly.

---

## Slash Commands Reference

| Command | Purpose | SDLC Stage |
|---------|---------|------------|
| `/read-docs` | Load project context | In Progress |
| `/update-docs` | Update documentation | In Progress |
| `/feature-flow-analysis <feature>` | Document feature flow | In Progress |
| `/security-check` | Validate no secrets in staged files | In Progress |
| `/add-testing` | Add tests for a feature | In Progress |
| `/validate-pr <number>` | Validate PR against methodology | Review |

---

## Memory Files

The `docs/memory/` directory contains persistent project state:

```
docs/memory/
├── requirements.md      ← SINGLE SOURCE OF TRUTH for features
├── architecture.md      ← Current system design (~1000 lines max)
├── changelog.md         ← Timestamped history (~500 lines)
├── feature-flows.md     ← Index of all feature flow documents
└── feature-flows/       ← Individual feature documentation
```

### How They Connect

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

## Development Skills

Skills in `.claude/skills/` define HOW to approach specific tasks:

| Skill | Principle | When |
|-------|-----------|------|
| `verification` | No "done" claims without evidence | Before saying "done" |
| `systematic-debugging` | Find root cause BEFORE fixing | When fixing bugs |
| `tdd` | Failing test first, then minimal code | When writing new code |
| `code-review` | Verify feedback technically first | When responding to PR comments |

---

## Quick Start Checklist

**For every development session:**

- [ ] Check GitHub Issues — pick the highest priority issue from Todo
- [ ] Assign yourself, apply `status-in-progress`, move to In Progress
- [ ] Create feature branch: `feature/<issue-number>-<slug>`
- [ ] Load context (`/read-docs` or read relevant feature flows)
- [ ] Implement changes
- [ ] Run tests (`test-runner` agent)
- [ ] Update documentation (see tiered doc requirements above)
- [ ] Open PR with `Fixes #N`, squash merge when approved
- [ ] Run `/validate-pr`

**For PR reviews:**

- [ ] Run `/validate-pr <number>`
- [ ] Verify all Critical issues resolved
- [ ] Approve only when report shows all pass
