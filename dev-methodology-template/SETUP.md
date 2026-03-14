# Setup Guide

Step-by-step instructions for integrating this development methodology into your project.

## Prerequisites

1. **Claude Code CLI** installed and configured
2. **Git repository** initialized
3. **Basic project structure** (source code, tests)

## Step 1: Copy Files

From your project root:

```bash
# Copy the .claude directory (skills and agents)
cp -r /path/to/dev-methodology-template/.claude .

# Copy the docs directory
cp -r /path/to/dev-methodology-template/docs .

# Copy the testing directory (optional)
cp -r /path/to/dev-methodology-template/testing .

# Copy the CLAUDE.md template
cp /path/to/dev-methodology-template/templates/CLAUDE.md.template CLAUDE.md

# Optionally copy the local config example
cp /path/to/dev-methodology-template/templates/CLAUDE.local.md.example CLAUDE.local.md
```

## Step 2: Configure CLAUDE.md

Open `CLAUDE.md` and replace all placeholders:

```markdown
# Find and replace these:
{{PROJECT_NAME}}        → Your Project Name
{{PROJECT_DESCRIPTION}} → What your project does
{{REPO_URL}}            → https://github.com/your-org/your-repo
{{BACKEND_URL}}         → http://localhost:8000
{{FRONTEND_URL}}        → http://localhost:3000
```

### Customize Sections

1. **Project Overview**: Update with your project's purpose
2. **Development Commands**: Add your project's build/run commands
3. **Key Files**: Update with your project's important file paths
4. **Project Structure**: Update the tree to match your layout

## Step 3: Initialize Memory Files

Remove the `.template` extension from memory files:

```bash
cd docs/memory
mv requirements.md.template requirements.md
mv architecture.md.template architecture.md
mv roadmap.md.template roadmap.md
mv changelog.md.template changelog.md
mv feature-flows.md.template feature-flows.md
```

Edit each file to add your project's initial state:

### requirements.md

Add your current features and planned features:

```markdown
## Implemented Features

### 1. User Authentication
**Status**: ✅ Complete
**Priority**: High
- [x] Login with email/password
- [x] Password reset flow
- [x] Session management
```

### architecture.md

Document your current stack:

```markdown
## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript |
| Backend | Node.js + Express |
| Database | PostgreSQL |
```

### roadmap.md

Add your current priorities:

```markdown
## Current Sprint

| Task | Status | Assignee |
|------|--------|----------|
| Add user profiles | 🚧 In Progress | Claude |
| Fix login bug | ⏳ Pending | - |
```

### changelog.md

Add your first entry:

```markdown
## Recent Changes

### 2025-01-08 10:00:00
🎉 **Initialized Development Methodology**
- Added Claude Code skills and agents
- Set up memory file structure
- Ready for disciplined development
```

## Step 4: Configure .gitignore

Add to your `.gitignore`:

```gitignore
# Claude Code local config (may contain secrets)
CLAUDE.local.md
.claude/settings.local.json
```

## Step 5: Customize Skills

Review and customize skills in `.claude/skills/`:

### read-docs/SKILL.md

Update file paths to match your project structure and add any project-specific docs to load.

### feature-flow-analysis/SKILL.md

Update layer references for your stack:

```markdown
# Replace generic references with your stack:
- Frontend: React components → Redux → API calls
- Backend: Express routes → Controllers → Database
```

### commit/SKILL.md

Update the Co-Authored-By line and any repo-specific references.

### roadmap/SKILL.md

The roadmap skill queries GitHub Issues. Make sure your repo uses priority labels (`priority-p0`, `priority-p1`, etc.) and type labels (`type-feature`, `type-bug`, etc.).

## Step 6: Customize Agents

Review and customize agents in `.claude/agents/`:

### test-runner.md

Update:
- Test suite location
- Test commands for each tier (smoke, core, full)
- Expected test count and duration

### feature-flow-analyzer.md

Update:
- Search patterns for your framework
- File path patterns
- Layer names and structure

### security-analyzer.md

Update:
- Framework-specific security checks
- Your security boundaries
- Report output path

## Step 7: Set Up GitHub Labels (Optional)

For full roadmap integration, create these labels in your GitHub repo:

```bash
# Priority labels
gh label create "priority-p0" --color "B60205" --description "Blocking/Urgent"
gh label create "priority-p1" --color "D93F0B" --description "Critical path"
gh label create "priority-p2" --color "FBCA04" --description "Important"
gh label create "priority-p3" --color "0E8A16" --description "Nice to have"

# Type labels
gh label create "type-feature" --color "0075CA" --description "New feature"
gh label create "type-bug" --color "D73A4A" --description "Bug fix"
gh label create "type-refactor" --color "CFD3D7" --description "Code refactoring"
gh label create "type-docs" --color "0075CA" --description "Documentation"

# Status labels
gh label create "status-ready" --color "0E8A16" --description "Ready to work on"
gh label create "status-in-progress" --color "FBCA04" --description "Being worked on"
gh label create "status-review" --color "D93F0B" --description "In review"
gh label create "status-blocked" --color "B60205" --description "Blocked"
```

## Step 8: First Run

Verify the setup:

```bash
# Start Claude Code
claude

# Load context
/read-docs

# You should see confirmation that docs were loaded
```

## Step 9: Create Your First Feature Flow

Test the methodology by documenting an existing feature:

```bash
/feature-flow-analysis user-login
```

This will create `docs/memory/feature-flows/user-login.md`.

## Verification Checklist

- [ ] CLAUDE.md has no `{{PLACEHOLDER}}` values remaining
- [ ] All memory files exist (no `.template` extension)
- [ ] `/read-docs` loads without errors
- [ ] Skills are accessible (try `/security-check`)
- [ ] Agents are accessible (ask "use the test-runner agent")
- [ ] `.gitignore` excludes local config files
- [ ] GitHub labels created (if using roadmap integration)

## Troubleshooting

### Skills not found

Ensure `.claude/skills/` is in your project root with `SKILL.md` files inside each skill directory.

### Memory files not loading

Check file paths in `read-docs/SKILL.md` match your actual structure.

### Agents not working

Verify YAML frontmatter is valid in agent files:

```yaml
---
name: agent-name
description: What it does
tools: Read, Grep, Glob
model: sonnet
---
```

## Next Steps

1. **Read the workflow guide**: `docs/DEVELOPMENT_WORKFLOW.md`
2. **Document existing features**: Use `/feature-flow-analysis`
3. **Add tests to flows**: Use `/add-testing`
4. **Establish the habit**: `/read-docs` at session start, `/update-docs` after changes
5. **Use `/implement`** for new features to get end-to-end automation
