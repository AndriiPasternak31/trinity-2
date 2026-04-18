---
name: edge-research
description: Structured Cornelius consultation for edge discovery. Queries Trinity MCP for market intelligence, geopolitical updates, and opportunity signals.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Edge Research

Structured consultation with Cornelius (via Trinity MCP) for edge discovery.
Runs every 12 hours via the `deep-research` schedule.

## Invocation

```
/edge-research [--topic <specific_topic>]
```

- No args: full briefing on all active positions + new opportunities
- `--topic <topic>`: focused research on a specific market or event

## Steps

### 1. Load Current State
- Read `workspace/heartbeat-state.json` for active positions and cycle number
- Read `workspace/edge-hypotheses.md` for tracked theses
- Read last 5 entries from `workspace/brier-log.csv` for recent decisions

### 2. Consult Cornelius

Ask Cornelius via Trinity MCP (`chat_with_agent`) for a structured briefing:

**a) Market-moving developments (last 12 hours):**
- Geopolitical events affecting active positions
- Crypto/macro shifts (BTC, ETH, oil, rates)
- Scheduled events in next 48 hours (FOMC, elections, deadlines)

**b) Edge opportunities:**
- Markets where opinion is shifting but price hasn't caught up
- Markets with upcoming catalysts the market may be underweighting
- Cross-market correlations to watch
- Any markets where GJOpen superforecaster base rates diverge from Polymarket prices

**c) Position review:**
- For each active position: has the thesis changed since last review?
- Risk assessment: any positions that should be exited urgently?
- Sizing: any positions that should be increased based on new info?

### 3. Update Edge Hypotheses

For each new opportunity identified:
- Add to `workspace/edge-hypotheses.md` with thesis, edge type, and success criteria
- If an existing hypothesis is invalidated, update its status to RETIRED with learning

### 4. Log Research

Append findings to `workspace/activity-log.md` under an "Edge Research" header:
```
## Edge Research - {timestamp} UTC

**Cornelius Brief:**
{summary of key findings}

**New Opportunities:**
{list of actionable opportunities with market names and prices}

**Position Updates:**
{any changes to existing position theses}

**Next Research Focus:**
{what to investigate in the next 12-hour cycle}
```

### 5. Update OSINT Signals

Log any real-world signals to `workspace/osint-signals.md`:
- Breaking news that affects markets
- Whale activity detected
- Social media narrative shifts
- Scheduled events approaching

## When to Run

- Scheduled every 12 hours via Trinity scheduler (`deep-research`)
- On-demand when entering a new market type or facing an uncertain position
- Before major catalyst events (elections, deadlines, FOMC)

## Notes

- Cornelius is accessed via Trinity MCP's `chat_with_agent` tool
- Always include your current positions in the query so Cornelius can assess relevance
- If Cornelius is unavailable, fall back to web search for current events
- Keep research queries focused - ask specific questions, not open-ended "tell me everything"
