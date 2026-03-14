---
name: refactor-audit
description: Audit codebase for refactoring candidates. Identifies complexity issues, large files/functions, code duplication, and maintainability problems. Outputs report to docs/reports/.
disable-model-invocation: true
argument-hint: "[scope] [--quick]"
automation: manual
---

# Refactor Audit

Analyze code to identify refactoring candidates with complexity-based thresholds.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Source Code | `src/` | ✅ | | Files to analyze |
| Audit Report | `docs/reports/refactor-audit-{date}.md` | | ✅ | Generated report |

## Usage

```
/refactor-audit                    # Full src/ scan
/refactor-audit backend            # Only src/backend/
/refactor-audit frontend           # Only src/frontend/
/refactor-audit src/backend/app.py # Single file
/refactor-audit --quick            # Top 10 issues only
```

## Arguments

- `$ARGUMENTS` - Scope (backend/frontend/path) and flags

## Procedure

### Phase 1: Parse Arguments

Determine scope from `$ARGUMENTS`:
- Empty or "all" → `src/`
- "backend" → `src/backend/`
- "frontend" → `src/frontend/`
- Path (contains `/` or file extension) → use as-is
- "--quick" flag → limit to top 10 issues

### Phase 2: Run Analysis

Analyze the codebase for complexity issues:

#### For Python files:
```bash
# Find large files (>500 lines)
find [scope] -name "*.py" -exec wc -l {} \; | awk '$1 > 500 {print}'

# Cyclomatic complexity (if radon available)
radon cc -s -a --min C [scope]

# Dead code (if vulture available)
vulture [scope] --min-confidence 80
```

#### For JavaScript/TypeScript files:
```bash
# Find large files
find [scope] -name "*.js" -o -name "*.ts" -o -name "*.vue" -o -name "*.tsx" | xargs wc -l | awk '$1 > 400 {print}'
```

### Phase 3: Categorize Findings

Group issues by severity using these thresholds:

**P0 Critical** - Must fix:
- Files >1000 lines
- Functions >200 lines
- Cyclomatic complexity >30

**P1 High** - Strongly recommended:
- Files 800-1000 lines
- Functions 100-200 lines
- Cyclomatic complexity 20-30
- Significant duplication (>10 similar lines)

**P2 Medium** - Recommended:
- Files 500-800 lines
- Functions 50-100 lines
- Cyclomatic complexity 15-20
- Parameters >7
- Nesting depth >4

**P3 Low** - Nice to have:
- Files 300-500 lines
- Functions 30-50 lines
- Cyclomatic complexity 10-15
- Minor duplication (6-10 lines)

### Phase 4: Generate Report

Create report at `docs/reports/refactor-audit-YYYY-MM-DD.md`:

```markdown
# Refactor Audit Report

**Generated**: YYYY-MM-DD HH:MM
**Scope**: [scope analyzed]
**Tool**: /refactor-audit

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| P0 Critical | X | Must fix |
| P1 High | X | Strongly recommended |
| P2 Medium | X | Recommended |
| P3 Low | X | Nice to have |

**Total issues**: X

## Critical Issues

### [File Path]
| Issue | Metric | Line | Recommendation |
|-------|--------|------|----------------|
| Function too long | 187 lines | 234 | Extract into smaller functions |

## Hotspots (Files with Multiple Issues)

| File | Issues | Total Severity Score |
|------|--------|---------------------|
| file.py | 5 | 12 |

## Recommendations

### Quick Wins (Low Risk, High Impact)
1. ...

### Requires Tests First
1. ...
```

### Phase 5: Report Location

Save the report and confirm:

```
Report saved to: docs/reports/refactor-audit-YYYY-MM-DD.md

Found X issues:
- P0 Critical: X
- P1 High: X
- P2 Medium: X
- P3 Low: X

Top 3 hotspots:
1. [file] - X issues
2. [file] - X issues
3. [file] - X issues
```

## Completion Checklist

- [ ] Scope correctly parsed from arguments
- [ ] Analysis run (complexity, file sizes, duplication)
- [ ] Findings categorized by severity (P0-P3)
- [ ] Hotspots identified (files with multiple issues)
- [ ] Report saved to `docs/reports/`
- [ ] Summary output provided
