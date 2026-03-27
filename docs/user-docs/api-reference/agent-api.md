# Agent API

Core REST API endpoints for agent lifecycle management, configuration, files, and metadata.

**Note:** All endpoints require JWT Bearer token unless noted. See [Authentication](authentication.md) for details. Full request/response schemas available at [Backend API Docs](http://localhost:8000/docs).

## Endpoints

### Agent CRUD and Lifecycle

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List all agents |
| `/api/agents` | POST | Create agent |
| `/api/agents/{name}` | GET | Get agent details |
| `/api/agents/{name}` | DELETE | Delete agent |
| `/api/agents/{name}/start` | POST | Start container |
| `/api/agents/{name}/stop` | POST | Stop container |
| `/api/agents/{name}/rename` | PUT | Rename agent |

### Agent Info and Files

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/info` | GET | Template metadata |
| `/api/agents/{name}/files` | GET | Workspace file tree |
| `/api/agents/{name}/files/download` | GET | Download file |
| `/api/agents/{name}/logs` | GET | Container logs |
| `/api/agents/{name}/stats` | GET | Live telemetry |

### Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/autonomy` | GET/PUT | Autonomy mode |
| `/api/agents/{name}/read-only` | GET/PUT | Read-only mode |
| `/api/agents/{name}/timeout` | GET/PUT | Execution timeout |
| `/api/agents/{name}/ssh-access` | POST | Generate SSH credentials |

### Credentials

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/credentials/status` | GET | Check credential files |
| `/api/agents/{name}/credentials/inject` | POST | Inject credentials |
| `/api/agents/{name}/credentials/export` | POST | Export encrypted |
| `/api/agents/{name}/credentials/import` | POST | Import encrypted |

### Sharing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/share` | POST | Share with email |
| `/api/agents/{name}/share/{email}` | DELETE | Remove share |
| `/api/agents/{name}/shares` | GET | List shares |

### Schedules

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/schedules` | GET/POST | List/create |
| `/api/agents/{name}/schedules/{id}` | GET/PUT/DELETE | CRUD |
| `/api/agents/{name}/schedules/{id}/enable` | POST | Enable |
| `/api/agents/{name}/schedules/{id}/disable` | POST | Disable |
| `/api/agents/{name}/schedules/{id}/trigger` | POST | Manual trigger |
| `/api/agents/{name}/schedules/{id}/executions` | GET | History |

### Shared Folders

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/folders` | GET/PUT | Folder config |
| `/api/agents/{name}/folders/available` | GET | Mountable folders |
| `/api/agents/{name}/folders/consumers` | GET | Consuming agents |

### Bulk/Fleet

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/context-stats` | GET | All agents context stats |
| `/api/agents/autonomy-status` | GET | All agents autonomy |

## See Also

- [Authentication](authentication.md) -- JWT token usage and login flow
- [Backend API Docs](http://localhost:8000/docs) -- Interactive Swagger documentation
