---
name: backtest
description: Run the Professor retrospectively over polygon-vybe's existing brier-log history.
user-invocable: true
automation: manual
allowed-tools: [Read, Write, Bash, Glob]
---

# Retrospective Backtest

Validate the Professor before any live operation: run the full grading
pipeline over polygon-vybe's historical brier-log.csv and inspect the
generated directives + calibration-notes.

## Usage

```
/backtest
```

## Process

1. Read `/Users/andrii/Desktop/projects/vybe/agents/polygon-vybe/workspace/brier-log.csv`
2. Load PolygonAdapter with `config/rubric.yaml`
3. Run `adapter.grade(df)` over the full resolved history
4. Hold out the most recent 20% of resolved rows as test set; evaluate
   Brier on train vs. test with and without applying directives
5. Write `workspace/backtest-report.md` with:
   - Full-history Brier
   - Proposed Directives
   - Held-out-set simulated Brier delta if directives applied

## Validation gate

If the Day-3 backtest report shows proposed directives that would have
**improved** held-out Brier by ≥ 0.01, proceed to live deployment.
Otherwise, stop and debug the adapter.

## Provisional-data note

Phase 1 is starting with < 30 resolved rows in polygon-vybe's brier-log. This
backtest's `MIN_RESOLVED_FOR_BACKTEST` floor has been set to 3 for
Phase-1 pipeline-validation purposes only. Real statistical validation
is deferred to the 14-day observation window (spec §6 criterion #1).
