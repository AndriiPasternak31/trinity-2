---
name: grade
description: Daily grading cycle — run the Professor, write calibration-notes + directives.
user-invocable: true
automation: scheduled
schedule: "0 6 * * *"
allowed-tools: [Read, Write, Bash, Glob]
---

# Daily Grade

Runs the Professor pipeline against polygon-vybe's latest brier-log.csv.
Writes calibration-notes.md (Student reads next cycle) and directives.json.

## State Dependencies

| Source | Location | Read | Write |
|---|---|---|---|
| Student log | `polygon-vybe/workspace/brier-log.csv` | ✓ | |
| Calibration notes | `polygon-vybe/workspace/calibration-notes.md` | | ✓ |
| Surprise log | `polygon-vybe/workspace/surprise-log.md` | | ✓ |
| Directives | `professor-polygon/workspace/directives.json` | | ✓ |
| HSH store | `professor-polygon/workspace/hidden_state_store.json` | ✓ | ✓ |
