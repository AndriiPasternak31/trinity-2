# Claude Code Development Methodology Template

A reusable development methodology kit for Claude Code projects. Provides skills (slash commands), sub-agents, memory files, and documentation templates to enforce disciplined, traceable development practices.

## What's Included

| Category | Contents |
|----------|----------|
| **Skills** | 13 slash commands: `/read-docs`, `/update-docs`, `/feature-flow-analysis`, `/add-testing`, `/security-check`, `/validate-pr`, `/commit`, `/implement`, `/roadmap`, `/refactor-audit`, `/tidy`, `/sync-feature-flows`, `/security-analysis` |
| **Agents** | 3 sub-agents: `feature-flow-analyzer`, `test-runner`, `security-analyzer` |
| **Memory Files** | Templates for requirements, architecture, roadmap, changelog, feature flows |
| **Workflow** | Development cycle documentation and testing guide |
| **Testing** | Phase-based testing framework templates |

## Quick Start

### 1. Copy to Your Project

```bash
# From your project root
cp -r path/to/dev-methodology-template/.claude .claude
cp -r path/to/dev-methodology-template/docs docs
cp path/to/dev-methodology-template/templates/CLAUDE.md.template CLAUDE.md
```

### 2. Configure Placeholders

Edit `CLAUDE.md` and replace:

| Placeholder | Replace With |
|-------------|--------------|
| `{{PROJECT_NAME}}` | Your project name |
| `{{PROJECT_DESCRIPTION}}` | One-line description |
| `{{REPO_URL}}` | GitHub repository URL |
| `{{BACKEND_URL}}` | API URL (e.g., `http://localhost:8000`) |
| `{{FRONTEND_URL}}` | Web UI URL (e.g., `http://localhost:3000`) |

### 3. Initialize Memory Files

```bash
# Remove .template extension and fill in initial content
cd docs/memory
for f in *.template; do mv "$f" "${f%.template}"; done
```

Edit each file to add your project's initial state.

## Directory Structure

```
your-project/
├── CLAUDE.md                    # Project instructions (from template)
├── CLAUDE.local.md              # Local/private config (gitignored)
├── .claude/
│   ├── skills/                  # Slash commands (skills)
│   │   ├── read-docs/SKILL.md
│   │   ├── update-docs/SKILL.md
│   │   ├── feature-flow-analysis/SKILL.md
│   │   ├── add-testing/SKILL.md
│   │   ├── security-check/SKILL.md
│   │   ├── validate-pr/SKILL.md
│   │   ├── commit/SKILL.md
│   │   ├── implement/SKILL.md
│   │   ├── roadmap/SKILL.md
│   │   ├── refactor-audit/SKILL.md
│   │   ├── tidy/SKILL.md
│   │   ├── sync-feature-flows/SKILL.md
│   │   └── security-analysis/SKILL.md
│   ├── agents/                  # Sub-agents
│   │   ├── feature-flow-analyzer.md
│   │   ├── test-runner.md
│   │   └── security-analyzer.md
│   └── settings.local.json      # Claude Code settings
└── docs/
    ├── DEVELOPMENT_WORKFLOW.md  # Development cycle guide
    ├── TESTING_GUIDE.md         # Testing philosophy
    └── memory/                  # Persistent project state
        ├── requirements.md      # Source of truth for features
        ├── architecture.md      # Current system design
        ├── roadmap.md           # Prioritized task queue
        ├── changelog.md         # Timestamped history
        ├── feature-flows.md     # Feature flow index
        └── feature-flows/       # Individual flow documents
```

## Development Cycle

This methodology enforces a 5-phase development cycle:

```
1. CONTEXT LOADING    →  /read-docs
       ↓
2. DEVELOPMENT        →  /implement or manual coding
       ↓
3. TESTING            →  test-runner agent
       ↓
4. DOCUMENTATION      →  /update-docs, /sync-feature-flows
       ↓
5. PR VALIDATION      →  /validate-pr (before merge)
```

