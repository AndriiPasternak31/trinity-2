# Voice Chat

Real-time voice conversations with agents via Gemini 2.5 Flash Native Audio model (~280ms latency). Audio streams bidirectionally through a backend WebSocket proxy.

## How It Works

1. Open an agent's **Chat** tab.
2. Click the microphone button.
3. A voice overlay appears with status, mute, and end controls.
4. Speak -- audio is captured as PCM 16kHz and streamed to the backend WebSocket.
5. The backend proxies audio to the Google Gemini Live API.
6. Agent response audio (PCM 24kHz) plays back in real-time.
7. Transcripts are auto-saved to the chat session with `source="voice"` markers.
8. Chat bubbles display a voice indicator badge for voice messages.

## Requirements

- `GEMINI_API_KEY` configured on the platform.

## Configuration

| Variable | Description |
|----------|-------------|
| `VOICE_ENABLED` | Enable or disable voice chat |
| `VOICE_MODEL` | Gemini model to use for voice |
| `VOICE_MAX_DURATION` | Maximum voice session duration |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/voice/start` | POST | Start a voice session |
| `/api/agents/{name}/voice/stop` | POST | Stop a voice session |
| `/api/agents/{name}/voice/status` | GET | Get session status |
| `/api/agents/{name}/voice/ws` | WebSocket | Bidirectional audio bridge |

## See Also

- [Agent Chat](../agents/agent-chat.md)
- Backend API Docs: http://localhost:8000/docs
