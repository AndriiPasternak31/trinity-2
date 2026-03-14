---
name: implement
description: End-to-end feature implementation from requirements to tests to documentation. Takes requirements file, GitHub issue, or description as input.
allowed-tools: [Task, Read, Write, Edit, Grep, Glob, Bash, Skill]
user-invocable: true
argument-hint: "<requirements-file|issue-number|'description'>"
automation: autonomous
---

# Implement Feature

End-to-end feature implementation from requirements to tested, documented code.

## Purpose

Autonomously implement features by:
1. Parsing requirements from file, GitHub issue, or inline description
2. Understanding existing patterns via feature flows
3. Implementing with minimal necessary changes
4. Creating and running tests
5. Updating documentation

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Requirements | `docs/requirements/*.md` | ✅ | | Feature specs |
| GitHub Issues | GitHub repo | ✅ | | Issue details |
| Feature Flows | `docs/memory/feature-flows/` | ✅ | | Existing patterns |
| Architecture | `docs/memory/architecture.md` | ✅ | | System design |
| Source Code | `src/` | ✅ | ✅ | Implementation |
| Tests | `tests/` | ✅ | ✅ | Test files |

## Arguments

- `$ARGUMENTS`:
  - File path: `docs/requirements/MY_FEATURE.md`
  - Issue number: `#42` or `42`
  - Inline description: `"Add endpoint for X that does Y"`

## Process

### Step 1: Parse Requirements

**If file path provided:**
```bash
cat "$ARGUMENTS"
```
Read and parse the requirements document.

**If issue number provided:**
```bash
gh issue view ${ARGUMENTS#\#} --json title,body,labels
```
Parse issue title, body, and labels for requirements.

**If inline description:**
Use the provided description directly as requirements.

**Extract:**
- Feature name/ID
- Core requirements (what must be built)
- Acceptance criteria (how to verify it works)
- Related features/flows (what to study first)

### Step 2: Study Existing Patterns

Read relevant feature flows to understand existing patterns:

```bash
ls docs/memory/feature-flows/*.md | head -20
```

Based on requirements, identify 2-4 related flows and read them:
- Similar features (e.g., if adding new page, read existing page flows)
- Same layer (e.g., if backend work, read similar endpoint flows)
- Integration points

Also read:
- `docs/memory/architecture.md` - for system context
- `CLAUDE.md` - for development rules

### Step 3: Plan Implementation

Create a mental implementation plan:

1. **Files to modify** - list specific files with line ranges
2. **Files to create** - new files needed
3. **Order of changes** - dependencies between changes
4. **Test strategy** - what tests to write

Apply best practices from CLAUDE.md:
- Minimal necessary changes only
- No unsolicited refactoring
- Follow existing patterns

### Step 4: Implement Feature

Execute implementation in order:

**Backend first (if applicable):**
1. Database schema/migrations (if needed)
2. Service layer logic
3. Router/controller endpoints
4. Models/schemas

**Frontend second (if applicable):**
1. Store/state management
2. Components
3. Views/routing

**Follow project patterns:**
- Use existing utility functions
- Match code style of surrounding code
- Add appropriate error handling

### Step 5: Create Tests

Create test files in `tests/` directory:

**Coverage targets:**
- Happy path (success case)
- Authentication/authorization
- Input validation
- Error cases
- Edge cases from requirements

### Step 6: Run Tests

Invoke the test-runner agent to execute tests:

```
Use Task tool:
  subagent_type: "test-runner"
  prompt: "Run tests for the newly implemented feature.

  Test file: tests/test_{feature_name}.py

  Report:
  - Total tests run
  - Passed/failed count
  - Any failure details with stack traces
  - Suggestions for fixes if failures occur"
```

### Step 7: Fix Test Failures

If tests fail:

1. **Analyze failure** - read error message and stack trace
2. **Identify root cause** - is it implementation bug or test bug?
3. **Fix the issue** - minimal change to resolve
4. **Re-run tests** - verify fix worked

Repeat until all tests pass.

**Max iterations:** 3 fix attempts. If still failing after 3 attempts, report status and stop.

### Step 8: Sync Feature Flows

Invoke sync-feature-flows to update documentation:

```
Use Skill tool:
  skill: "sync-feature-flows"
  args: "recent"
```

### Step 9: Update Documentation

Invoke update-docs to finalize:

```
Use Skill tool:
  skill: "update-docs"
```

### Step 10: Report Completion

Output final status:

```
## Implementation Complete: {Feature Name}

### Requirements Source
- {file/issue/description}

### Changes Made
**Backend:**
- `src/backend/xyz.py` - Added endpoint

**Frontend:**
- `src/frontend/xyz.vue` - New component

**Tests:**
- `tests/test_xyz.py` - {N} tests ({all passed/X failures})

### Documentation Updated
- Feature flow: `docs/memory/feature-flows/xyz.md`
- Changelog: Entry added
- Requirements: Status updated

### Verification
- [ ] Tests passing: ✅
- [ ] Feature flow created/updated: ✅
- [ ] Docs updated: ✅

### Next Steps
{Any manual verification needed}
```

## Completion Checklist

- [ ] Requirements parsed from input
- [ ] Related feature flows studied
- [ ] Implementation plan created
- [ ] Feature implemented
- [ ] Tests created
- [ ] Tests run via test-runner agent
- [ ] All tests passing (or max fix attempts reached)
- [ ] Feature flows synced via `/sync-feature-flows`
- [ ] Documentation updated via `/update-docs`
- [ ] GitHub issue updated (if issue number was provided)
- [ ] Completion report generated

## Error Recovery

| Error | Recovery |
|-------|----------|
| Requirements file not found | Ask for correct path or use inline description |
| GitHub issue not found | Verify issue number, check repo access |
| Test runner unavailable | Run tests directly |
| Tests fail after 3 fix attempts | Report current state, list remaining failures |
| Feature flow sync fails | Create flow manually using feature-flow-analysis |
| Backend not running | Report dependency, list manual test commands |

## Best Practices Enforced

From CLAUDE.md:
- **Minimal necessary changes** - only modify what's required
- **No unsolicited refactoring** - don't "improve" unrelated code
- **Follow existing patterns** - match code style
- **No over-engineering** - simplest solution that works

## Related Skills

- [read-docs](../read-docs/) - Load documentation context
- [sync-feature-flows](../sync-feature-flows/) - Update feature flows
- [update-docs](../update-docs/) - Update all documentation
- [feature-flow-analysis](../feature-flow-analysis/) - Manual flow creation
