# Plan: Generate Default Avatars (AVATAR-003)

Admin button in Settings to generate avatars for all agents that don't have one yet. Uses the same Gemini pipeline as custom avatars (AVATAR-001) with a generic prompt derived from each agent's name and type. These are real Gemini-generated portraits — same quality as custom avatars, just auto-prompted.

## Approach

**Reuse the existing Gemini image generation pipeline** — same `ImageGenerationService.generate_image()` with `use_case="avatar"` and prompt refinement. For each agent without an avatar, construct a default identity prompt from the agent's name and type (e.g., "A professional AI assistant named Atlas" or "A creative robot named Pixel"). The prompt goes through the same refinement + generation flow as custom avatars.

**Why Gemini (same as custom)?** One pipeline to maintain. The avatar best practices, prompt refinement, technical spec block, and storage all stay identical. Default avatars get the same quality and consistency as custom ones. The only difference is the prompt is auto-generated instead of user-written.

**DB tracking:** Add `is_default_avatar` column so we can distinguish default vs custom avatars, allowing re-runs to skip custom avatars and overwrite stale defaults.

**Sequential generation with progress:** Avatars are generated one at a time (Gemini rate limits). The endpoint returns a summary when complete. No emotion variants or reference images for defaults — those are only for custom avatars.

## Default Identity Prompt Construction

For each agent, build a prompt from available metadata:

```
"{agent_type_description} named {agent_name}"
```

Where `agent_type_description` maps agent type to a stylized robot/android concept:
- `business-assistant` → sleek chrome and navy metallic android executive
- `code-assistant` → matte black android with glowing teal circuit traces
- `research-assistant` → brushed silver robot with amber eyes and spectacle frames
- `creative-assistant` → iridescent holographic android with purple-pink surface
- `data-analyst` → gunmetal robot with grid lines and green glowing eyes
- (default/unknown) → smooth dark metallic android with indigo glowing eyes

Default avatars use a robot/android aesthetic to be visually distinct from custom photorealistic avatars, clearly signaling these are placeholders. The agent name is appended for uniqueness.

## Files to Modify

### 1. `src/backend/db/schema.py` (line 66)
Add `is_default_avatar INTEGER DEFAULT 0` to `agent_ownership` CREATE TABLE definition, before the FOREIGN KEY line.

### 2. `src/backend/db/migrations.py`
- Add migration #26: `_migrate_agent_ownership_default_avatar` — `ALTER TABLE agent_ownership ADD COLUMN is_default_avatar INTEGER DEFAULT 0`
- Register in `run_all_migrations()` list (after `operator_queue_table`)
- Update docstring migration list

### 3. `src/backend/db/agents.py` (lines 806-844)
- Modify `set_avatar_identity()`: also set `is_default_avatar = 0` (clears default flag when real avatar is generated)
- Modify `clear_avatar_identity()`: also set `is_default_avatar = 0`
- Add `get_agents_without_custom_avatar()`: returns agent dicts (name, type) where `avatar_updated_at IS NULL OR is_default_avatar = 1`
- Add `set_default_avatar(agent_name, identity_prompt, updated_at)`: sets `avatar_updated_at`, `avatar_identity_prompt`, and `is_default_avatar = 1`

### 4. `src/backend/database.py` (line 425)
Add delegation methods: `get_agents_without_custom_avatar()`, `set_default_avatar()`

### 5. `src/backend/routers/avatar.py`
Add endpoint at top (before `/{agent_name}` routes to avoid path conflicts):

```
POST /api/agents/avatars/generate-defaults
```

Admin-only. For each agent without a custom avatar:
1. Build default identity prompt from agent name + type
2. Call `image_generation_service.generate_image(prompt, use_case="avatar", aspect_ratio="1:1", agent_name=name)`
3. Save PNG to `/data/avatars/{name}.png` (no `_ref.png`, no emotion variants)
4. Call `db.set_default_avatar(name, prompt, now)`
5. On failure, log and continue to next agent

Returns `{generated, failed, skipped, agents, errors, message}`.

**Route ordering note**: This must be defined BEFORE the `/{agent_name}/avatar` routes since `avatars` could match as an agent_name. FastAPI resolves routes in definition order, so defining it first ensures it matches the literal path.

### 6. `src/frontend/src/views/Settings.vue`
**Template**: Add "Default Avatars" card section after Skills Library, before Info Box (~line 1052). Contains:
- Section header with description explaining these are Gemini-generated placeholder avatars
- "Generate Default Avatars" button with spinner
- Result message showing count of generated/skipped/failed agents

**Script**: Add state refs (`generatingDefaultAvatars`, `defaultAvatarResult`) and `generateDefaultAvatars()` async function calling the endpoint.

## Data Flow

```
Settings.vue button click
  -> POST /api/agents/avatars/generate-defaults
    -> require admin
    -> db.get_agents_without_custom_avatar()
       (WHERE avatar_updated_at IS NULL OR is_default_avatar = 1)
    -> For each agent:
       1. Build prompt: "{type_description} named {agent_name}"
       2. image_generation_service.generate_image(prompt, use_case="avatar")
          -> Gemini Flash refines prompt (same AVATAR_BEST_PRACTICES)
          -> Gemini Image model generates portrait
       3. Save PNG to /data/avatars/{name}.png
       4. db.set_default_avatar(name, prompt, now)
    -> Return summary {generated, failed, skipped}
```

When user later generates a real custom avatar via existing flow:
```
POST /api/agents/{name}/avatar/generate
  -> db.set_avatar_identity() now also sets is_default_avatar = 0
  -> Default is overwritten, agent marked as having custom avatar
  -> Reference image + emotion variants created (custom-only features)
```

## Verification

1. Start services: `./scripts/deploy/start.sh` (after rebuilding backend: `docker-compose build backend`)
2. Login as admin, navigate to Settings
3. Confirm "Default Avatars" section appears with Generate button
4. Click Generate — should report N agents generated (takes ~10-15s per agent via Gemini)
5. Navigate to Agents list — all agents should now show unique Gemini-generated portrait avatars
6. Navigate to an agent detail — default avatar displays in header
7. Generate a custom avatar for one agent via the avatar modal
8. Return to Settings, click Generate again — that agent should be skipped
9. Delete an agent's avatar — clicking Generate again should re-create its default
