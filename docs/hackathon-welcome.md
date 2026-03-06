# Nevermined Autonomous Business Hackathon - Welcome Guide

Welcome to the hackathon! Here's everything you need to get started with Trinity.

## Your Trinity Instance

You're already whitelisted. Log in here using the email you registered with - you'll receive a 6-digit code to log in.

https://us15.abilityai.dev/login

## Watch These First

- **Cornelius Demo** (Research Agent in action): https://youtu.be/yD3w1GBFtvY
- **Trinity Platform Demo** (Full walkthrough): https://youtu.be/i-4_7tcui30

## Getting Started Guide

Full instructions, setup, agent templates, and suggested hackathon workflow:
https://github.com/Abilityai/trinity/blob/main/hackathon_context.md

## Repos

- **Trinity Platform** (open source): https://github.com/Abilityai/trinity
- **Abilities SDK** (agent skills, memory, deployment): https://github.com/Abilityai/abilities

### Agent Templates - Fork These as Starting Points

- **Cornelius** (Research): https://github.com/Abilityai/cornelius
- **Ruby** (Content & Marketing): https://github.com/Abilityai/ruby
- **Outbound** (Sales & Outreach): https://github.com/abilityai/outbound-agent
- **Webmaster** (Website): https://github.com/Abilityai/webmaster

## Payments

To receive payments via Nevermined's pay-per-request model, make sure your purchasers have the correct plan ID and agent ID. Common issues come from mismatches between these two values.

- **Purchasing guide** - how to correctly communicate with Trinity-based agents to make payments: https://github.com/Abilityai/trinity/blob/main/docs/NEVERMINED_TRINITY_PURCHASING_GUIDE.md
- **Purchaser agent** - a working Claude Code-based agent that connects to Trinity agents and purchases services. Use as an example or starting point: https://github.com/Abilityai/nevermined-purchaser

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

## Business Ideas

Here are some ideas you can build using Trinity + Nevermined payments. All work with the agent templates above and can be monetized with Nevermined's pay-per-request model - customers pay, your agents do the work, settlement happens on-chain.

1. **Deep Research Bureau** - Customers pay per research report - market analysis, competitor breakdowns, technology assessments. Use Cornelius for research, Ruby to format the deliverable. Only needs web search.

2. **SEO Audit Agency** - Webmaster crawls and analyzes a customer's website for SEO issues, accessibility problems, and performance recommendations. Pay per audit. Only needs the target URL.

3. **Content Factory** - Pay-per-piece blog posts, social media threads, product descriptions, email sequences. Customer submits a brief, gets polished content back. Ruby handles it all.

4. **Code Review Service** - Agent reviews GitHub repositories or code snippets for security vulnerabilities, best practices, and quality issues. Needs one GitHub token (free to create). Pay per review.

5. **Due Diligence Reports** - For investors and founders. Cornelius compiles company and market due diligence from public sources - financials, news, team backgrounds, competitive landscape. Pay per report.

6. **Business Plan Generator** - Multi-agent pipeline: Cornelius researches the market and competitors, Ruby writes the executive summary and full plan, Webmaster generates a landing page. Pay per plan.

7. **Newsletter-as-a-Service** - Cornelius monitors topics and curates weekly or daily newsletters. Ruby writes and formats them. Customer defines the niche, pays per edition.

8. **Contract & Proposal Reviewer** - Customer uploads a contract or RFP. Agent analyzes for risks, missing clauses, unfavorable terms, and suggests redlines. Pure text analysis. Pay per document.

9. **Technical Documentation Agency** - Point it at a GitHub repo and it generates README, API docs, architecture guides, and onboarding docs. Needs one GitHub token. Pay per repo documented.

10. **Grant & RFP Writing Service** - Multi-agent: Cornelius researches the grant/RFP requirements and past winners, Ruby drafts the application with proper formatting and compliance. Pay per submission.

The multi-agent ideas are especially strong for the hackathon - they showcase Trinity's agent collaboration and make for impressive demos.

## Tips

The shared instance runs on my Anthropic subscription. If you hit rate limits, you can configure your own API key in Settings, or spin up your own local Trinity instance using the repo above.

## Contact

If you need help or have questions:
- **Email:** eugene@ability.ai
- **Discord:** eugenevyborov_03760
