# Feature: Agent Avatars (AVATAR-001, AVATAR-002)

## Overview
AI-generated circular avatars for agents using Gemini image generation, with a reference image system for quick variations, two-button hover UI, and fallback to deterministic gradient initials.

## User Story
As an agent owner, I want to generate a custom avatar for my agent from a text description, and quickly regenerate variations without re-entering my prompt, so that my agents are visually distinguishable across the platform.

## Entry Points
- **UI (Generate/Edit)**: `src/frontend/src/components/AgentHeader.vue:4-49` - Two-button hover overlay (regenerate + edit) or camera icon
- **UI (Display)**: `src/frontend/src/components/AgentAvatar.vue` - Reusable avatar component (5 sizes)
- **UI (Modal)**: `src/frontend/src/components/AvatarGenerateModal.vue` - Generation modal with reference preview
- **API (Generate)**: `POST /api/agents/{agent_name}/avatar/generate`
- **API (Regenerate)**: `POST /api/agents/{agent_name}/avatar/regenerate`
- **API (Serve display)**: `GET /api/agents/{agent_name}/avatar`
- **API (Serve reference)**: `GET /api/agents/{agent_name}/avatar/reference`
- **API (Identity)**: `GET /api/agents/{agent_name}/avatar/identity`
- **API (Delete)**: `DELETE /api/agents/{agent_name}/avatar`

---

## Frontend Layer

### Components

#### AgentAvatar.vue (reusable display component)
- **File**: `src/frontend/src/components/AgentAvatar.vue`
- Props: `name` (required), `avatarUrl` (nullable), `size` (sm/md/lg/xl/2xl)
- Sizes: sm=24px, md=32px, lg=48px, xl=64px, 2xl=96px
- Shows `<img>` when `avatarUrl` is set; on `@error` falls back to initials
- Fallback: deterministic gradient from agent name hash + 2-letter initials
- Gradient uses `hsl(hash%360, 65%, 45%)` to `hsl((hash+40)%360, 65%, 55%)`

#### AgentHeader.vue (avatar trigger - two-button hover UI with crossfade)
- **File**: `src/frontend/src/components/AgentHeader.vue:4-49`
- Avatar sits on left edge of card at `absolute left-0 top-3 -translate-x-1/2` (50% in, 50% out)
- Wrapped in indigo ring border (`border-[3px] border-indigo-400`) with `overflow-hidden`
- **Crossfade transition** (AVATAR-002): Avatar wrapped in `<Transition name="avatar-crossfade">` inside a `relative w-24 h-24` container. Both leaving and entering elements are `absolute inset-0`, creating a true crossfade (1s ease) when `emotionAvatarUrl` changes.
- Two hover states:
  1. **Avatar exists with prompt**: Two buttons side by side:
     - Left: refresh icon (circular arrows) - emits `cycle-emotion` (instant emotion swap)
     - Right: pencil icon - emits `open-avatar-modal` (open modal for new reference)
  2. **No avatar or no prompt**: Single camera icon - emits `open-avatar-modal`
- Only visible to owners (`agent.can_share && !agent.is_system`)
- Props: `hasAvatarPrompt` (Boolean), `emotionAvatarUrl` (String, nullable)
- Emits: `open-avatar-modal`, `cycle-emotion`

#### AvatarGenerateModal.vue (generation modal with reference preview)
- **File**: `src/frontend/src/components/AvatarGenerateModal.vue`
- Props (line 86-92): `show`, `agentName`, `initialPrompt`, `currentAvatarUrl`, `hasReference` (Boolean)
- Emits: `close`, `updated`
- **Reference preview** (line 7-25): When `hasReference` is true, shows:
  - Left: small (w-16 h-16) reference image loaded from `/api/agents/{name}/avatar/reference?v={Date.now()}`
  - Arrow chevron icon between images
  - Right: current avatar via AgentAvatar component (xl size)
  - Labels "Reference" and "Current" beneath each
- **Generate button label** (line 73): Shows "New Reference" when `hasReference` is true, otherwise "Generate"
- **Generate action** (line 108-124): calls `POST /api/agents/{agentName}/avatar/generate` with `{identity_prompt}`
- **Remove Avatar** (line 126-139): calls `DELETE /api/agents/{agentName}/avatar`
- Contains textarea for identity prompt (500 char max, line 31-38)

