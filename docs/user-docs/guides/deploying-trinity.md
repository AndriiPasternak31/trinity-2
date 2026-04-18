# Deploying Trinity

Trinity runs your agents 24/7 with scheduling, monitoring, and multi-agent coordination. Choose cloud-hosted for simplicity or self-hosted for complete control.

## Cloud vs Self-Hosted

| | Cloud Hosted (ability.ai) | Self Hosted |
|---|---|---|
| **Infrastructure** | Zero to manage | You manage |
| **Setup time** | 30 seconds | 10-15 minutes |
| **Data location** | ability.ai servers | Your perimeter |
| **Pricing** | Pay-per-agent | Free forever |
| **Best for** | Teams focused on building | Enterprises with compliance requirements |

## Option A: Cloud Hosted (ability.ai)

### Step 1: Create an account

Sign up at [ability.ai](https://ability.ai).

### Step 2: Get your MCP connection URL

After signup, go to **Settings > API Keys** and copy your MCP server URL.

### Step 3: Connect from Claude Code

```bash
/trinity:connect
```

The skill asks for your connection URL and saves it to your config.

### Step 4: Deploy your first agent

```bash
/trinity:onboard
```

Done. Your agent is now running on ability.ai.

## Option B: Self Hosted

### Requirements

- Docker Desktop (or Docker + Docker Compose)
- Git
- 8GB RAM minimum
- Modern web browser

### Step 1: Clone and start

```bash
git clone https://github.com/abilityai/trinity.git
cd trinity
./scripts/deploy/start.sh
```

This builds the base agent image and starts all services (backend, frontend, MCP server, Redis, Vector).

### Step 2: Complete the setup wizard

Open `http://localhost` in your browser. Set your admin password on first visit.

### Step 3: Connect from Claude Code

```bash
/trinity:connect

# When prompted, enter:
# URL: http://localhost:8080/mcp
# Username: admin
# Password: (your admin password)
```

### Step 4: Deploy your first agent

```bash
/trinity:onboard
```

## Key URLs (Self-Hosted)

| Service | URL |
|---------|-----|
| Web UI | http://localhost |
| Backend API docs | http://localhost:8000/docs |
| MCP Server | http://localhost:8080/mcp |

## Managing Services (Self-Hosted)

```bash
# Stop all services
./scripts/deploy/stop.sh

# Start all services
./scripts/deploy/start.sh

# View backend logs
docker-compose logs -f backend

# Rebuild after code changes
docker-compose build
```

## Next Steps

- [Building Agents](building-agents.md) — Create and deploy with Claude Code + abilities
- [Using Trinity](using-trinity.md) — Dashboard, agent management, monitoring

## See Also

- [Quick Start](../getting-started/quick-start.md) — 5-minute agent creation
- [Trinity CLI](../cli/trinity-cli.md) — Command-line deployment
