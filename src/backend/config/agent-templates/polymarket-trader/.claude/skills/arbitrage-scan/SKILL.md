---
name: arbitrage-scan
description: Scan Polymarket for structural arbitrage opportunities - intra-market YES/NO spreads, cross-market correlation mispricings, and dispute discount opportunities.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Arbitrage Scan

Systematic scan for structural mispricings on Polymarket. Three scan types, each exploiting a different kind of market inefficiency.

## Invocation

```
/arbitrage-scan [--top-50 | --disputes | --crypto-pairs]
```

- `--top-50` - Run all 3 scan types on top 50 markets by volume (default)
- `--disputes` - Only scan disputed markets
- `--crypto-pairs` - Only scan crypto price market pairs for delta-neutral opportunities

## Scan Type 1: Intra-Market YES/NO Arbitrage

**What:** Find markets where YES_ask + NO_ask < $0.98 (guaranteed profit after Polymarket's 2% fee on net winnings).

**How:**
```bash
# Get top active markets with token IDs
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&order=volume&ascending=false&limit=50" | jq '[.[] | .markets[] | {question: .question, yes_token: .clobTokenIds[0], no_token: .clobTokenIds[1]}]'
```

For each market, check the best ask on both sides:
```bash
# YES side best ask
curl -s "https://clob.polymarket.com/book?token_id=<YES_TOKEN>" | jq '[.asks[] | .price | tonumber] | sort | .[0]'

# NO side best ask
curl -s "https://clob.polymarket.com/book?token_id=<NO_TOKEN>" | jq '[.asks[] | .price | tonumber] | sort | .[0]'
```

**Flag if:** YES_ask + NO_ask < 0.98. Profit = $1.00 - YES_ask - NO_ask - (0.02 * profit).

**Reality check:** Most arb opportunities are fleeting or have insufficient liquidity. Check size available at the ask price before acting.

## Scan Type 2: Cross-Market Correlation Arbitrage

**What:** Find related markets where combined probabilities are logically inconsistent.

**Examples:**
- "BTC above $70k by April" YES should be >= "BTC above $80k by April" YES (because $80k implies $70k)
- Election markets across states should have consistent conditional probabilities
- "X by March" and "X by June" — the June version can't be cheaper than March

**How:** Search for market pairs that reference the same underlying:
```bash
# Search for BTC markets
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&title=bitcoin&limit=20" | jq '.[] | {title: .title, markets: [.markets[] | {q: .question, yes: .clobTokenIds[0]}]}'

# Compare YES prices across related markets
```

**Flag if:** Logical inconsistency found (e.g., higher threshold priced higher than lower threshold).

## Scan Type 3: Dispute Discount

**What:** Markets in dispute often have depressed prices due to uncertainty. If you can assess likely resolution direction, buy at discount.

**How:**
```bash
# Search for markets with dispute-related terms
curl -s "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100" | jq '[.[] | select(.title | test("dispute|disputed|resolution"; "i"))] | .[] | {title: .title, volume: .volume}'
```

**Cross-reference:** Check UMA voter wallets from `workspace/whale-watchlist.json` (category: `uma_voters`) to see how dispute resolution specialists are positioning.

**Companion tool:** https://www.betmoar.fun/ — check dispute vote direction and status.

## Output

Log all found opportunities to `workspace/arbitrage-log.csv`:
```
timestamp,scan_type,market_a,market_b,price_a,price_b,combined,profit_pct,liquidity,action,notes
```

## When to Run

- Scheduled every 6 hours via Trinity scheduler
- On-demand when capital is available and you want structural opportunities
- After a market enters dispute (scan type 3 specifically)

## Notes

- Polymarket charges 2% fee on net winnings — arb must exceed this to be profitable
- Liquidity matters — a 5% arb spread with $2 available is not worth executing
- Arb opportunities are competitive — bots scan continuously. Anything obvious is likely already taken.
- The real edge is in scan types 2 and 3 — they require judgment that bots can't easily replicate