#### Usage Locations

| Location | File | Line | Size | Context |
|----------|------|------|------|---------|
| Agent Detail Header | `src/frontend/src/components/AgentHeader.vue` | 6 | 2xl | Overlapping left edge of card, ring border, hover overlay |
| Dashboard Graph Nodes | `src/frontend/src/components/AgentNode.vue` | 28 | md | In node header, before agent name label |
| Agents List (desktop) | `src/frontend/src/views/Agents.vue` | 272 | sm | In agent row, before name link |
| Agents List (tablet) | `src/frontend/src/views/Agents.vue` | 442 | sm | In agent row, after status dot |
| Agents List (mobile) | `src/frontend/src/views/Agents.vue` | 585 | sm | In agent row, after status dot |

### State Management

No dedicated store. Avatar state is managed locally in AgentDetail.vue:

- `showAvatarModal = ref(false)`
- `avatarIdentityPrompt = ref('')`
- `avatarHasReference = ref(false)`
- `availableEmotions = ref([])` — list of emotion names from API (AVATAR-002)
- `emotionAvatarUrl = ref(null)` — current emotion URL, overrides base avatar (AVATAR-002)
- `emotionCycleTimer = ref(null)` — setInterval handle for 30s cycling (AVATAR-002)
- `loadAvatarIdentity()` called on mount
- `@open-avatar-modal="showAvatarModal = true"` handler on AgentHeader
- `@cycle-emotion="cycleEmotion"` handler on AgentHeader — instant emotion swap (AVATAR-002)
- `:has-avatar-prompt` and `:emotion-avatar-url` props passed to AgentHeader
- `AvatarGenerateModal` component with `has-reference` prop

### API Calls

```javascript
// Load identity prompt + reference status on mount (AgentDetail.vue:638-648)
const response = await axios.get(`/api/agents/${agent.value.name}/avatar/identity`, {
  headers: authStore.authHeader
})
avatarIdentityPrompt.value = response.data.identity_prompt || ''
avatarHasReference.value = response.data.has_reference || false

// Generate avatar (AvatarGenerateModal.vue:114) — creates BOTH display + reference
await axios.post(`/api/agents/${agentName}/avatar/generate`, {
  identity_prompt: identityPrompt
})

// Load available emotions (AgentDetail.vue — AVATAR-002)
const response = await axios.get(`/api/agents/${agent.value.name}/avatar/emotions`)
availableEmotions.value = response.data.emotions || []

// Remove avatar + reference (AvatarGenerateModal.vue:131)
await axios.delete(`/api/agents/${agentName}/avatar`)
```

### Avatar URL Construction

The avatar URL includes a cache-busting `?v=` timestamp query parameter:

```javascript
// Backend constructs URL in two places:
// 1. agents.py:312 (single agent detail)
avatar_url = f"/api/agents/{agent_name}/avatar?v={identity['updated_at']}"

// 2. helpers.py:157 (agent list batch query)
avatar_url = f"/api/agents/{agent_name}/avatar?v={avatar_updated_at}"
```

The `avatar_url` field is included in agent data returned by both `GET /api/agents` (list) and `GET /api/agents/{name}` (detail).

### Data Flow for Dashboard Nodes

```
helpers.py:get_accessible_agents() -> agent_dict["avatar_url"]
  -> stores/network.js:460 -> avatarUrl: agent.avatar_url || null
    -> AgentNode.vue:28 -> <AgentAvatar :avatar-url="data.avatarUrl" />
```

System agents also get avatarUrl at `stores/network.js:426`.

### On Avatar Updated (refresh cycle)

```
AvatarGenerateModal emits 'updated'
  -> AgentDetail.vue @updated="onAvatarUpdated"
    -> onAvatarUpdated():
      1. await loadAgent()          -- re-fetches agent with new avatar_url (cache-busted)
      2. await loadAvatarIdentity() -- re-fetches identity prompt + reference status
      3. stopEmotionCycling()       -- old emotions are invalid (AVATAR-002)
      4. Poll every 15s for new emotions (up to 12 attempts / 3 min)
      5. startEmotionCycling() once any emotions appear
```

