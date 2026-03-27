# Chat API

API endpoints for agent chat, voice, streaming, and public chat access.

**Note:** All endpoints require JWT Bearer token unless noted. See [Authentication](authentication.md) for details. Full request/response schemas available at [Backend API Docs](http://localhost:8000/docs).

## Endpoints

### Authenticated Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/chat` | POST | Send message (stream-json output) |
| `/api/agents/{name}/chat/sessions` | GET | List sessions |
| `/api/agents/{name}/chat/sessions/{id}` | GET | Session with messages |
| `/api/agents/{name}/chat/sessions/{id}/close` | POST | Close session |
| `/api/agents/{name}/chat/history/persistent` | GET | Persistent history |
| `/api/agents/{name}/chat/history` | DELETE | Reset session |
| `/api/agents/{name}/activity` | GET | Activity summary |

### Voice Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/voice/start` | POST | Start voice session |
| `/api/agents/{name}/voice/stop` | POST | Stop session |
| `/api/agents/{name}/voice/status` | GET | Session status |
| `/api/agents/{name}/voice/ws` | WS | Audio WebSocket bridge |

### Public Chat (no auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/public/chat/{token}` | POST | Public chat |
| `/api/public/history/{token}` | GET | Public history |

### Paid Chat (x402)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/paid/{agent_name}/chat` | POST | Paid chat (402/200) |
| `/api/paid/{agent_name}/info` | GET | Payment requirements |

### Task Execution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/task` | POST | Submit task |
| `/api/agents/{name}/executions` | GET | List executions |
| `/api/agents/{name}/executions/{id}` | GET | Execution details |

## See Also

- [Authentication](authentication.md) -- JWT token usage and login flow
- [Agent API](agent-api.md) -- Agent lifecycle and configuration endpoints
- [Backend API Docs](http://localhost:8000/docs) -- Interactive Swagger documentation
