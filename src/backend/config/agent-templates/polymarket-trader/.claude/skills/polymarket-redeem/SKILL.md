---
name: polymarket-redeem
description: Redeem resolved Polymarket positions to recover USDC. Identifies redeemable positions, calls Conditional Tokens contract, and recovers capital from winning bets.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Polymarket Redeem

Redeem resolved prediction market positions to recover USDC capital.

## Invocation

```
/polymarket-redeem [--all | --dry-run | <condition_id>]
```

- `--all` - Redeem all resolved positions
- `--dry-run` - Show what would be redeemed without executing
- `<condition_id>` - Redeem a specific position

## How It Works

When a Polymarket market resolves:
- **Winning positions** can be redeemed for $1.00 per share
- **Losing positions** are worth $0.00 but should be cleared
- Redemption calls the Conditional Tokens contract on Polygon
- Gas fees are covered by the Polymarket relayer — no POL needed for redemptions

## Steps

### 1. Check Positions
Fetch all positions and identify resolved ones:
```bash
curl -s "https://data-api.polymarket.com/positions?user=$POLYGON_ADDRESS" | jq '[.[] | select(.resolved == true)] | length'
```

### 2. Identify Redeemable
For each resolved position, check:
- Is the market resolved? (`resolved: true`)
- What was the outcome?
- Is this a winning position? (position side matches outcome)
- Has it already been redeemed?

### 3. Display Summary
Show what will be redeemed:
```
Position: [Market Name]
Side: YES/NO @ $0.XX
Outcome: YES/NO
Result: WIN/LOSS
Redeemable: $X.XX
```

### 4. Execute Redemption
If `--dry-run` is not set, call the Conditional Tokens contract via py-clob-client:
```python
from py_clob_client.client import ClobClient
client = ClobClient("https://clob.polymarket.com", key=POLYGON_PRIVATE_KEY, chain_id=137)
# Redeem resolved positions
```

### 5. Update State
- Log redemption to `workspace/activity-log.md`
- Update `workspace/portfolio-snapshots.csv` with new balance

## When to Use

- After markets resolve (positions show `redeemable: true`)
- When capital is needed for new trades
- During heartbeat when low on available USDC
- Scheduled automatically every 30 minutes via Trinity scheduler (`quick-pulse`)

## Notes

- Gas fees are covered by the Polymarket relayer — no POL balance needed
- Winning positions return $1.00 per share
- Losing positions return $0.00 but clearing them keeps the portfolio clean
- No gas balance check needed — relayer covers all transaction fees on Polygon

## Praxis integration — backprop

After writing the resolved row to brier-log.csv, invoke:

```
mcp__trinity__chat_with_agent(
  agent_name="professor-polygon",
  skill="cornelius-backprop",
  args={}
)
```

This triggers the backprop run over newly resolved rows.