### On Cycle Emotion (instant swap, AVATAR-002)

```
AgentHeader emits 'cycle-emotion'
  -> AgentDetail.vue @cycle-emotion="cycleEmotion"
    -> cycleEmotion():
      1. Pick random emotion from availableEmotions
      2. Set emotionAvatarUrl to /api/agents/{name}/avatar/emotion/{emotion}?v={timestamp}
      3. AgentHeader crossfade transition renders new image (1s ease)
```

---

## Backend Layer

### Router: `src/backend/routers/avatar.py`

Registered in `src/backend/main.py:356`:
```python
app.include_router(avatar_router)  # Agent Avatars (AVATAR-001)
```

Prefix: `/api/agents`, Tags: `["avatars"]`

#### Endpoint: GET `/{agent_name}/avatar` (line 31)
- **Auth**: None (public asset)
- **Returns**: `FileResponse` with PNG from `/data/avatars/{agent_name}.png`
- **Cache**: `Cache-Control: public, max-age=86400` (24 hours)
- **Error**: 404 if no avatar file exists

#### Endpoint: GET `/{agent_name}/avatar/reference` (line 45)
- **Auth**: None (public asset)
- **Returns**: `FileResponse` with PNG from `/data/avatars/{agent_name}_ref.png`
- **Cache**: `Cache-Control: no-cache` (always fresh -- reference may change on re-generate)
- **Error**: 404 if no reference image exists

#### Endpoint: GET `/{agent_name}/avatar/identity` (line 59)
- **Auth**: Required (access control check via `can_user_access_agent`)
- **Returns**: `{agent_name, identity_prompt, updated_at, has_avatar, has_reference}`
- **`has_reference`** (line 77): checks `Path("/data/avatars/{agent_name}_ref.png").exists()`
- **Error**: 403 if user cannot access agent

#### Endpoint: POST `/{agent_name}/avatar/generate` (line 81)
- **Auth**: Required (owner or admin only)
- **Request Body**: `{identity_prompt: string}` (max 500 chars)
- **Flow**:
  1. Validate ownership (owner or admin, line 88-96)
  2. Validate prompt (non-empty, <= 500 chars, lines 98-103)
  3. Check image generation service availability (GEMINI_API_KEY, lines 105-110)
  4. Call `service.generate_image(prompt, use_case="avatar", aspect_ratio="1:1", refine_prompt=True, agent_name=agent_name)` (lines 112-118)
  5. Save PNG to BOTH `/data/avatars/{agent_name}.png` AND `/data/avatars/{agent_name}_ref.png` (lines 124-128)
  6. Update DB: `db.set_avatar_identity(agent_name, prompt, timestamp)` (lines 131-132)
- **Returns**: `{agent_name, identity_prompt, refined_prompt, updated_at}`
- **Key**: First generation saves same image as both display and reference. Subsequent regenerations only update display.
- **Errors**: 404 (not found), 403 (not owner), 400 (empty/too long), 501 (no API key), 422 (generation failed)

#### Endpoint: POST `/{agent_name}/avatar/regenerate` (line 144)
- **Auth**: Required (owner or admin only)
- **Request Body**: None (empty POST)
- **Flow**:
  1. Validate ownership (lines 150-157)
  2. Check reference image exists at `/data/avatars/{agent_name}_ref.png` (lines 160-162)
  3. Check stored identity prompt exists in DB (lines 164-166)
  4. Check image generation service availability (lines 168-173)
  5. Read reference bytes: `ref_path.read_bytes()` (line 175)
  6. Call `service.generate_variation(prompt, reference_image=reference_bytes, aspect_ratio="1:1", agent_name=agent_name)` (lines 176-181)
  7. Save PNG to display only: `/data/avatars/{agent_name}.png` (lines 187-188) -- reference stays unchanged
  8. Update DB timestamp: `db.set_avatar_identity(agent_name, identity["identity_prompt"], now)` (line 191)
- **Returns**: `{agent_name, identity_prompt, updated_at}`
- **Errors**: 404 (agent not found / no reference image / no identity prompt), 403, 501, 422

