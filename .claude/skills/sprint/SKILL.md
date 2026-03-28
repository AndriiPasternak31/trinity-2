---
name: sprint
description: Full development cycle — pick issue, plan review, implement, code review, sync docs, commit to feature branch, and create PR. Orchestrates /cso, /autoplan, /implement, /review, /validate-pr, /sync-feature-flows.
allowed-tools: [Agent, Bash, Edit, Glob, Grep, Read, Skill, Write, AskUserQuestion]
user-invocable: true
argument-hint: "[issue-number]"
automation: gated
---

# Sprint

Full development cycle from issue selection to pull request.

## Purpose

Automate the complete Trinity development workflow:
1. Select the highest-priority issue from the backlog
2. Validate requirements and acceptance criteria
3. Create a feature branch
4. Security audit (via `/cso --diff`) — optional, recommended for P0/P1
5. Plan review (via `/autoplan`) — strategy + eng + security review
6. Human reviews and approves the plan
7. Implement the feature (via `/implement`)
8. Pre-landing code review (via `/review`)
9. Verify tests exist and pass
10. Sync feature flow documentation (via `/sync-feature-flows`)
11. Process/docs validation (via `/validate-pr`)
12. Commit, push, and create a PR

## Pipeline Overview

```
/sprint X → /cso --diff → /autoplan → review → approve → /implement → /review → /validate-pr → /sync-feature-flows → PR
```

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| GitHub Project Board | `abilityai project #6` | ✅ | ✅ | Ranked issue pipeline |
| GitHub Issues | `abilityai/trinity` | ✅ | ✅ | Issue details, labels |
| Requirements | `docs/memory/requirements.md` | ✅ | ✅ | Feature requirements |
| Architecture | `docs/memory/architecture.md` | ✅ | ✅ | System design |
| Feature Flows | `docs/memory/feature-flows/` | ✅ | ✅ | Feature documentation |
| Changelog | `docs/memory/changelog.md` | ✅ | ✅ | Change history |
| Source Code | `src/`, `docker/base-image/` | ✅ | ✅ | Implementation |
| Tests | `tests/` | ✅ | ✅ | Test files |
| Git | `.git/` | ✅ | ✅ | Branches, commits |

## Arguments

- `$ARGUMENTS`:
  - Empty: Auto-select top issue from backlog (highest rank, P1a first)
  - Issue number: `#68` or `68` — work on a specific issue

## Prerequisites

- Git working tree is clean (`git status` shows no uncommitted changes)
- On `main` branch (or specify base branch)
- Docker running (if implementation touches containers)

## Process

### Step 1: Select Issue

**If issue number provided in `$ARGUMENTS`:**
```bash
gh issue view ${ARGUMENTS#\#} --repo abilityai/trinity --json number,title,body,labels,state
```

**If no argument — auto-select from backlog:**
```bash
# Get ranked P1 pipeline from Trinity Roadmap project
gh project item-list 6 --owner abilityai --format json --limit 20
```

Selection criteria (in order):
1. **Status = Todo** (skip Done, In Progress)
2. **Tier P1a first**, then P1b, then P1c
3. **Lowest rank number** within tier (rank 1 = highest priority)
4. Skip issues labeled `status-in-progress` or `status-blocked`

Present the selected issue to the user:

```
Selected: #[number] — [title]
Tier: [P1a/P1b/P1c]
Labels: [labels]

[First 5 lines of body]

Proceed with this issue?
```

**GATE: Wait for user approval before continuing.**

### Step 2: Validate Issue

Check the issue has enough detail to implement:

1. **Has acceptance criteria?** Look for `## Acceptance Criteria` or checkbox list
2. **Has scope?** Files to change, endpoints, components mentioned
3. **Has clear problem statement?** Summary or Problem section exists

If missing critical detail:
- Warn the user: "Issue #N is missing [acceptance criteria / scope / problem statement]. Proceed anyway or add detail first?"
- **GATE: Wait for user decision.**

### Step 3: Claim Issue & Create Branch

```bash
# Assign yourself and update labels
gh issue edit [NUMBER] --repo abilityai/trinity \
  --add-label "status-in-progress"

# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/[NUMBER]-[slug]
```

Branch naming: `feature/[issue-number]-[2-3-word-slug]`
- Example: `feature/68-live-execution-output`

### Step 4: Security Audit (P0/P1 recommended)

For P0 and P1 issues, run a security audit scoped to the branch changes:

```
/cso --diff
```

This checks: secrets archaeology, dependency supply chain, CI/CD pipeline, auth boundaries, and Trinity-specific security patterns on the changed files.

**For P2/P3 issues**: Ask the user if they want to run `/cso --diff` or skip.

**GATE: If critical findings, present them. User must acknowledge before proceeding.**

### Step 5: Plan Review

Run the auto-review pipeline:

```
/autoplan #[NUMBER]
```

This reviews the plan from 3 angles:
- **Strategy**: Is this the right approach? Premises valid? Scope calibrated?
- **Engineering**: Architecture sound? Edge cases? Test coverage?
- **Security**: New attack surface? Auth boundaries? Input validation?

Auto-decides intermediate questions using 6 decision principles. Surfaces taste decisions at the end.

**GATE: Wait for user to approve the autoplan output before implementing.**

