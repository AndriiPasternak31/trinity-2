# Getting Help

Get instant answers about Trinity through the AI-powered documentation assistant, or connect with the community.

## Trinity Docs Q&A Bot

Ask questions about Trinity and get grounded answers from the documentation.

### CLI Usage

```bash
./scripts/ask-trinity.sh "How do I create an agent?"
./scripts/ask-trinity.sh "What credentials do agents need?"
./scripts/ask-trinity.sh "How do I troubleshoot a stuck agent?"
```

### API Usage

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  "https://us-central1-mcp-server-project-455215.cloudfunctions.net/ask-trinity" \
  -d '{"question": "How do I schedule an agent task?"}'
```

**Response:**
```json
{
  "answer": "To schedule an agent task...",
  "state": "SUCCEEDED"
}
```

No authentication required. The bot uses Vertex AI Search with Gemini to generate answers from the onboarding documentation.

## Other Resources

| Resource | Description |
|----------|-------------|
| [GitHub Issues](https://github.com/abilityai/trinity/issues) | Report bugs and request features |
| [GitHub Discussions](https://github.com/abilityai/trinity/discussions) | Ask questions and share ideas |
| [Demo Video](https://youtu.be/SWpNphnuPpQ) | Watch Trinity in action |
| [API Docs](http://localhost:8000/docs) | Interactive Swagger documentation |

## See Also

- [Overview](overview.md) — What is Trinity
- [Setup](setup.md) — Installation and configuration
- [Quick Start](quick-start.md) — Create your first agent
