# utilities Plugin

General-purpose ops and productivity skills for SSH-accessible services and daily workflows.

## Installation

```bash
/plugin install utilities@abilityai
```

## Skills

| Skill | Description |
|-------|-------------|
| `/utilities:save-conversation` | Save conversation as structured markdown |
| `/utilities:investigate-incident` | Structured incident investigation |
| `/utilities:bug-report` | Create sanitized GitHub issue |
| `/utilities:safe-deploy` | Safe deployment with backup/rollback |
| `/utilities:docker-ops` | Docker container management |
| `/utilities:sync-ops-knowledge` | Update ops docs from commits |
| `/utilities:batch-claude-loop` | Batch headless Claude Code calls |

## Safe Deployment

Deploy with automatic backup and rollback capability:

```bash
# Deploy with backup
/utilities:safe-deploy update

# Rollback to previous version
/utilities:safe-deploy rollback
```

The skill:
1. Creates a backup of current state
2. Applies the update
3. Verifies deployment health
4. Rolls back automatically on failure

## Docker Operations

Manage Docker containers:

```bash
/utilities:docker-ops logs backend
/utilities:docker-ops restart frontend
/utilities:docker-ops status
```

## Incident Investigation

Structured approach to investigating production issues:

```bash
/utilities:investigate-incident
```

Guides through:
1. **Symptoms** — What's happening?
2. **Timeline** — When did it start?
3. **Scope** — What's affected?
4. **Evidence** — Logs, metrics, traces
5. **Hypothesis** — Likely causes
6. **Resolution** — Fix and verify

## Conversation Export

Save the current conversation as markdown:

```bash
/utilities:save-conversation
```

Exports to a timestamped file with:
- Full conversation history
- Code blocks preserved
- Tool calls summarized

## Batch Processing

Run Claude Code headlessly on multiple inputs:

```bash
/utilities:batch-claude-loop
```

Useful for:
- Processing multiple files
- Running the same analysis across repos
- Automated code review

## See Also

- [Abilities Overview](overview.md) — Full toolkit overview
- [GitHub: abilityai/abilities](https://github.com/abilityai/abilities) — Source repository
