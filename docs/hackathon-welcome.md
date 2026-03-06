# Nevermined Autonomous Business Hackathon - Welcome Guide

Welcome to the hackathon! Here's everything you need to get started with Trinity.

## Your Trinity Instance

You're already whitelisted. Log in here using the email you registered with - you'll receive a 6-digit code to log in.

https://us15.abilityai.dev/login

## Getting Started Guide

Full instructions, setup, agent templates, payments, business ideas, and suggested hackathon workflow:

https://github.com/Abilityai/trinity/blob/main/hackathon_context.md

## MCP Configuration

The default MCP configuration in the Keys section may have an incorrect URL. Use this configuration instead:

```json
{
  "mcpServers": {
    "trinity": {
      "type": "http",
      "url": "https://mcp-us15.abilityai.dev/mcp",
      "headers": {
        "Authorization": "Bearer {YOUR_TOKEN}"
      }
    }
  }
}
```

Replace `{YOUR_TOKEN}` with your actual token from the Keys section.

## Known Issues & Tips

- **Infinite execution bug:** Some MCP servers can become stuck, causing agents to loop indefinitely. If you see this, email me and we can investigate.
- **New agents need subscription:** When you create a new agent, email me so I can assign a subscription manually. I check periodically but emailing speeds it up.
- **Task timeout:** You can set custom timeouts on manual task executions. The default 15-minute timeout may not be enough for long-running tasks - extend it if needed.
- **Web Terminal:** The hackathon subscription doesn't work in the Web Terminal tab. If you've configured your own API key, Web Terminal works fine. Otherwise, use the Tasks and Chat tabs.
- **Stateless execution:** Each task execution is independent - it's not aware of previous task runs. It only knows about the current workspace state.
- **Housekeeping:** If you've abandoned an agent and don't plan to use it, please shut it down or let me know. This frees up resources for everyone.

## Contact

If you need help or have questions:
- **Email:** eugene@ability.ai
- **Discord:** eugenevyborov_03760