#### Endpoint: DELETE `/{agent_name}/avatar` (line 202)
- **Auth**: Required (owner or admin only)
- **Flow**:
  1. Validate ownership (lines 208-215)
  2. Delete both files: `/data/avatars/{agent_name}.png` AND `/data/avatars/{agent_name}_ref.png` (lines 218-223)
  3. Clear DB: `db.clear_avatar_identity(agent_name)` (line 226)
- **Returns**: `{message: "Avatar removed for {agent_name}"}`

### Image Generation Pipeline

The avatar generation uses the shared image generation service (IMG-001).

**File**: `src/backend/services/image_generation_service.py`

**Models** (lines 29-30):
- Text model (prompt refinement): `gemini-2.0-flash` (fast text generation)
- Image model (image generation): `gemini-3.1-flash-image-preview` (latest image model)

**Generate flow** (`generate_image()`, line 71):
1. **Prompt Refinement** (lines 122-128): Gemini 2.0 Flash rewrites the raw identity prompt using avatar-specific best practices
2. **Image Generation** (lines 131-156): Gemini 3.1 Flash Image Preview generates the actual PNG

**Variation flow** (`generate_variation()`, line 313):
1. Wraps the stored prompt with variation instructions (lines 343-349):
   ```
   "Generate a new variation of this portrait. Keep the same subject identity,
   features, and overall style but create a fresh natural variation -- slightly
   different expression, micro-changes in lighting angle, or subtle pose shift.
   The result should look like a different photo from the same session."
   ```
2. Calls `_call_gemini_image()` with reference image bytes as `inlineData` part (lines 351-357)

**Reference image support in `_call_gemini_image()`** (line 232):
- Accepts optional `reference_image: bytes` and `reference_mime_type: str` parameters
- When reference provided, it is included as an `inlineData` part before the text prompt (lines 256-262)
- The parts list is: `[{inlineData: {mimeType, data: base64}}, {text: prompt}]`

### Avatar Prompt Engineering (Dark Mode Style)

**File**: `src/backend/services/image_generation_prompts.py:166-227`

The avatar prompt (`AVATAR_BEST_PRACTICES`) uses a **consistency-through-extreme-specificity** approach with a **dark mode aesthetic** that matches the Trinity UI:

