# Polymarket Ecosystem Intelligence

> Source: Cryptomannn Community (LT program) + HolyPoly Grail platform
> Collected: 2026-02-23 to 2026-03-27
> Key people: **Borkiss** (CTO/CAO), **Spirit** (Research Lead)

---

## 1. HolyPoly Grail — Analytics Platform

**URL**: https://www.holypoly.ca

The team's proprietary analytics terminal for Polymarket. Built on Next.js, dark-themed trading terminal UI.

### Boards (Modules)

| Board | Code | URL | Purpose | Access |
|-------|------|-----|---------|--------|
| SEISMIC | B01 | [/boards/earthquake](https://www.holypoly.ca/boards/earthquake) | Earthquake monitoring map + TG alert bot. Tracks USGS data for Polymarket earthquake markets | Public (no login) |
| SIGINT | B02 | [/boards/iran](https://www.holypoly.ca/boards/iran) | Geopolitical OSINT dashboard — Iran situation monitoring, news, for geopolitical markets | Public (no login) |
| CALC | B03 | [/boards/calculator](https://www.holypoly.ca/boards/calculator) | Delta-neutral strategy calculator for any markets, especially BTC/SOL/ETH 1D | Requires Google login |
| SCREENER | B04 | [/boards/screener](https://www.holypoly.ca/boards/screener) | N-leg arbitrage screener for weather and climate markets | LT members only (contact [Borkiss on TG](https://t.me/borkiss)) |
| MUSK | B05 | [/boards/musk](https://www.holypoly.ca/boards/musk) | Musk tweet count tracker with prediction model + activity heatmap | Unknown (recently launched) |

### Platform Features (from landing page)
- N-leg arbitrage analysis
- Global OSINT aggregation (GDELT, AIS vessel tracking, FIRMS wildfire data)
- Transparent microstructure insights (MIT-licensed calculations, open-source)
- Real-time CLOB data from Polymarket (12,000+ markets)
- WebSocket feeds for live data

---

## 2. Market-Making Engine (bs-p)

**Repo**: https://github.com/lubluniky/bs-p
**Author**: Borkiss
**Status**: Open-source, live-tested

A high-performance computational kernel for Polymarket market-making. NOT a ready-made bot — a risk calculation engine.

### Technical Foundation
- Based on **Avellaneda-Stoikov market-making strategy in logit space**
- Adapted from "Toward Black-Scholes for Prediction Markets" (Shaw & Dalen, 2025)
- **C core + Rust FFI bindings**, AVX-512 SIMD acceleration
- Performance: **6.71 ns/market** quote latency across 8,192 markets
- Throughput: **29.05M msgs/sec** for market data handling

### Core Capabilities

| Feature | What It Does |
|---------|--------------|
| **Adaptive Kelly Sizing** | Calculates optimal bet size from edge, portfolio state, and risk limits. Prevents overexposure ("anti-gambling protection") |
| **Implied Volatility Radar** | Extracts implied vol from current spread — shows which markets have high uncertainty priced in by market makers |
| **What-If Stress Tests** | Simulates PnL impact if event probability jumps by X%. Runs across thousands of positions in microseconds |
| **Order Book Pressure (OBI/VWM)** | Detects aggressive buying/selling pressure in the order book. Signals whether the bot is trading against momentum |
| **Portfolio Greeks** | Aggregates risk across correlated markets (e.g., election outcomes in different states) into a single risk metric with correlation adjustments |

---

## 3. Telegram Bots Ecosystem

### Holy Snipe
- **URL**: https://t.me/holy_snipe_bot (updated address)
- **Purpose**: Alerts on actions (buys/sells) of any selected Polymarket account
- **Latency**: ~1 min (improved from 3-5 min)

### Insider Scanner
- **URL**: https://t.me/HolyPolyInsiderScanner
- **Purpose**: Alerts on buys from potential insiders and whales
- **Criteria**: >$9K buy AND <10 trades in history (new account, large bet = potential insider)

### Holy Dispute
- **URL**: https://t.me/holy_poly_dispute
- **Purpose**: Alerts on markets with level 1-2 disputes (final disputes excluded)
- **Companion tool**: https://www.betmoar.fun/ — view dispute status and check which direction voters are leaning

### EQ Feed
- **URL**: https://t.me/eqfeed_bot
- **Purpose**: Earthquake alerts from same source as Polymarket, via direct API
- **Features**: Share prices included, alerts for M6.5+ (matching Polymarket bet thresholds)
- **Powered by**: dreambound.org

### Holy TOP-10 Tracker
- **URL**: https://t.me/poly_market_whale_tracker_bot
- **Purpose**: Alerts on buys/sells from top-10 holders on each side (YES/NO) of a selected market

### BetMoar Bot (integrated into Holy Poly community chat)
- **Purpose**: In-chat research and trading assistant
- **Trigger**: Paste any market URL or account URL for automatic detailed stats

#### BetMoar Commands

**Trading**
```
bm s [query]         — search markets
bm ob [query]        — view orderbook via search
bm ob [number]       — view orderbook for specific market
```

**Portfolio**
```
bm pos [filter]      — view your positions
bm profile           — view trader profile
bm chart profile [interval] — view your PnL chart
bm recent [filters] [page]  — view recent trades
bm leaderboard       — view trader rankings
```

**Summary**
```
bm summary [interval]          — chat summary for period (e.g., 3h, 12h)
bm summary [interval] markets  — chat summary focused on market discussions
```

**Betting Tools**
```
bm kelly    — calculate optimal bet size (Kelly criterion)
bm apy      — calculate simple annual yield
bm tz       — convert timezones
bm track    — track wallets and their trades in real-time
```

**AI Analysis**
```
bm ai cope [@user]   — get "copium" for losses
bm ai flex [@user]   — celebrate winning trades
bm ai pvp @user      — compare results with another trader
bm ai roast [@user]  — roast trading performance
```

---

## 4. Whale Watchlist — Accounts to Track

Curated by **Spirit** (Research Lead). Categorized by market specialization.

### General / Mixed Strategy
| Account | Notes |
|---------|-------|
| [@bobe2](https://polymarket.com/@bobe2) | |
| [@JAHODA](https://polymarket.com/@JAHODA) | |
| [@Car](https://polymarket.com/@Car) | Uses [@clashreport](https://x.com/clashreport?s=21) as info source |
| [@ImJustKen](https://polymarket.com/@ImJustKen) | |
| [@TheWolfOfPoly](https://polymarket.com/@TheWolfOfPoly) | |
| [@kekkone](https://polymarket.com/@kekkone) | |
| [@archaic](https://polymarket.com/@archaic) | |
| [@dontshowmyname](https://polymarket.com/@dontshowmyname) | |
| [@mango-lassi](https://polymarket.com/@mango-lassi) | |
| [@Euan](https://polymarket.com/@Euan) | |
| [@LlamaEnjoyer](https://polymarket.com/@LlamaEnjoyer) | |
| [@AJSV](https://polymarket.com/@AJSV) | |
| [@Roflan-ludoman](https://polymarket.com/@Roflan-ludoman) | |
| [@slight-](https://polymarket.com/@slight-) | |
| [@poorsob](https://polymarket.com/@poorsob) | |
| [@pako](https://polymarket.com/@pako) | |
| [@mombil](https://polymarket.com/@mombil) | |
| [@Vespucci](https://polymarket.com/@Vespucci) | |
| [@Dropper](https://polymarket.com/@Dropper) | |
| [@JJo](https://polymarket.com/@JJo) | |
| [@0xheavy888](https://polymarket.com/@0xheavy888) | |
| [@HolyMoses7](https://polymarket.com/@HolyMoses7) | |
| [@donjo](https://polymarket.com/@donjo) | |
| [@033033033](https://polymarket.com/@033033033) | |
| [@0xe3726a...](https://polymarket.com/@0xe3726a1b9c6ba2f06585d1c9e01d00afaedaeb38) | |
| [@scottilicious](https://polymarket.com/@scottilicious) | |
| [@0xe8dd77...](https://polymarket.com/@0xe8dd7741ccb12350957ec71e9ee332e0d1e6ec86) | |

### Musk Tweet Markets Specialists
| Account | Notes |
|---------|-------|
| [@Annica](https://polymarket.com/@Annica) | |
| [@szz](https://polymarket.com/@szz) | |
| [@Prexpect](https://polymarket.com/@Prexpect) | |
| [@sb911](https://polymarket.com/@sb911) | |

### Google Insider
| Account | Notes |
|---------|-------|
| [@beepboopzyx](https://polymarket.com/@beepboopzyx) | Suspected insider knowledge on Google events |

### Long-Term Crypto + 15-Min Markets
| Account | Notes |
|---------|-------|
| [@justdance](https://polymarket.com/@justdance) | |
| [@coinman2](https://polymarket.com/@coinman2) | |
| [@x6916Cc00...](https://polymarket.com/@x6916Cc00AA1c3e75ECf4081DF7caE7D2f3592fd4) | |
| [@0xf705fa...](https://polymarket.com/@0xf705fa045201391d9632b7f3cde06a5e24453ca7) | |

### TGE (Token Generation Events)
| Account | Notes |
|---------|-------|
| [@filthyBera](https://polymarket.com/@filthyBera) | |

### Geopolitics — Israel
| Account | Notes |
|---------|-------|
| [@Rundeep](https://polymarket.com/@Rundeep) | |

### Geopolitics — Middle East
| Account | Notes |
|---------|-------|
| [@Sonix](https://polymarket.com/@Sonix) | |

### 15-Minute BTC Markets
| Account | Notes |
|---------|-------|
| [@gabagool22](https://polymarket.com/@gabagool22) | |
| [@distinct-baguette](https://polymarket.com/@distinct-baguette) | |
| [@PBot1](https://polymarket.com/@PBot1) | |
| [@1TickWonder2](https://polymarket.com/@1TickWonder2) | |
| [@Sharky6999](https://polymarket.com/@Sharky6999) | |
| [@kingofcoinflips](https://polymarket.com/@kingofcoinflips) | |
| [@a4385](https://polymarket.com/@a4385?via=archive) | 15K -> 230K in 2 days |
| [@bratanbratishka](https://polymarket.com/@bratanbratishka) | 100K in 2 days on 5-15 min markets |

### Speed Trading (1-second captures)
| Account | Notes |
|---------|-------|
| [@megamm2](https://polymarket.com/@megamm2) | Catches many trades at 1-second precision |

### Weather Markets
| Account | Notes |
|---------|-------|
| [0xa2711d...](https://polymarket.com/profile/0xa2711d1d311a0b2fa7f88d5c7cb760a3fa062727) | |
| [@neobrother](https://polymarket.com/@neobrother) | |
| [@VibeTrader](https://polymarket.com/@VibeTrader) | |
| [@1pixel](https://polymarket.com/@1pixel) | |
| [@0x594edB...](https://polymarket.com/@0x594edB9112f526Fa6A80b8F858A6379C8A2c1C11-1762688003124) | |
| [@HondaCivic](https://polymarket.com/@HondaCivic) | |

### Movies / Entertainment
| Account | Notes |
|---------|-------|
| [@0xe2b1fc...](https://polymarket.com/@0xe2b1fc269d0c2e27da11fadd1d9596fe28227d2a) | |

### Sports
| Address | Notes |
|---------|-------|
| `0x5350afcd8bd8ceffdf4da32420d6d31be0822fda` | |
| `0x204f72f35326db932158cba6adff0b9a1da95e14` | |
| `0x2005d16a84ceefa912d4e380cd32e7ff827875ea` | |

### Gaming / Esports
| Account | Notes |
|---------|-------|
| [@DaisyFarm](https://polymarket.com/@DaisyFarm) | |
| [@BossOfEsports](https://polymarket.com/@BossOfEsports) | |

### UMA Voters (Dispute Resolution Specialists)
| Account | Notes |
|---------|-------|
| [@The-Joker](https://polymarket.com/@The-Joker) | |
| [@bamesjond](https://polymarket.com/@bamesjond) | |
| [@Car](https://polymarket.com/@Car) | Also in general list |
| [@JJo](https://polymarket.com/@JJo) | Also in general list |
| [@aenews2](https://polymarket.com/@aenews2) | |
| [@ImJustKen](https://polymarket.com/@ImJustKen) | Also in general list |
| [@neformal](https://polymarket.com/@neformal) | |
| [@scout](https://polymarket.com/@scout) | |
| [@Rex416](https://polymarket.com/@Rex416) | |
| [@Infringe](https://polymarket.com/@Infringe) | |
| [@cashy](https://polymarket.com/@cashy) | |
| [@ithinkthisisgod](https://polymarket.com/@ithinkthisisgod) | |
| [@Sonix](https://polymarket.com/@Sonix) | Also in Middle East list |

---

## 5. External Resources & Info Sources

| Resource | URL | Purpose |
|----------|-----|---------|
| Clash Report (X/Twitter) | https://x.com/clashreport | Geopolitical OSINT — source used by top trader @Car |
| BetMoar | https://www.betmoar.fun/ | Dispute status viewer + vote direction checker |
| Cryptomannn Notion (Polymarket guide) | https://cryptomannn-academy.notion.site/POLYMARKET-30dd878f6f55807bb210d832f4fc7624 | "Polymarket from A to Z" stream/guide |
| XTracker | https://xtracker.polymarket.com/ | Official Polymarket resolution source for tweet counting markets |
| Polymarket API docs | https://docs.polymarket.com/ | Official API for programmatic trading |

---

## 6. Key Contacts

| Person | Role | Telegram | Notes |
|--------|------|----------|-------|
| Borkiss | CTO/CAO | https://t.me/borkiss | Technical lead, built bs-p engine and HolyPoly Grail |
| Borkiss | Notes channel | https://t.me/borkiss_notes | Technical posts and updates |
| Spirit | Research & Ideas Lead | https://t.me/crypto_spirit_lt | Curates whale watchlists, market analysis |
| Manager | Sales/Access | https://t.me/cryptomannn_manager | For pricing, demo access |

---

## 7. Key Takeaways for Agent Development

### What They Built That We Can Learn From
1. **Event-to-market correlation** — map real-world data sources (USGS, OSINT, tweet counters) directly to Polymarket markets
2. **Whale tracking as alpha** — following specific profitable accounts by market category gives edge
3. **Insider detection heuristic** — large buys (>$9K) from accounts with <10 trades = potential insider signal
4. **Dispute monitoring** — markets in dispute can create trading opportunities (buy cheap during dispute uncertainty)
5. **N-leg arbitrage** — scanning for YES+NO < $1 across related markets
6. **Kelly criterion position sizing** — mathematical bet sizing prevents overexposure
7. **Implied volatility from spreads** — reading market maker uncertainty from bid/ask spread width

### Open-Source Assets We Can Directly Use
- **bs-p engine** (https://github.com/lubluniky/bs-p) — C/Rust kernel for risk calculations, Kelly sizing, stress tests, Greeks
- **Polymarket API** (https://docs.polymarket.com/) — direct CLOB access for order book data, trading
- **XTracker** (https://xtracker.polymarket.com/) — resolution data for tweet markets

### Strategies Observed in the Community
- **Delta-neutral** strategies on BTC/SOL/ETH 1D markets (CALC board)
- **Weather arbitrage** across 14 cities (SCREENER board)
- **Musk tweet prediction** with mathematical models + activity heatmap
- **15-min BTC scalping** — some traders made 100K+ in 2 days
- **Copy trading** top wallets with 60%+ win rate
- **Dispute edge trading** — buying into disputed markets at discount
