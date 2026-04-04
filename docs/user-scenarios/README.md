# User Scenarios

Concrete, step-by-step paths a user takes to accomplish a goal with Trinity. Each scenario documents the actions, expected results, and common failure modes for a specific task.

## How to Use

- **Developers**: Load relevant scenarios into context before modifying a feature path
- **Reviewers**: Check if a PR breaks steps in any documented scenario
- **New users**: Read scenarios as task-oriented tutorials

## CLI

| Scenario | Persona | Goal |
|----------|---------|------|
| [First-Time Setup](cli/first-time-setup.md) | New user with a Trinity instance | Install CLI, authenticate, verify connection |
| [Deploy Agent](cli/deploy-agent.md) | Developer with a local agent repo | Package and deploy an agent to Trinity |
| [Chat with Agent](cli/chat-with-agent.md) | User with a running agent | Send messages and view responses via CLI |

## Format

All scenarios follow the template defined in `.claude/skills/user-scenario/SKILL.md`. To create new scenarios, run `/user-scenario`.
