# Agent Files

Two-panel file manager in the Agent Detail Files tab for browsing, previewing, and editing agent workspace files.

## How It Works

1. Open the agent detail page and click the **Files** tab.
2. The left panel displays a file tree with search and expandable directories.
3. The right panel shows a preview of the selected file.
4. Supported previews: images, video, audio, PDF, and text files.
5. Click the edit button on any text file to modify and save it inline.
6. Delete files directly from the file manager. Protected path warnings appear for critical files.
7. Toggle **Show hidden files** to reveal dotfiles (`.env`, `.claude/`, etc.).
8. The agent workspace root is `/home/developer/`.

### Content Folder Convention

The `content/` directory is gitignored by default. Use it for large generated assets such as images, audio, and video.

### Shared Folders

Agents can expose their workspace folder for other agents to mount as a collaboration mechanism.

- Configure in the agent's **Sharing** tab using the Expose and Consume toggles.
- Permission-gated: only permitted agents can mount a shared folder.
- Relevant API endpoints: `GET/PUT /api/agents/{name}/folders`, `GET /api/agents/{name}/folders/available`, `GET /api/agents/{name}/folders/consumers`.

## For Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/{name}/files` | GET | List workspace files (tree structure) |
| `/api/agents/{name}/files/download` | GET | Download file content (100 MB limit) |

## See Also

- [Creating Agents](creating-agents.md)
- [Managing Agents](managing-agents.md)
