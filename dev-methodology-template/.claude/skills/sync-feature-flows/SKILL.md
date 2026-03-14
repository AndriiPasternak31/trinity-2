---
name: sync-feature-flows
description: Analyze code changes and update affected feature flow documentation. Creates new flows for new features, updates existing flows for modified code.
allowed-tools: [Task, Read, Write, Edit, Grep, Glob, Bash]
user-invocable: true
argument-hint: "[commit-range|file-list|'recent']"
automation: gated
---

# Sync Feature Flows

Analyze code changes and synchronize feature flow documentation.

## Purpose

Keep feature flow documentation in sync with code changes by:
- Detecting which features were affected by recent changes
- Updating existing flow documents with new file paths, line numbers, endpoints
- Creating new flow documents for newly introduced features
- Maintaining a minimal, navigable index in feature-flows.md

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Feature Flows Index | `docs/memory/feature-flows.md` | ✅ | ✅ | Flow index (keep minimal) |
| Feature Flow Docs | `docs/memory/feature-flows/*.md` | ✅ | ✅ | Individual flow documents |
| Git History | `.git` | ✅ | | Recent changes |
| Changelog | `docs/memory/changelog.md` | ✅ | | Recent feature work |
| Source Code | `src/` | ✅ | | All source files |

## Arguments

- `$ARGUMENTS`:
  - `recent` or empty: Analyze last 5 commits
  - `HEAD~N..HEAD`: Specific commit range
  - `file1.py file2.vue`: Specific files to analyze

## Process

### Step 1: Identify Changed Files

```bash
# If 'recent' or no argument
git log --oneline -5 --name-only | grep -E '\.(py|vue|js|ts|tsx|jsx)$' | sort -u

# If commit range provided
git diff --name-only $ARGUMENTS | grep -E '\.(py|vue|js|ts|tsx|jsx)$'

# If file list provided
# Use the provided file list directly
```

Store the list of changed files.

### Step 2: Map Files to Features

Analyze changed files and map to feature flows by examining:
- Which existing flow documents reference these files
- Whether new endpoints/components were added
- Whether existing endpoints were modified

```bash
# Find which feature flows reference the changed files
grep -rl "changed-file-name" docs/memory/feature-flows/*.md
```

### Step 3: Check Existing Flows

For each identified feature:

```bash
# Check if flow document exists
ls docs/memory/feature-flows/{feature-name}.md 2>/dev/null
```

Categorize:
- **Needs Update**: Flow exists but code changed significantly
- **Needs Creation**: No flow exists for this feature
- **Up to Date**: Flow exists and changes are minor

### Step 4: Present Analysis

[APPROVAL GATE]

Present findings to user:

```
## Feature Flow Sync Analysis

### Changed Files
- path/to/file1.py (added/modified/deleted)
- path/to/file2.vue

### Affected Flows

**Needs Update** (existing docs with outdated info):
1. [feature.md] - file.py changed (lines 150-200)

**Needs Creation** (new features without docs):
1. [new-feature.md] - new endpoint detected

**Up to Date** (no action needed):
- existing-feature.md

Proceed with updates? [Y/n]
```

Wait for approval before making changes.

### Step 5: Spawn Feature Flow Analyzer

For each flow that needs update or creation:

```
Use the Task tool to spawn the feature-flow-analyzer agent:

Task(
  subagent_type: "feature-flow-analyzer",
  prompt: "Analyze and document/update the {feature-name} feature flow.

  Focus on these changed files:
  - {file1}
  - {file2}

  The flow document is at: docs/memory/feature-flows/{feature-name}.md

  IMPORTANT: When updating feature-flows.md index:
  - Add only ONE row to the appropriate table
  - Keep descriptions to ONE LINE
  - Put all details in the flow document itself, not the index"
)
```

Run agents sequentially to avoid conflicts in feature-flows.md.

### Step 6: Verify Index Size

After all updates:

```bash
wc -l docs/memory/feature-flows.md
```

If > 400 lines, the index may be bloated. Review and condense any verbose entries.

### Step 7: Report Completion

```
## Feature Flow Sync Complete

### Updated Flows
- [feature.md](docs/memory/feature-flows/feature.md) - Updated endpoints

### Created Flows
- [new-feature.md](docs/memory/feature-flows/new-feature.md) - New feature documented

### Index Status
- Lines: {count}
- Status: ✅ Minimal / ⚠️ Needs condensing
```

## Completion Checklist

- [ ] Changed files identified
- [ ] Files mapped to feature flows
- [ ] Existing flows checked
- [ ] Analysis presented (if manual)
- [ ] Feature-flow-analyzer spawned for each affected flow
- [ ] Index size verified (< 400 lines)
- [ ] Completion report generated

## Error Recovery

| Error | Recovery |
|-------|----------|
| Git not available | Fall back to file list from changelog |
| Flow document locked | Skip and report, try again later |
| Index too large | Run condensation pass before proceeding |
| Agent spawn fails | Log error, continue with remaining flows |

## Related Skills

- [feature-flow-analysis](../feature-flow-analysis/) - Manual single-flow analysis
- [update-docs](../update-docs/) - General documentation updates
