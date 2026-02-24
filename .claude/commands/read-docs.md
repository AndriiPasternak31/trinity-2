# Read Project Documentation

Load all project documentation into context for this session.

## Instructions

1. Read these files in full (no summaries until all are loaded):
   - `docs/memory/requirements.md` - Feature requirements (SINGLE SOURCE OF TRUTH)
   - `docs/memory/architecture.md` - Current system design
   - `docs/memory/feature-flows.md` - Feature flow index
   - `docs/DEPLOYMENT.md` - Production deployment guide
   - `docs/TESTING_GUIDE.md` - Testing approach and standards

2. Query GitHub Issues for roadmap priorities:
   ```bash
   gh issue list --repo abilityai/trinity --label "priority-p0" --state open --json number,title,labels
   gh issue list --repo abilityai/trinity --label "priority-p1" --state open --json number,title,labels
   ```

3. Read changelog using Bash (file is 1200+ lines, only need recent entries):
   - Run: `head -150 docs/memory/changelog.md`
   - Do NOT use the Read tool for changelog - use Bash with head command

   Note: `CLAUDE.md` is loaded automatically at session start - no need to read it again.

4. Understand the current project state:
   - What features are implemented?
   - What's currently in progress?
   - What are the current priorities from GitHub Issues?

5. Report completion:
   ```
   Documentation loaded. Ready to work on Trinity.

   Top P0: [first P0 issue from GitHub]
   Top P1: [first P1 issue from GitHub]
   Recent Change: [most recent changelog entry]
   ```

## When to Use

- At the start of a new session
- When you need to understand the current project state
- Before starting work on a new task
- When switching between different areas of the codebase

## Principle

Load context first, then act. Never modify code without understanding the current state.
