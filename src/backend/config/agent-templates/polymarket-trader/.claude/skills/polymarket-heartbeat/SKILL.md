---
name: polymarket-heartbeat
description: Autonomous trading loop with anti-passivity rules. Executes a full trading cycle - scan markets, analyze opportunities, record decisions, calibrate probabilities, execute trades, and persist state.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Polymarket Heartbeat

Autonomous trading cycle. Each invocation executes one full cycle of the heartbeat loop.

## Invocation

```
/polymarket-heartbeat [--live]
```

- `--live` - Execute real trades (default: analysis only)

## Cycle Steps

Execute these steps in order. Do NOT skip steps.

### 1. Load Context
- Read `workspace/heartbeat-state.json` for current cycle number, hold count, last actions
- Read `workspace/activity-log.md` for recent trade history
- Read `workspace/calibration-params.json` for Platt scaling parameters

### 2. DEEP Scan (5 Levels)
Surface scans are NOT enough. Run all 5 levels:

**Level 1 - Volume Discovery:**
```bash
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&order=volume&ascending=false&limit=20" | jq '.[] | {title: .title, volume: .volume, endDate: .endDate}'
```

**Level 2 - Category Searches:**
```bash
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&tag=politics&limit=10" | jq '.[].title'
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&tag=crypto&limit=10" | jq '.[].title'
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&tag=ai&limit=10" | jq '.[].title'
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&title=trump&limit=10" | jq '.[].title'
```

**Level 3 - Full Orderbook Analysis** (for top candidates):
```bash
curl -s "https://clob.polymarket.com/book?token_id=<TOKEN>" | jq '{
  bids: [.bids[] | {p: (.price | tonumber), s: (.size | tonumber)}] | sort_by(-.p)[:15],
  asks: [.asks[] | {p: (.price | tonumber), s: (.size | tonumber)}] | sort_by(.p)[:15]
}'
```
Look for bid/ask clusters in 0.10-0.90 range with real size (>$100).

**Level 4 - Near-Term Resolution:**
Filter for markets ending within 14 days.

**Level 5 - Twitter Intel:**
Use Twitter MCP if available, otherwise web search for current narratives.

### 3. Analyze
Deep dive top 5-10 opportunities with orderbook and spread analysis.

**Consider Intelligence Resources** (see CLAUDE.md) for relevant signals:
- Is there a whale watchlist category that matches this market type?
- Are specialists positioning on this market? What direction?
- For geopolitical markets: what is @Car doing? Ask Cornelius for @clashreport context.
- For earthquake markets: check USGS feed for recent M6.5+ events.
- For Musk tweet markets: check XTracker + what @Annica/@szz are doing.
- For any market: are there large buys from new accounts (insider signal)?
Use your judgment about which resources are relevant. Don't check everything mechanically.

### 4. Opinion Analysis
For each candidate trade, answer:
- What does current price reflect about aggregate opinion?
- What catalyst could SHIFT opinion? (news, event, narrative)
- Which direction will opinion move when catalyst hits?
- Am I positioned BEFORE the shift?
- **Key:** Predict where opinion WILL GO, not just what will happen.

### 5. Review Positions & Balance

**5a. Query live USDC.e balance** (the ACTUAL available capital):
```bash
# Query USDC.e (0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174) balance for proxy wallet
USDC_E_HEX=$(curl -s -X POST https://polygon-bor-rpc.publicnode.com \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174\",\"data\":\"0x70a08231000000000000000000000000${POLYGON_ADDRESS#0x}\"},\"latest\"],\"id\":1}" | jq -r '.result')
USDC_AVAILABLE=$(python3 -c "print(int('$USDC_E_HEX', 16) / 1e6)")
echo "USDC.e available: $USDC_AVAILABLE"
```

**Set `usdc_available` from this live query, NOT from cached state or position math.**

**5b. Review current positions:**
```bash
curl -s "https://data-api.polymarket.com/positions?user=$POLYGON_ADDRESS" | jq '.[] | {market: .title, size: .size, avgPrice: .avgPrice, curPrice: .curPrice}'
```

