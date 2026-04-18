# Polymarket Trader — Ecosystem Enhancement Design

## Context

The Polymarket Trader agent (`polygon-vybe` repo, branch `trinity/polygon-andrii/2fb423a3`) is a live, autonomous trading agent at cycle 33 with ~$115 portfolio across 14 positions. It trades on Polymarket using Platt calibration, Brier scoring, anti-passivity rules, and Cornelius as a research brain via Trinity MCP.

**Problem:** The agent scans markets in isolation. It doesn't know what profitable traders are doing, misses structural arbitrage, and doesn't connect real-world data feeds to market movements. Its heartbeat cycle is also very rigid — a 14-step checklist that doesn't encourage adaptive thinking.

**Solution:** Add an **Intelligence Resources** catalog to the agent — whale watchlists, OSINT feeds, arbitrage patterns, and data APIs — that it consults based on its own judgment about what's relevant to the specific market it's analyzing. Not a checklist to follow, but a toolkit to reason with.

**Source intel:** `docs/research/polymarket-ecosystem-intel.md`

---

## Core Architecture Change: Resource Catalog + Judgment

Instead of adding "Level 6, Level 7, Level 8" to the rigid heartbeat checklist, we restructure the agent's knowledge:

**Before:** "Execute these 14 steps in order. Do NOT skip steps."
**After:** "Here are your intelligence resources. When you're analyzing a market, consider which resources are relevant and use them."

The agent keeps its core heartbeat flow (scan → analyze → decide → execute → log) but gains a **resource-aware reasoning layer** — a catalog of intelligence sources it can pull from based on context.

### How the agent accesses external information

| Source | Method | Reliability |
|--------|--------|-------------|
| Whale wallet trades | Polymarket Data API (free, no auth) | High — on-chain data, always accurate |
| Market orderbooks | CLOB API (free, no auth) | High — real-time |
| Insider detection | Polymarket Data API (filter by size + trade count) | High — same API |
| UMA voter positions | Polymarket Data API | High |
| USGS earthquakes | Public JSON API | High — official government feed |
| XTracker (Musk tweets) | Web scraping | Fragile — could break anytime |
| X/Twitter (@clashreport etc.) | Cornelius web search (Option B) | Medium — not real-time, but good enough for 4h cycles |
| X/Twitter (@clashreport etc.) | Track @Car's wallet instead (Option C) | High — follow the money, not the news |

**Key insight:** For OSINT sources like @clashreport, tracking what @Car (who reads @clashreport) is buying is MORE reliable than trying to read @clashreport directly. Whale wallet tracking IS the OSINT signal — compressed into an on-chain action.

---

## What Gets Added to the Agent

### 1. Intelligence Resources Section (CLAUDE.md)

A new section in CLAUDE.md — NOT part of the heartbeat checklist. The agent decides when each resource is relevant.

```markdown
## Intelligence Resources

These resources are available for your analysis. Use them when relevant —
you decide what applies to each market. Don't mechanically check everything;
think about which resources matter for the specific opportunity you're evaluating.

### Whale Watchlist
**File:** workspace/whale-watchlist.json
**API:** curl -s "https://data-api.polymarket.com/trades?user=<ADDRESS>&limit=10"
**What it is:** 60+ curated wallets of consistently profitable Polymarket traders,
categorized by specialty (Musk tweets, BTC 15-min, weather, geopolitics, sports,
gaming, UMA dispute voters, general profitable).
**When useful:**
- Before entering a market: are specialists in this category positioning?
- Reviewing existing positions: are specialists still holding or exiting?
- Unusual volume on a market: is it whale-driven?
- If multiple specialists are positioning the same direction, that's a strong signal
**Signal strength:** High. These are curated accounts with proven track records.

### Insider Detection
**API:** Same Data API — filter by trade size and account history
**What it is:** Flag buys >$9K from accounts with <10 historical trades. New account + large bet = potential insider.
**When useful:** When a market has unusual one-sided volume from unfamiliar accounts
**How to check:**
  1. Pull recent large trades on the market
  2. For suspicious accounts, check total trade count
  3. Factor into edge analysis — don't blindly follow, but note the signal

### UMA Voter Tracking
**Wallets:** Listed in whale-watchlist.json under "uma_voters" category
**What it is:** Accounts known to vote on UMA dispute resolutions
**When useful:** When a market enters or is in dispute. Their positioning signals likely resolution direction.
**Companion:** betmoar.fun — check dispute vote direction

### Arbitrage Patterns
**What to scan for:**
1. **Intra-market:** YES_ask + NO_ask < $0.98 on same market (guaranteed profit after 2% PM fee)
2. **Cross-market:** Related markets with inconsistent pricing (e.g., "BTC >70k" vs "BTC >80k" — the latter can't be more probable)
3. **Dispute discount:** Markets in dispute often have depressed prices — if you can assess resolution direction (via UMA voters), buy at discount
**When useful:** Always worth a quick scan during market exploration. The agent already knows about intra-exchange arb (L#24) but doesn't systematically scan for it.

### Delta-Neutral Crypto Strategy
**What it is:** When entering crypto price markets, check if opposing markets can be combined for a hedged position.
**Example:** Buy "BTC won't dip to $60k" NO + "BTC won't reach $80k" NO. If BTC stays in range, both pay $1. If combined cost < $1, it's guaranteed profit within that range.
**When useful:** When the agent is already looking at crypto price markets (which it does frequently — 3 BTC/ETH positions right now).

### USGS Earthquake Feed
**API:** curl -s "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_hour.geojson" | jq '.features[] | select(.properties.mag >= 6.5) | {mag: .properties.mag, place: .properties.place, time: (.properties.time / 1000 | todate)}'
**What it is:** Real-time earthquake data from the same source Polymarket uses for resolution.
**When useful:** When earthquake markets are active on Polymarket. M6.5+ is the typical bet threshold.
**Edge:** USGS reports faster than Polymarket prices move — timing edge if you catch it first.

### Musk Tweet Markets
**Resolution source:** xtracker.polymarket.com (Post Counter figure)
**Counting rules:** Main feed posts, quote posts, reposts count. Replies do NOT count (except replies on main feed). Deleted posts count if captured within ~5 minutes.
**Key wallets:** @Annica, @szz, @Prexpect, @sb911 (in whale-watchlist.json under "musk_tweets")
**Strategy:** If you can estimate tweet velocity (tweets/hour), project count at market close. Compare to market ranges. Check what tweet market specialists are doing.
**When useful:** When weekly or monthly tweet count markets are active.
**XTracker access:** Web scrape — fragile, may need fallback to counting manually or checking whale positions instead.

### Geopolitical OSINT
**Primary method:** Track wallet @Car (consistently profitable, uses @clashreport as info source)
**Secondary method:** Ask Cornelius to web search for recent @clashreport tweets on the topic
**What it is:** @clashreport is a real-time geopolitical OSINT account. Rather than reading it directly (no X API), follow what @Car is doing — @Car's trades ARE the @clashreport signal, compressed into action.
**When useful:** Before entering geopolitical/Iran/Middle East positions (the agent already trades these heavily).
**Why @Car's wallet > reading X directly:** On-chain actions are concrete and timestamped. No interpretation needed. If @Car buys, they assessed the situation and acted.

### Key Twitter Accounts (via Cornelius web search)
When you need context beyond wallet tracking, ask Cornelius to search for:
- @ValeriusLabs — Contrarian PM analysis
- @asteraappai — PM market structure
- @polyaborik — PM whale activity
- @clashreport — Geopolitical OSINT
Use: mcp__trinity__chat_with_agent(agent_name="cornelius", message="Search recent tweets from @clashreport about [topic]", timeout_seconds=300)
```

