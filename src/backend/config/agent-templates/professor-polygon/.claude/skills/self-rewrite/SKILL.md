---
name: self-rewrite
description: Apply pending Directives to polygon-vybe — git-commit edits to calibration params + new correction skills.
user-invocable: true
automation: scheduled
schedule: "10 6 * * *"
allowed-tools: [Read, Write, Bash, Edit]
---

# Self-Rewrite

Reads `professor-polygon/workspace/directives.json`, applies each to
polygon-vybe's writable paths, commits each as a separate commit
authored by `professor-polygon`.

## Writable whitelist

- `polygon-vybe/workspace/calibration-params.json` — overwrite
- `polygon-vybe/.claude/skills/correction-<id>/SKILL.md` — create only

Any directive that would touch any other path is refused and logged to
`professor-polygon/workspace/refused-directives.md`.
