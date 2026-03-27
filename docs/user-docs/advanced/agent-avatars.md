# Agent Avatars

AI-generated avatars for agents using reference images, emotion variants, and default generation.

## Features

- **Reference Image** -- Upload a reference image and the avatar is generated in that style.
- **Variation Regeneration** -- Generate new variations from an existing avatar.
- **Emotion Variants** -- The Agent Detail page cycles through emotion-based avatar variants every 30 seconds.
- **Default Avatar Generation** -- Admin button in Settings generates robot/android-style avatars for all agents without a custom avatar.
- **WebP Conversion** -- Avatars are converted to WebP via Pillow for optimization.
- **Stable Emotion Cache Keys** -- Emotion variants use stable cache keys to avoid redundant generation.
- **Dark Mode Compatible** -- Avatar styling adapts to dark mode.
- **Dashboard Timeline** -- Avatars display in Dashboard Timeline tiles at large size with a border ring.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/avatar` | GET | Serve the agent's current avatar |
| `/api/agents/{name}/avatar` | POST | Generate or upload a new avatar |

## See Also

- [Managing Agents](../agents/managing-agents.md)
- [Dashboard](../operations/dashboard.md)
