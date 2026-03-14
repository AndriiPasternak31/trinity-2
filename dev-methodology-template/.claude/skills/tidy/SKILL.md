---
name: tidy
description: Audit and clean up repository structure. Identifies outdated docs, misplaced files, orphan configs, and test artifacts. Reports findings first and requires approval before making changes (except safe artifacts).
disable-model-invocation: true
argument-hint: "[scope] [--report-only]"
automation: gated
---

# Repository Tidy Skill

Audit and clean up the repository structure without breaking code.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Requirements | `docs/memory/requirements.md` | ✅ | | Feature status |
| Feature Flows | `docs/memory/feature-flows.md` | ✅ | | Active flows |
| Root Files | Project root | ✅ | | Misplaced files |
| Docs Folder | `docs/` | ✅ | | Outdated docs |
| Config Folder | `config/` | ✅ | | Orphan configs |
| Tests Folder | `tests/` | ✅ | | Test artifacts |
| Archive | `archive/` | | ✅ | Archived files |

## Usage

```
/tidy                    # Full audit of all areas
/tidy docs               # Audit only docs/ folder
/tidy root               # Audit only root folder
/tidy tests              # Audit only tests/ folder
/tidy config             # Audit only config/ folder
/tidy --report-only      # Generate report without any changes
/tidy docs --report-only # Combine scope and report-only
```

## Core Principles

1. **Never break code** - Only touch non-code files (docs, configs, test artifacts)
2. **Report before action** - Always generate audit report first
3. **Archive over delete** - Move outdated files to `archive/` preserving structure
4. **Safe deletes are automatic** - `__pycache__`, `.pyc`, test outputs don't need approval
5. **Everything else needs approval** - Wait for explicit user confirmation

## Procedure

### Phase 1: Safe Cleanup (Automatic)

Delete these without asking (they're regenerable artifacts):
- `__pycache__/` directories
- `*.pyc`, `*.pyo` files
- `.DS_Store` files
- `*.log` files in non-essential locations
- `node_modules/.cache/`

Report what was cleaned.

### Phase 2: Audit by Scope

#### Root Folder Audit
Check for files that don't belong:
- Stray `.md` files (except README.md, CONTRIBUTING.md, LICENSE, CHANGELOG.md, CLAUDE.md)
- Config files that should be in `config/`
- Scripts that should be in `scripts/`
- Temporary or backup files

#### Docs Folder Audit
Cross-reference with project state:
- Read `docs/memory/requirements.md` for feature status
- Read `docs/memory/feature-flows.md` for active flows
- Identify docs for REMOVED features
- Find drafts that were never finalized

#### Tests Folder Audit
- Find orphan test outputs not in `.gitignore`
- Check for stale test fixtures
- Identify tests for removed features

#### Config Folder Audit
- Find unused config files
- Identify orphan configs

### Phase 3: Generate Report

```markdown
## Tidy Report - [DATE]

### Safe Cleanup Completed
| Type | Count | Space Freed |
|------|-------|-------------|

### Root Folder Issues
| File | Issue | Recommendation |
|------|-------|----------------|

### Documentation Issues
| File | Issue | Recommendation |
|------|-------|----------------|

### Config Issues
| File | Issue | Recommendation |
|------|-------|----------------|

### Test Artifact Issues
| File | Issue | Recommendation |
|------|-------|----------------|

### Recommended Actions
**Archive** (move to archive/ preserving structure):
- [ ] file1 - reason

**Relocate** (move to correct location):
- [ ] file1 -> new/location

**Delete** (truly orphan, no value):
- [ ] file1 - reason
```

### Phase 4: Wait for Approval

If `--report-only` was specified, stop here.

Otherwise, present the report and ask:
- "Which actions should I take? (all / archive only / specific items / none)"

### Phase 5: Execute Approved Changes

For approved items:
1. Create `archive/` directory if needed
2. Move files to `archive/` preserving original path structure
3. Relocate misplaced files to correct locations
4. Delete approved orphan files
5. Update any index files that reference moved files

## Exclusions (Never Touch)

- `.git/`
- `node_modules/`
- `.venv/`, `venv/`
- `__pycache__/` (auto-cleaned, not audited)
- `.claude/` (except for orphan detection)
- `archive/` (already archived)
- `*.db` files (databases)
- `.env*` files (secrets)

## Completion Checklist

- [ ] Safe artifacts cleaned (pycache, .pyc, .DS_Store)
- [ ] Audit report generated
- [ ] User approved changes (or --report-only)
- [ ] Archive directory structure preserved
- [ ] Index files updated if needed
- [ ] No code files touched