See `docs/DEVELOPMENT_WORKFLOW.md` for details.

## Skills Reference

### Core Workflow

| Skill | Purpose |
|-------|---------|
| `/read-docs` | Load project context at session start |
| `/update-docs` | Update changelog, architecture, requirements after changes |
| `/commit [message]` | Stage, commit, push, and link to GitHub Issues |
| `/validate-pr <number>` | Validate PR against methodology and generate merge report |

### Feature Development

| Skill | Purpose |
|-------|---------|
| `/implement <source>` | End-to-end feature implementation from requirements to docs |
| `/feature-flow-analysis <name>` | Document feature from UI to database |
| `/sync-feature-flows [range]` | Batch-update feature flows from code changes |
| `/add-testing <name>` | Add testing section to feature flow |

### Code Quality & Security

| Skill | Purpose |
|-------|---------|
| `/security-check` | Pre-commit secret detection in staged files |
| `/security-analysis [scope]` | Full OWASP-based security audit |
| `/refactor-audit [scope]` | Identify complexity issues and refactoring candidates |
| `/tidy [scope]` | Audit and clean up repository structure |

### Project Management

| Skill | Purpose |
|-------|---------|
| `/roadmap [command]` | Query GitHub Issues for priorities and status |

## Agents Reference

| Agent | Purpose |
|-------|---------|
| `feature-flow-analyzer` | Traces and documents feature vertical slices |
| `test-runner` | Runs test suite with tiered execution (smoke/core/full) |
| `security-analyzer` | OWASP Top 10 security analysis |

## Memory Files Explained

```
requirements.md  ──defines──►  What features exist
       │
       ▼
roadmap.md       ──prioritizes──►  What to work on next
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

## Customization

### Adding Project-Specific Skills

Create new directories in `.claude/skills/` with a `SKILL.md` file:

```markdown
---
name: my-skill
description: What this skill does
allowed-tools: [Read, Write, Edit, Bash]
user-invocable: true
automation: manual
---

# My Custom Skill

Description of what this skill does.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|

## Process

### Step 1: ...

## Completion Checklist

- [ ] Step completed
```

### Adding Project-Specific Agents

Create new `.md` files in `.claude/agents/`:

```markdown
---
name: my-agent
description: What this agent does
tools: Read, Grep, Glob, Write, Edit
model: sonnet
---

You are a specialist for [domain]. Your job is to [task].

## Instructions
...
```

### Extending Memory Files

The memory file structure can be extended. Common additions:

- `docs/memory/decisions.md` - Architecture Decision Records (ADRs)
- `docs/memory/incidents.md` - Incident response log
- `docs/memory/integrations.md` - Third-party integration details

## Best Practices

### DO

- Load context before starting work (`/read-docs`)
- Read feature flows before modifying features
- Run tests after every significant change
- Update feature flows when behavior changes
- Run `/security-check` before every commit
- Use `/commit` for consistent commit messages with issue linking

### DON'T

- Skip context loading ("I remember from last time")
- Modify features without reading their flow
- Commit without running tests
- Leave feature flows outdated after changes
- Create documentation files unless explicitly asked

## Changelog Format

Use emoji prefixes for quick visual scanning:

| Emoji | Category |
|-------|----------|
| `🎉` | Major milestone |
| `✨` | New feature |
| `🔧` | Bug fix |
| `🔄` | Refactoring |
| `📝` | Documentation |
| `🔒` | Security update |
| `🚀` | Performance |
| `💾` | Data/persistence |
| `🐳` | Infrastructure |

## Status Labels

Use consistent status labels across all memory files:

| Status | Meaning |
|--------|---------|
| `⏳` | Pending / Not started |
| `🚧` | In progress |
| `✅` | Complete |
| `❌` | Blocked / Failed |

## License

MIT License - Use freely in your projects.