### Step 6: Implement

Run the `/implement` skill with the issue number:

```
/implement #[NUMBER]
```

This handles:
- Reading requirements and existing patterns
- Implementing backend, frontend, and agent changes
- Writing initial tests
- Updating `requirements.md` if needed

### Step 7: Pre-Landing Code Review

Run the code review on the implementation:

```
/review
```

This catches structural issues tests miss: SQL safety, race conditions, auth boundary violations, scope drift, enum completeness.

**If critical findings**: Fix them before proceeding. The `/review` skill offers a fix-first flow.

### Step 9: Verify Tests

After `/implement` completes, explicitly verify tests were created:

```bash
# Check if new test files were created
git diff --name-only --diff-filter=A | grep -E "^tests/"

# Check if existing test files were modified
git diff --name-only | grep -E "^tests/"
```

**If no tests found:**
1. Identify what should be tested (new endpoints, services, edge cases)
2. Create test file: `tests/test_[feature].py`
3. Write tests following existing patterns (see `tests/` for examples)
4. Run the tests:
```bash
cd tests && source .venv/bin/activate && python -m pytest tests/test_[feature].py -v --tb=short 2>&1 | tail -30
```

**If tests exist, run them to verify they pass:**
```bash
cd tests && source .venv/bin/activate && python -m pytest tests/test_[feature].py -v --tb=short 2>&1 | tail -30
```

Fix any failures before proceeding.

### Step 10: Sync Feature Flows

Run the `/sync-feature-flows` skill to update documentation:

```
/sync-feature-flows recent
```

This handles:
- Detecting which feature flows are affected
- Updating existing flow documents
- Creating new flow documents if needed
- Updating the feature flows index

Also verify changelog was updated (should be done by `/implement`, but check):
```bash
head -20 docs/memory/changelog.md
```

If changelog was not updated, add an entry now following the existing format.

### Step 11: Commit, Push & Create PR

**Stage all changes:**
```bash
git add -A
git status
```

Review the diff to ensure:
- No secrets, credentials, or `.env` files
- No unrelated changes
- No debug artifacts (screenshots, test outputs)

**GATE: Present summary to user before committing.**

```
Ready to commit and create PR:

Issue: #[NUMBER] — [title]
Branch: feature/[NUMBER]-[slug]
Files changed: [count]
Tests: [count] new/modified test files
Docs: [list of updated flow docs]

Proceed?
```

Then commit and create PR:

```
/commit closes #[NUMBER]
```

After commit succeeds, push and create PR:

```bash
git push -u origin feature/[NUMBER]-[slug]
```

```bash
gh pr create --repo abilityai/trinity \
  --title "[type]: [short description] (#[NUMBER])" \
  --body "$(cat <<'EOF'
## Summary
[2-3 bullet points describing what was implemented]

## Changes
[List of key files changed]

## Test Plan
- [ ] New tests pass: `pytest tests/test_[feature].py -v`
- [ ] Existing tests unaffected
- [ ] Manual verification: [key steps]

Closes #[NUMBER]

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

The PR title prefix should match the change type:
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code restructuring
- `docs:` — documentation only

### Step 12: Final Status

Report completion:

```
Sprint complete:

Issue: #[NUMBER] — [title]
Branch: feature/[NUMBER]-[slug]
PR: [PR URL]
Tests: [pass/fail count]
Docs updated: [list]

Next steps:
- Review PR at [URL]
- Run /validate-pr [PR number] for merge readiness check
```

## Completion Checklist

- [ ] Issue selected and validated
- [ ] Feature branch created from latest main
- [ ] Security audit passed (via /cso --diff, P0/P1)
- [ ] Plan reviewed and approved (via /autoplan)
- [ ] Implementation complete (via /implement)
- [ ] Code review passed (via /review)
- [ ] Tests exist and pass
- [ ] Feature flows synced (via /sync-feature-flows)
- [ ] Changelog updated
- [ ] No secrets in diff
- [ ] Committed with issue reference
- [ ] PR created with summary

## Error Recovery

| Error | Recovery |
|-------|----------|
| No issues in backlog | Report "Backlog empty" and stop |
| Issue lacks detail | Ask user to add detail or skip to next issue |
| Implementation fails | Show error, ask user to intervene or skip |
| Tests fail | Fix failures before proceeding; if unfixable, note in PR |
| Branch already exists | Ask user: reuse, delete and recreate, or pick different issue |
| Merge conflicts | Rebase on main, resolve conflicts, continue |
| Push fails | Check remote, auth; retry or ask user |

## Self-Improvement

After completing this skill's primary task, consider tactical improvements:

- [ ] **Review execution**: Were there friction points, unclear steps, or inefficiencies?
- [ ] **Identify improvements**: Could error handling, step ordering, or instructions be clearer?
- [ ] **Scope check**: Only tactical/execution changes — NOT changes to core purpose or goals
- [ ] **Apply improvement** (if identified):
  - [ ] Edit this SKILL.md with the specific improvement
  - [ ] Keep changes minimal and focused
- [ ] **Version control** (if in a git repository):
  - [ ] Stage: `git add .claude/skills/sprint/SKILL.md`
  - [ ] Commit: `git commit -m "refactor(sprint): <brief improvement description>"`
