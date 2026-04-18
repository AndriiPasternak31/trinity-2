---
name: cornelius-backprop
description: On polygon-vybe position resolution, feed outcome signal to Cornelius for Q-value update.
user-invocable: true
automation: event
event: polygon-vybe.position-resolved
allowed-tools: [Read, Write, Bash, mcp__trinity__chat_with_agent]
---

# Cornelius Backprop

When polygon-vybe resolves a position, parse the reasoning's cited Cornelius
note IDs and call cornelius's `/record-outcome(note_id, outcome, attribution)`
for each.

Closes the trader → Cornelius feedback loop that Eugene's current Oracle-only
Cleon flow leaves open.