**Fixed Technical Specification** (appended to every refined prompt):
- **Framing**: extreme close-up, face filling 85-90% of frame, centered, front-facing
- **Background**: dark slate-navy (#1a1f2e) to dark charcoal (#111827) -- matches UI `bg-gray-900`
- **Lighting**: single soft key light upper-left 45deg, cool 5600K color temperature, subtle indigo-blue rim light (#6366f1) on right edge -- matches UI indigo accent color
- **Color grading**: modern digital, cool desaturated palette, deep rich shadows, clean highlight rolloff, no film grain, sharp and clean
- **Lens**: 85mm f/1.4 prime, shallow DOF on background only
- **Style**: modern studio portrait photograph, photographic realism
- **No text, no watermarks, no labels**
- **Circular crop safe**: nothing important in corners

**Subject description rules**: preserve ALL user details literally, add only missing defaults (expression, pose), be literal not creative, front-facing or very slight 3/4 turn.

### Avatar URL in Agent Data

Two code paths construct the `avatar_url` field:

1. **Single agent detail** (`src/backend/routers/agents.py:309-314`):
   ```python
   identity = db.get_avatar_identity(agent_name)
   if identity and identity.get("updated_at"):
       agent_dict["avatar_url"] = f"/api/agents/{agent_name}/avatar?v={identity['updated_at']}"
   ```

2. **Agent list (batch)** (`src/backend/services/agent_service/helpers.py:154-159`):
   ```python
   avatar_updated_at = metadata.get("avatar_updated_at")
   agent_dict["avatar_url"] = (
       f"/api/agents/{agent_name}/avatar?v={avatar_updated_at}"
       if avatar_updated_at else None
   )
   ```

### Avatar Cleanup on Agent Operations

**On Delete** (`src/backend/routers/agents.py:422-428`):
```python
avatar_path = Path("/data/avatars") / f"{agent_name}.png"
if avatar_path.exists():
    avatar_path.unlink()
```
**NOTE**: The delete path only removes `{agent_name}.png`. It does NOT remove `{agent_name}_ref.png`. However, the avatar router's own `DELETE /{agent_name}/avatar` endpoint (line 202) does clean up both files. The gap is in the agent deletion code path in `agents.py`.

**On Rename** (`src/backend/routers/agents.py:1511-1518`):
```python
old_avatar = Path("/data/avatars") / f"{agent_name}.png"
new_avatar = Path("/data/avatars") / f"{sanitized_name}.png"
if old_avatar.exists():
    old_avatar.rename(new_avatar)
```
**NOTE**: The rename path only renames `{agent_name}.png`. It does NOT rename `{agent_name}_ref.png`. This means after a rename, the reference image is orphaned and regeneration will fail (404 "No reference image found").

### Configuration

```python
# src/backend/config.py:104
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
```

Avatar directory: `/data/avatars/` (created on first generate, bind-mounted from host)

Files per agent:
- `/data/avatars/{agent_name}.png` -- display avatar (served by `GET /avatar`)
- `/data/avatars/{agent_name}_ref.png` -- reference image (served by `GET /avatar/reference`)

---

## Data Layer

### Schema Changes

**Table**: `agent_ownership` (modified)

Two columns added by migration #24:

```sql
avatar_identity_prompt TEXT,  -- User's character description
avatar_updated_at TEXT         -- ISO timestamp for cache-busting
```

**File**: `src/backend/db/schema.py:65-66` (in CREATE TABLE definition)

### Migration #24

**File**: `src/backend/db/migrations.py:647-666`
**Function**: `_migrate_agent_avatar_columns(cursor, conn)`

```python
new_columns = [
    ("avatar_identity_prompt", "TEXT"),
    ("avatar_updated_at", "TEXT"),
]
# Uses ALTER TABLE ADD COLUMN (idempotent check via PRAGMA table_info)
```

### Database Operations

**File**: `src/backend/db/agents.py:802-845` (AgentOperations class)

| Method | Line | Description |
|--------|------|-------------|
| `set_avatar_identity(agent_name, prompt, updated_at)` | 806 | UPDATE agent_ownership SET avatar_identity_prompt, avatar_updated_at |
| `get_avatar_identity(agent_name)` | 818 | SELECT avatar_identity_prompt, avatar_updated_at |
| `clear_avatar_identity(agent_name)` | 834 | UPDATE SET NULL for both columns |

**Delegation**: `src/backend/database.py:418-425` delegates to `self._agent_ops`:
```python
def set_avatar_identity(self, agent_name, prompt, updated_at):
    return self._agent_ops.set_avatar_identity(agent_name, prompt, updated_at)
def get_avatar_identity(self, agent_name):
    return self._agent_ops.get_avatar_identity(agent_name)
def clear_avatar_identity(self, agent_name):
    return self._agent_ops.clear_avatar_identity(agent_name)
```

### Batch Query Integration

The `get_all_agent_metadata()` method (`src/backend/db/agents.py:846`) includes `avatar_updated_at` in its single-query result (line 880) to avoid N+1 queries on the agent list page.

---

## Side Effects

- **File System**: Avatar PNGs stored at `/data/avatars/{agent_name}.png` (display) and `/data/avatars/{agent_name}_ref.png` (reference)
- **No WebSocket**: Avatar changes do not broadcast WebSocket events (user refreshes to see update)
- **No Activity Tracking**: Avatar generation is not tracked as an agent activity
- **Cache-busting**: `?v={updated_at}` query param forces browser cache invalidation on re-generation
- **Reference image no-cache**: Reference endpoint uses `Cache-Control: no-cache` to always serve fresh content

---

## Error Handling

| Error Case | HTTP Status | Message |
|------------|-------------|---------|
| Avatar file not found | 404 | "No avatar found" |
| Reference image not found | 404 | "No reference image found" |
| No reference for regenerate | 404 | "No reference image found. Generate an avatar first." |
| No identity prompt for regenerate | 404 | "No identity prompt found. Generate an avatar first." |
| Agent not in DB | 404 | "Agent not found" |
| User not owner/admin (generate) | 403 | "Only the agent owner can generate avatars" |
| User not owner/admin (regenerate) | 403 | "Only the agent owner can regenerate avatars" |
| User not owner/admin (delete) | 403 | "Only the agent owner can remove avatars" |
| User cannot access agent | 403 | "Access denied" |
| Empty prompt | 400 | "identity_prompt cannot be empty" |
| Prompt too long | 400 | "identity_prompt must be 500 characters or less" |
| No GEMINI_API_KEY | 501 | "Image generation not available: GEMINI_API_KEY not configured" |
| Generation failed | 422 | Error message from generation service |

---

## Testing

### Prerequisites
- Backend running at `http://localhost:8000`
- `GEMINI_API_KEY` configured in `.env`
- At least one agent created
- Logged in as agent owner or admin

### Test Steps

1. **Generate Avatar (First Time)**
   **Action**: Navigate to agent detail, hover over avatar area (left edge of header), click camera icon, enter "a wise owl with spectacles", click Generate
   **Expected**: Modal shows spinner, then closes. Avatar appears in header with indigo ring border.
   **Verify**: `GET /api/agents/{name}/avatar` returns PNG. `GET /api/agents/{name}/avatar/reference` also returns PNG (same image). Avatar displays in agent list, dashboard nodes.

2. **Regenerate Variation (Two-Button UI)**
   **Action**: Hover over avatar. Two buttons appear (refresh + pencil). Click the refresh icon (left button).
   **Expected**: Spinner overlay on avatar while generating. New avatar appears (variation of reference). Reference image unchanged.
   **Verify**: `GET /api/agents/{name}/avatar` returns new image. `GET /api/agents/{name}/avatar/reference` returns original reference. DB `avatar_updated_at` changed.

3. **Change Prompt (New Reference)**
   **Action**: Hover over avatar, click pencil icon (right button). Modal opens showing reference (small, left) + arrow + current (large, right). Change prompt to "a friendly robot". Click "New Reference".
   **Expected**: New avatar generated from new prompt. Both display and reference updated.
   **Verify**: Both `/avatar` and `/avatar/reference` return new images.

4. **Modal Reference Preview**
   **Action**: Open avatar modal when reference exists.
   **Expected**: Small reference image (left), arrow icon, current avatar (right) displayed above the prompt input. Generate button says "New Reference".

5. **Remove Avatar**
   **Action**: Open avatar modal, click "Remove Avatar"
   **Expected**: Avatar removed, fallback to gradient initials. Both display and reference files deleted.
   **Verify**: Files deleted. DB columns cleared. `avatar_url` is null in agent data.

6. **Fallback Display**
   **Action**: View agent without avatar
   **Expected**: Circular gradient with 2-letter initials (deterministic color from name)
   **Verify**: Same gradient color every time for same agent name.

7. **Avatar Survives Rename**
   **Action**: Rename agent from "my-agent" to "new-agent"
   **Expected**: Display avatar file renamed from `my-agent.png` to `new-agent.png`. Avatar still displays after rename.
   **Known Gap**: Reference file `my-agent_ref.png` is NOT renamed. Regeneration will fail after rename until a new avatar is generated.

8. **Avatar Cleaned Up on Delete**
   **Action**: Delete agent with avatar
   **Expected**: Display avatar file removed from `/data/avatars/`.
   **Known Gap**: Reference file `{agent}_ref.png` is NOT cleaned up by the agent delete path in `agents.py:424`. It remains as an orphan.

9. **No API Key**
   **Action**: Remove GEMINI_API_KEY, try to generate avatar
   **Expected**: 501 error "Image generation not available"

10. **Non-Owner Cannot Generate**
    **Action**: View a shared agent as non-owner
    **Expected**: Hover overlay does not appear. Avatar modal cannot be triggered.
    **Verify**: `agent.can_share` is false, overlay `v-if` hides it.

11. **Regenerate Without Reference**
    **Action**: Call `POST /api/agents/{name}/avatar/regenerate` when no reference exists
    **Expected**: 404 "No reference image found. Generate an avatar first."

---

## Known Gaps

~~1. **Agent delete does not clean up `_ref.png`**: Fixed in AVATAR-002 — agents.py now deletes both `_ref.png` and all `_emotion_*.png` files.~~
~~2. **Agent rename does not rename `_ref.png`**: Fixed in AVATAR-002 — agents.py now renames `_ref.png` and all `_emotion_*.png` files.~~

No known gaps remaining after AVATAR-002.

---

## Emotion Variants (AVATAR-002)

### Overview

After generating a new avatar, the backend automatically generates 8 emotion variants in the background using `asyncio.create_task()`. The AgentDetail page cycles through available emotions every 30 seconds.

### Emotions

| Emotion | Expression Description |
|---------|----------------------|
| happy | warm, genuine smile with bright, joyful eyes |
| thoughtful | reflective, contemplative expression with pensive gaze |
| surprised | wide, alert eyes with raised eyebrows |
| determined | firm, resolute expression with focused eyes |
| calm | serene, relaxed expression with soft eyes |
| amused | playful half-smile with sparkling eyes |
| curious | inquisitive expression with raised eyebrow |
| confident | self-assured expression with steady gaze |

### Storage

Files per agent (in addition to base + ref):
- `/data/avatars/{agent_name}_emotion_{emotion}.png` (8 files)

### Backend

#### Constants (`src/backend/services/image_generation_prompts.py`)
- `AVATAR_EMOTIONS` — list of 8 emotion names
- `AVATAR_EMOTION_PROMPTS` — dict mapping each emotion to a facial expression description

#### Service Method (`src/backend/services/image_generation_service.py`)
- `generate_emotion_variation(emotion_prompt, reference_image, ...)` — calls `_call_gemini_image()` directly with caller-supplied prompt + reference image

#### Router (`src/backend/routers/avatar.py`)

**Background function**: `_generate_emotions_background(agent_name, reference_bytes, identity_prompt)`
- Fire-and-forget via `asyncio.create_task()`
- Iterates 8 emotions sequentially (avoids API rate limits)
- Guards at each iteration: checks reference file still exists and content matches
- Individual failures logged but don't stop the loop

**New endpoints**:
- `GET /{agent_name}/avatar/emotions` — No auth. Returns `{"agent_name", "emotions": ["happy", ...]}`
- `GET /{agent_name}/avatar/emotion/{emotion}` — No auth. Serves PNG with 24h cache. Validates emotion name.

**Modified endpoints**:
- `POST /{agent_name}/avatar/generate` — After saving avatar+ref, deletes old emotion files, kicks off background emotion generation
- `DELETE /{agent_name}/avatar` — Also deletes all `_emotion_{name}.png` files

#### Agent Operations (`src/backend/routers/agents.py`)
- **Delete** — Also deletes `_emotion_{name}.png` files
- **Rename** — Also renames `_emotion_{name}.png` files

### Frontend

#### AgentHeader.vue
- New prop: `emotionAvatarUrl` (String, default null)
- When set, overrides `agent.avatar_url` on the `AgentAvatar` component

#### AgentDetail.vue

**State**:
- `availableEmotions` — list of available emotion names from API
- `emotionAvatarUrl` — current emotion URL (null = use base avatar)
- `emotionCycleTimer` — setInterval handle

**Functions**:
- `loadAvailableEmotions()` — GET `/api/agents/{name}/avatar/emotions`
- `cycleEmotion()` — picks random emotion, sets URL with cache-bust
- `startEmotionCycling()` — clears old timer, calls `cycleEmotion()`, sets 30s interval
- `stopEmotionCycling()` — clears interval, resets URL to null

**Lifecycle**:
- `onMounted` — loads emotions + starts cycling
- `onActivated` — reloads emotions + restarts cycling
- `onDeactivated` / `onUnmounted` — stops cycling

**`onAvatarUpdated()`** — stops cycling, clears emotions, polls every 15s for new emotions (up to 12 attempts / 3 min), starts cycling once any appear.

### Scope Limitations
- **No cycling on Agents page or Dashboard** — only AgentDetail
- **No DB schema changes** — emotion state is purely file-based
- **No changes to AvatarGenerateModal** — emotion generation is automatic

---

## Related Flows
- [image-generation.md](image-generation.md) - Shared Gemini image generation pipeline (IMG-001)
- [agent-lifecycle.md](agent-lifecycle.md) - Avatar cleanup on delete
- [agent-rename.md](agent-rename.md) - Avatar file rename on agent rename
- [agent-network.md](agent-network.md) - Avatar display in dashboard graph nodes
- [agents-page-ui-improvements.md](agents-page-ui-improvements.md) - Avatar in agent list rows