### 6. Record Decision
**MANDATORY** - Log to `workspace/brier-log.csv` BEFORE executing:
```
DECISION: d{cycle}_{seq}
decision_type: EDGE or EXPLORE
Market: {name} @ {market_price}
My Probability: {X}% (vs market {Y}%)
Edge: +{Z}% ({edge_type})
Confidence: {1-5}/5
Rationale: {why I'm better than market}
Opinion Shift: {what catalyst will move opinion?}
```

**VALIDATION before appending to brier-log.csv:**
- my_raw_prob != market_price (REJECT if equal - you must state a divergent belief)
- my_calibrated_prob is computed from my_raw_prob (not from market_price)
- edge_type is not empty
- decision_type is EDGE or EXPLORE (default: EDGE)
- For EXPLORE bets: learning_goal must be specified

### 6a. Calibrate
Apply Platt scaling to raw probability:
```
logit(p) = ln(p / (1 - p))
calibrated_prob = 1 / (1 + exp(-(A * logit(raw_prob) + B)))
```
- Read A, B from `workspace/calibration-params.json`
- Log both raw and calibrated probability

### 6b. Edge Check
Compare calibrated probability to market price. Proceed if edge exists.

### 7. Execute
Trade based on calibrated probability using py-clob-client.
**Default to BET.** You need a reason NOT to bet.

### 8. Save Snapshot
**MANDATORY** - Append cycle data to `workspace/portfolio-snapshots.csv`:
```
cycle,timestamp,positions_value,btc_price,eth_price,notes
```

**VALIDATION before appending:**
- Verify exactly 6 comma-separated columns
- cycle is an integer
- timestamp is ISO 8601
- positions_value, btc_price, eth_price are numbers
- notes is a quoted string if it contains commas

### 9. Log
Record all decisions with timestamp and rationale in `workspace/activity-log.md`.

### 10. Update State
Write to `workspace/heartbeat-state.json`:
```json
{
  "cycle": N,
  "last_run": "ISO timestamp",
  "consecutive_holds": 0,
  "consecutive_blocks": 0,
  "last_action": "BUY/SELL/HOLD/BLOCKED",
  "markets_explored": 20,
  "trades_this_session": 1
}
```
- `consecutive_holds`: only increments on HOLD, resets on trade or BLOCKED
- `consecutive_blocks`: only increments on BLOCKED, resets on trade or HOLD

### 11. Schedule Next Cycle
Trinity scheduler handles this automatically. No manual timer needed.

### 12. Retrospective (Every 5 Cycles)
- How many bets did I make? (Target: 2+ per 5 cycles)
- What did I learn?
- What market types haven't I tried yet?

### 13. Edge Research (Proactive)
- Consult Cornelius via Trinity MCP for fresh insights
- Ask Cornelius before entering political/geopolitical positions
- Validate edge hypotheses

### 14. Quality Check (Every 10 Cycles)
Run `/decision-quality --full` for calibration report.

## Anti-Passivity Rules (STRICT)

| Trigger | Required Action |
|---------|-----------------|
| 3 consecutive HOLD cycles | MUST place $5-10 bet or exit position |
| >50% capital idle | Deploy immediately - no excuses |
| Surface scan shows "no opportunities" | Run DEEP exploration |
| Same position 10 cycles | Exit for capital velocity |

**HOLDING IS FAILURE.** Default action is BET, not HOLD.

**BLOCKED vs HOLD:** BLOCKED (no USDC, API error) does NOT count toward the 3-hold limit. Still log what you WOULD have done. Note: POL gas is NOT required — the Polymarket relayer covers gas fees.

## Position Limits

```
max_per_market: $15
max_total: $100
min_bet: $5
exploration_bet: $5
```

## Praxis integration — read Professor feedback

1. If `workspace/calibration-notes.md` exists, read it and absorb the
   calibration guidance into your reasoning for this cycle.
2. Before submitting any trade to CLOB, check `template.yaml` field
   `graduation_mode`:
   - `shadow`: log the intended trade to brier-log.csv and STOP (do not execute)
   - `queue`: POST the intended trade to Trinity Operator Queue via
     `mcp__trinity__operator_queue__create`, block on the response:
     - approved → proceed to CLOB submit
     - rejected → record rejection + reason in brier-log.csv; skip
   - `auto`: submit to CLOB directly (current behavior)
3. For each decision, include any cited Cornelius note IDs in the
   `rationale` field using the form `cornelius:<note_id>` (enables
   downstream backprop).