### 2. Whale Watchlist File (workspace/whale-watchlist.json)

Machine-readable categorized wallet list. Same structure as in original spec — categories for musk_tweets, btc_15min, weather, geopolitics_israel, geopolitics_middle_east, google_insider, crypto_longterm, sports, gaming, uma_voters, general_profitable.

**Implementation note:** Wallet handles need to be resolved to addresses. For each handle, query `https://polymarket.com/@<handle>` to get the on-chain address. This is a one-time setup step.

### 3. Arbitrage Scan Skill (.claude/skills/arbitrage-scan/SKILL.md)

Standalone skill (not part of heartbeat) that the agent can invoke when it wants to systematically scan for structural opportunities. Scheduled every 6 hours via template.yaml, but also invocable on-demand.

Three scan types: intra-market YES/NO, cross-market correlation, dispute discount.

### 4. OSINT Signals Log (workspace/osint-signals.md)

Optional log for when external data (USGS earthquake, whale movement, etc.) triggered the agent to investigate a market. Helps with retrospective analysis — which OSINT sources actually led to trades?

---

## Files Modified (Summary)

| File | Action | Description |
|------|--------|-------------|
| `CLAUDE.md` | Edit | Add "Intelligence Resources" section (replaces rigid Level 6/7). Resource catalog with when-to-use guidance |
| `workspace/whale-watchlist.json` | Create | 60+ wallets categorized by specialty, with addresses |
| `.claude/skills/arbitrage-scan/SKILL.md` | Create | Standalone arbitrage scanning skill (3 scan types) |
| `.claude/skills/polymarket-heartbeat/SKILL.md` | Edit | Add light reference to Intelligence Resources (not mandatory steps) |
| `template.yaml` | Edit | Add arbitrage-scan schedule (every 6h) |
| `workspace/arbitrage-log.csv` | Create | Header row for tracking arb opportunities |
| `workspace/osint-signals.md` | Create | Template for OSINT signal logging |

**What does NOT change:**
- Core heartbeat flow (scan → analyze → decide → execute → log)
- Existing skills (polymarket-redeem, decision-quality)
- Position limits, anti-passivity rules, Brier scoring
- Cornelius integration
- Platt calibration

---

## Verification Plan

1. **Whale tracking works:** Query Data API for 3 wallets from the watchlist, confirm trades are returned
2. **Insider detection works:** Query a high-volume market's recent trades, filter by size >$9K, check trade counts
3. **Arbitrage scan works:** Run `/arbitrage-scan --top-50`, confirm it finds and logs YES/NO spreads
4. **USGS API works:** Query earthquake feed, confirm JSON parsing returns expected format
5. **Cornelius OSINT works:** Ask Cornelius to search for @clashreport tweets, confirm it returns results
6. **Integration test:** Run 3 heartbeat cycles with all resources available, verify the agent naturally incorporates relevant resources into its analysis without being told which ones to use
7. **No regressions:** Existing trading, redemption, and Brier logging still work
