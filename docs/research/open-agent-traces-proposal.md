# Proposal: Open Agent Trace Recording & Export for Trinity

**Author:** Andrii Pasternak
**Date:** March 27, 2026
**Status:** Proposal — seeking feedback before implementation

---

## The Opportunity

Today (March 27, 2026), Clement Delangue, CEO of Hugging Face, posted:

> **"We need more open agent traces datasets. Who can help?"**
> — 17.8K views, 122 likes, 33 bookmarks, reposted by HF org

The thread revealed a clear gap:
- **WildPinesAI:** "tracing infra exists everywhere. nobody wants to publish their messy real-world runs, just cherry-picked demos."
- **Clement's response:** "why not? messy is great for training!"
- **Maziyar Panahi (HF):** "we need a cli extension where users can let all the data to be uploaded to HF regularly. but we need strong PII extraction and de-anonymization pipelines"
- **Clement:** "who wants to build this? happy to support!"

Source: https://x.com/ClementDelangue/status/2037530125638455610

## Why Trinity Is Uniquely Positioned

I researched every public agent trace dataset available today:

| Dataset | Source | What It Captures |
|---------|--------|-----------------|
| TRAIL (PatronusAI) | HF Hub | 148 traces from coding agents (GAIA/SWE-Bench) — evaluation only |
| MemGPT function-call-traces | HF Hub | Memory-augmented chatbot conversations |
| SWE-bench experiments | GitHub | Coding agent patches and reasoning traces |
| Agent-X, Jupyter Agent | HF Hub | Task-specific benchmark traces |

**The gap:** Every public dataset is from coding agents or chatbots. Zero datasets exist for **autonomous agents** that:
- Run on schedules (cron-triggered, not human-initiated)
- Use real tools via MCP (file I/O, shell commands, API calls)
- Collaborate with other agents via event subscriptions
- Operate without human supervision for extended periods

**That's exactly what Trinity agents do.** No other platform produces this type of trace data at scale.

## What This Means for Trinity

### Short-term: Visibility & Positioning
- Reply to Clement's thread with a concrete contribution — not a promise, a working feature
- First autonomous agent trace dataset on HF Hub positions Trinity as infrastructure for the open agent ecosystem
- HF CEO is actively looking for collaborators ("happy to support!")

### Medium-term: Product Differentiation
- "Record and export your agent's traces" becomes a Trinity feature no other orchestration platform offers
- Traces double as a debugging/evaluation tool for Trinity users
- Creates a data flywheel: more agents -> more traces -> better training data -> better agents

### Long-term: Distribution Moat
- Trinity becomes the default producer of real autonomous agent traces
- Operational telemetry becomes a distribution channel (researchers cite the dataset, discover Trinity)
- As Codex (independent AI review) put it: *"Trinity turns operational telemetry into a distribution moat — both orchestration runtime and data exhaust pipeline for next-gen agent model research."*

## What We'd Build

### V1: Trace Recording + Download (3-5 days)

**Core idea:** Instrument `agent-server.py` to record every message, tool call, and event during execution as structured JSONL. Add a "Download Trace" button on the execution detail page.

**Trace format (`trinity_trace_v1`):** OpenAI chat-compatible JSONL with Trinity extensions:

```jsonl
{"schema_version":"trinity_trace_v1","trace_id":"exec_abc123","agent_name":"my-agent","template":"github:Org/repo","trigger":"schedule"}
{"turn":1,"role":"system","content":"You are a market analyst...","timestamp":"2026-03-27T16:00:00Z"}
{"turn":2,"role":"user","content":"Run the morning scan","timestamp":"2026-03-27T16:00:00Z"}
{"turn":3,"role":"assistant","content":"Checking watchlist...","tool_calls":[{"id":"tc_1","function":{"name":"mcp_read_file","arguments":"{...}"}}],"model":"claude-sonnet-4-6","tokens":{"input":1200,"output":85}}
{"turn":4,"role":"tool","tool_call_id":"tc_1","name":"mcp_read_file","content":"AAPL\nMSFT\n...","duration_ms":45}
```

**Why this format:**
- Immediately consumable by ML training pipelines (`datasets.load_dataset("json", data_files="trace.jsonl")`)
- OpenAI chat format is the de facto standard researchers already work with
- Trinity-specific extensions (model, tokens, latency, trigger type) add unique metadata
- Each trace includes a `run_metadata.json` with agent config, schedule info, tool inventory, and execution stats

**Architecture:**
- `TraceRecorder` class inside agent containers writes JSONL to shared volume on every event
- Backend serves traces via `GET /api/executions/{id}/trace/bundle` (authenticated)
- Frontend adds "Download Trace" button on execution detail page
- No latency impact on agent execution (<5ms overhead per turn)
- Works with all agents using the standard base image

### V2: HF Hub Publish + PII Redaction (future)
- One-click "Publish to HF Hub" button using `huggingface_hub` library
- PII redaction layer (regex + NER-based scrubbing) before publishing
- Bulk export (all traces for an agent or time range)
- Opt-in per-agent toggle for trace recording

## What I'm Asking

1. **Does this align with Trinity's direction?** Adding trace recording as a feature — is this something we want in the platform?
2. **Timing:** Clement is actively looking for contributors right now. Shipping V1 this week and replying to his thread with a real demo would have maximum impact. Is that pace acceptable?
3. **Open source implications:** The traces would be from Trinity agents running real tasks. Even with PII redaction deferred (V1 traces come from our own agents), are there concerns about publishing agent behavior data publicly?
4. **Scope:** V1 is intentionally minimal — record + download only. V2 (HF publish, PII redaction, bulk export) would follow based on reception. Is this the right scoping?

## References

- Clement's tweet: https://x.com/ClementDelangue/status/2037530125638455610
- TRAIL dataset (benchmark): https://huggingface.co/datasets/PatronusAI/TRAIL
- MemGPT traces (closest format reference): https://huggingface.co/datasets/MemGPT/function-call-traces
- Full technical design doc: available on request (covers schema details, error handling, storage, API specs)
