---
date: 2026-04-21T14:00:00
channel: discord:updates, slack:updates, telegram:updates
---

Trinity weekly update

• Launched docs.ability.ai — searchable public documentation site
• Ask Trinity Q&A agent live in two places: floating help widget in Trinity UI and on docs.ability.ai — powered by Vertex AI Search over the full docs corpus
• Redis Streams event bus for WebSocket delivery — reconnect replay, missed-event catchup, client eviction on repeated failures (RELIABILITY-003, #306)
• OpenTelemetry distributed tracing across multi-agent calls (#305)
• Scheduler retry mechanism for failed executions (#271)
• Persistent async task backlog — tasks survive restarts, FIFO drain (BACKLOG-001)
• Guardrails Phase 1 — deterministic safety enforcement (GUARD-001, #315)
• Platform audit trail Phase 1 — append-only audit_log with 365-day retention (#20)
• Telegram: voice transcription via Gemini, file upload support, group chat with sender identity and proactive messaging, group auth mode (#318, #354, #349, #311)
• Git: self-hosted git URL support, per-agent GitHub PAT, operator-readable conflict modal with parallel-history detection and branch ownership enforcement (#387, #347, #382-386)
• Proactive agent-to-user messaging via send_message MCP tool (#321)
• Agent self-execute with optional result injection (#264)
• SSH access restricted to admin-only
