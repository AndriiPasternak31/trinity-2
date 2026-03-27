# Nevermined x402 Payments

Monetize agents with per-request payments using the Nevermined x402 payment protocol. Users pay per chat message; agents earn credits.

## Concepts

- **x402 Protocol** -- HTTP-native payment protocol. Unauthenticated requests to a paid endpoint return HTTP 402 (Payment Required) with payment instructions.
- **NVM API Key** -- Nevermined platform API key used to verify payments and settle credits.
- **Agent ID** -- The Nevermined-assigned identifier for the agent being monetized.
- **Plan ID** -- The Nevermined plan that defines credit pricing and allocation.
- **Access Token** -- A payment-signature header value that proves the caller has purchased credits.

## How It Works

### Setup (Admin)

1. Open the agent detail page and navigate to the payment settings.
2. Enter the **NVM API Key**, **Agent ID**, and **Plan ID** from Nevermined.
3. Enable payments for the agent.
4. The agent now has a paid chat endpoint: `POST /api/paid/{agent_name}/chat`.

### Payment Flow

```
Client -> POST /api/paid/{agent}/chat (no token)
  <- 402 Payment Required (includes payment info)

Client -> Purchases credits via Nevermined checkout page
Client -> POST /api/paid/{agent}/chat (payment-signature header)
  <- 200 OK (agent response, 1 credit deducted)
```

| Step | Action |
|------|--------|
| 1 | Client sends a chat request without payment credentials |
| 2 | Trinity returns HTTP 402 with Nevermined payment details |
| 3 | Client purchases credits via the Nevermined checkout page |
| 4 | Client retries the request with `payment-signature` header containing the access token |
| 5 | Trinity verifies payment, deducts one credit, routes to agent |
| 6 | Trinity settles the transaction with Nevermined |

### Payment Info (Public)

Call `GET /api/paid/{agent_name}/info` to retrieve payment requirements without authentication. Returns the Agent ID, Plan ID, checkout URL, and credits per request.

## For Agents

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/paid/{agent_name}/chat` | POST | Paid chat (returns 402/403/200) |
| `/api/paid/{agent_name}/info` | GET | Payment requirements (no auth) |
| `/api/nevermined/agents/{name}/config` | POST | Configure payment settings |
| `/api/nevermined/agents/{name}/config` | GET | Get payment configuration |
| `/api/nevermined/agents/{name}/config` | DELETE | Remove payment configuration |
| `/api/nevermined/agents/{name}/config/toggle` | PUT | Enable or disable payments |
| `/api/nevermined/agents/{name}/payments` | GET | Payment history |
| `/api/nevermined/settlement-failures` | GET | Failed settlements (admin) |
| `/api/nevermined/retry-settlement/{log_id}` | POST | Retry failed settlement (admin) |

### MCP Tools

| Tool | Description |
|------|-------------|
| `configure_nevermined` | Set NVM API Key, Agent ID, Plan ID |
| `get_nevermined_config` | Retrieve current payment configuration |
| `toggle_nevermined` | Enable or disable payments |
| `get_nevermined_payments` | View payment history |

## Limitations

- Only one Nevermined plan per agent.
- Settlement failures must be retried manually via the admin endpoint.
- The `payment-signature` header is required on every paid request; there is no session persistence.

## See Also

- [MCP Server](mcp-server.md)
- [Nevermined Documentation](https://docs.nevermined.io/)
