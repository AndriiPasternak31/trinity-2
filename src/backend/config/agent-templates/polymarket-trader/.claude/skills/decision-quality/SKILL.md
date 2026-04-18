---
name: decision-quality
description: Evaluate trading decision quality independent of outcomes. Computes Brier scores, calibration curves, edge capture metrics, and updates Platt scaling parameters.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Decision Quality

Evaluate trading decision quality independent of P&L outcomes.

## Invocation

```
/decision-quality [--full | --quick]
```

- `--full` - Complete analysis with calibration update and recalibration check
- `--quick` - Summary metrics only
- `--learning` - Learning report for EXPLORE bets only

## Key Metrics

### 1. Brier Score
Measures calibration: do your probability estimates match reality?

```
brier_score = (predicted_probability - actual_outcome)^2
```

- **0.0** = perfect calibration
- **0.25** = random guessing (always predicting 50%)
- **Lower is better**

Compute from `workspace/brier-log.csv` for resolved trades where `decision_type=EDGE` (or no decision_type column, which defaults to EDGE). Exclude EXPLORE bets from Brier calibration - they have their own learning metrics.

### 2. Edge Capture
Are you finding real edge over market prices?

```
edge_capture = average(|my_probability - market_price|) for winning trades
```

Compare your calibrated probabilities vs market prices at time of trade.

### 3. Process Adherence
Are you following trading rules?

Check:
- Decision recorded BEFORE every trade? (brier-log.csv entries have pre-trade timestamps)
- Deep scan run every cycle? (5 levels, not surface-only)
- Anti-passivity rules followed? (no 3+ consecutive holds)
- Position limits respected? (max $15/market, $100 total)
- Cornelius consulted for political/geopolitical bets?

### 4. Attribution Honesty
Are you honest about skill vs luck?

For each resolved trade, classify:
- **Skill** - Edge hypothesis was correct, outcome matched reasoning
- **Luck** - Right outcome but wrong reasoning
- **Bad luck** - Good reasoning but wrong outcome
- **Bad skill** - Wrong reasoning and wrong outcome

## Full Analysis Steps

### Step 1: Load Data
```
Read workspace/brier-log.csv
Filter for resolved trades (resolved=1)
```

### Step 2: Compute Brier Scores
For each resolved trade:
```
brier = (calibrated_probability - outcome)^2
```

Report:
- Overall Brier score (average)
- Brier score by edge type
- Brier score by confidence level
- Trend over time (improving or degrading?)

### Step 3: Calibration Curve
Group predictions into bins (0-10%, 10-20%, ..., 90-100%).
For each bin, compare:
- Average predicted probability
- Actual win rate

**Well-calibrated**: predicted ~= actual in each bin.
**Overconfident**: predicted > actual (common LLM bias).
**Underconfident**: predicted < actual.

### Step 4: Recalibration Check
Read `workspace/calibration-params.json`.
If `n_trades_used` has reached `next_recalibration_at`:

1. Extract (raw_probability, outcome) pairs from brier-log.csv
2. Fit logistic regression: `outcome ~ A * logit(raw_prob) + B`
3. Update calibration-params.json:
```json
{
  "A": <fitted_A>,
  "B": <fitted_B>,
  "source": "fitted from brier-log.csv",
  "last_updated": "<today>",
  "n_trades_used": <count>,
  "next_recalibration_at": <count + 50>
}
```

### Step 5: Report
Generate summary:
```
=== Decision Quality Report (Cycle N) ===

Resolved trades: X
Overall Brier Score: 0.XXX (target: <0.20)
Edge Capture: X.X% average edge on winners

Calibration:
  0-20%: predicted X%, actual X% [OK/OVER/UNDER]
  20-40%: predicted X%, actual X% [OK/OVER/UNDER]
  40-60%: predicted X%, actual X% [OK/OVER/UNDER]
  60-80%: predicted X%, actual X% [OK/OVER/UNDER]
  80-100%: predicted X%, actual X% [OK/OVER/UNDER]

Process: X/5 rules followed
Attribution: X% skill, X% luck, X% bad luck, X% bad skill

Platt Scaling: A=X.X, B=X.X (recalibration at N trades)
```

Write report to `workspace/activity-log.md`.

## Learning Report (--learning flag)

When invoked with `--learning`, generate a report for EXPLORE bets only:

1. Filter `workspace/brier-log.csv` for `decision_type=EXPLORE`
2. For resolved EXPLORE bets, compute:
   - Average learning score (1-5)
   - Market types explored (unique list)
   - Top insights (ranked by learning_score)
   - Market types NOT yet explored (compare against: crypto, politics, sports, AI/tech, weather, geopolitics, macro)
3. Recommend which market types to explore next
4. Write learning report to `workspace/activity-log.md`

## Schedule

- **Every 10 heartbeat cycles**: Run `--quick` for summary
- **Daily at 06:00**: Run `--full` via Trinity scheduler (`quality-review`)
- **Every 50 cycles**: Run `--learning` for exploration bet review
- **After recalibration milestone**: Run `--full` to verify new parameters
