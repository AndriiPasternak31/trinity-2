"""
Trinity injection API endpoints.
"""
import os
import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..models import TrinityInjectRequest, TrinityInjectResponse, TrinityStatusResponse
from ..config import TRINITY_META_PROMPT_DIR, WORKSPACE_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


def check_trinity_injection_status() -> dict:
    """Check if Trinity has been injected"""
    workspace = WORKSPACE_DIR

    files = {
        ".trinity/prompt.md": (workspace / ".trinity" / "prompt.md").exists(),
        "CLAUDE.local.md": (workspace / "CLAUDE.local.md").exists(),
    }

    directories = {
        ".trinity": (workspace / ".trinity").exists(),
    }

    return {
        "meta_prompt_mounted": TRINITY_META_PROMPT_DIR.exists(),
        "files": files,
        "directories": directories,
        "claude_md_has_trinity_section": files["CLAUDE.local.md"],
        "injected": all(files.values()) and all(directories.values())
    }


@router.get("/api/trinity/status", response_model=TrinityStatusResponse)
async def get_trinity_status():
    """Check Trinity injection status"""
    status = check_trinity_injection_status()
    return TrinityStatusResponse(**status)


@router.post("/api/trinity/inject", response_model=TrinityInjectResponse)
async def inject_trinity(request: TrinityInjectRequest = TrinityInjectRequest()):
    """
    Inject Trinity meta-prompt and planning infrastructure.

    This endpoint:
    1. Copies prompt.md to .trinity/prompt.md
    2. Writes CLAUDE.local.md with Trinity platform instructions (survives git operations)
    3. Cleans up legacy Trinity section from CLAUDE.md if present
    """
    workspace = WORKSPACE_DIR

    # Check if meta-prompt is mounted
    if not TRINITY_META_PROMPT_DIR.exists():
        return TrinityInjectResponse(
            status="error",
            error="Trinity meta-prompt not mounted at /trinity-meta-prompt"
        )

    # Check if already injected
    current_status = check_trinity_injection_status()
    if current_status["injected"] and not request.force:
        # Check if source prompt.md has changed (e.g. new sections added)
        prompt_src = TRINITY_META_PROMPT_DIR / "prompt.md"
        prompt_dst = workspace / ".trinity" / "prompt.md"
        prompt_stale = False
        if prompt_src.exists() and prompt_dst.exists():
            try:
                prompt_stale = prompt_src.read_text() != prompt_dst.read_text()
            except Exception:
                pass
        if not prompt_stale:
            return TrinityInjectResponse(
                status="already_injected",
                already_injected=True
            )
        logger.info("Meta-prompt has changed, re-injecting")

    files_created = []
    directories_created = []

    try:
        # 1. Create .trinity directory and copy prompt.md
        trinity_dir = workspace / ".trinity"
        trinity_dir.mkdir(parents=True, exist_ok=True)
        directories_created.append(".trinity")

        prompt_src = TRINITY_META_PROMPT_DIR / "prompt.md"
        prompt_dst = trinity_dir / "prompt.md"
        if prompt_src.exists():
            shutil.copy2(prompt_src, prompt_dst)
            files_created.append(".trinity/prompt.md")
            logger.info(f"Copied {prompt_src} to {prompt_dst}")

        # 2. Write CLAUDE.local.md — gitignored, survives git operations
        #    This is the platform's channel for instructions to the agent.
        #    Agents own CLAUDE.md; the platform owns CLAUDE.local.md.
        claude_local_path = workspace / "CLAUDE.local.md"
        claude_md_updated = False

        local_content = """# Trinity Platform Instructions

> This file is managed by the Trinity platform. Do not edit manually — it is overwritten on each agent start.

## Trinity Agent System

This agent is part of the Trinity Deep Agent Orchestration Platform.

### Agent Collaboration

You can collaborate with other agents using the Trinity MCP tools:

- `mcp__trinity__list_agents()` - See agents you can communicate with
- `mcp__trinity__chat_with_agent(agent_name, message)` - Delegate tasks to other agents

**Note**: You can only communicate with agents you have been granted permission to access.
Use `list_agents` to discover your available collaborators.

### Operator Communication

See @.trinity/prompt.md for the full operator communication protocol.

### Package Persistence

When installing system packages (apt-get, npm -g, etc.), add them to your setup script so they persist across container updates:

```bash
# Install package
sudo apt-get install -y ffmpeg

# Add to persistent setup script
mkdir -p ~/.trinity
echo "sudo apt-get install -y ffmpeg" >> ~/.trinity/setup.sh
```

This script runs automatically on container start. Always update it when installing system-level packages.
"""

        # Append custom instructions if provided
        if request.custom_prompt and request.custom_prompt.strip():
            local_content += f"""
## Custom Instructions

{request.custom_prompt.strip()}
"""
            logger.info("Custom prompt included in CLAUDE.local.md")

        with open(claude_local_path, "w") as f:
            f.write(local_content)
        claude_md_updated = True
        files_created.append("CLAUDE.local.md")
        logger.info("Wrote CLAUDE.local.md with Trinity platform instructions")

        # 3. Ensure CLAUDE.local.md is gitignored
        gitignore_path = workspace / ".gitignore"
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            if "CLAUDE.local.md" not in gitignore_content:
                with open(gitignore_path, "a") as f:
                    f.write("\n# Trinity platform instructions (managed by platform, not git)\nCLAUDE.local.md\n")
                logger.info("Added CLAUDE.local.md to .gitignore")
        else:
            with open(gitignore_path, "w") as f:
                f.write("# Trinity platform instructions (managed by platform, not git)\nCLAUDE.local.md\n")
            logger.info("Created .gitignore with CLAUDE.local.md entry")

        # 4. Clean up legacy Trinity section from CLAUDE.md if present
        claude_md_path = workspace / "CLAUDE.md"
        if claude_md_path.exists():
            content = claude_md_path.read_text()
            if "## Trinity Agent System" in content:
                parts = content.split("## Trinity Agent System")
                cleaned = parts[0].rstrip()
                # Also remove Custom Instructions that followed Trinity section
                if len(parts) > 1 and "## Custom Instructions" in parts[1]:
                    # Custom instructions were part of the old injection, now in CLAUDE.local.md
                    pass
                with open(claude_md_path, "w") as f:
                    f.write(cleaned + "\n")
                logger.info("Cleaned up legacy Trinity section from CLAUDE.md")

        return TrinityInjectResponse(
            status="injected",
            already_injected=False,
            files_created=files_created,
            directories_created=directories_created,
            claude_md_updated=claude_md_updated
        )

    except Exception as e:
        logger.error(f"Trinity injection failed: {e}")
        return TrinityInjectResponse(
            status="error",
            error=str(e)
        )


@router.post("/api/trinity/reset")
async def reset_trinity():
    """
    Reset Trinity injection - remove all injected files and directories.
    """
    workspace = WORKSPACE_DIR
    files_removed = []
    directories_removed = []

    try:
        # Remove .trinity directory
        trinity_dir = workspace / ".trinity"
        if trinity_dir.exists():
            shutil.rmtree(trinity_dir)
            directories_removed.append(".trinity")

        # Remove .claude/commands/trinity directory
        commands_dir = workspace / ".claude/commands/trinity"
        if commands_dir.exists():
            shutil.rmtree(commands_dir)
            directories_removed.append(".claude/commands/trinity")

        # Note: We don't remove plans/ as that contains user data

        # Remove CLAUDE.local.md (platform-managed file)
        claude_local_path = workspace / "CLAUDE.local.md"
        if claude_local_path.exists():
            claude_local_path.unlink()
            files_removed.append("CLAUDE.local.md")

        # Also clean up legacy Trinity section from CLAUDE.md if present
        claude_md_path = workspace / "CLAUDE.md"
        if claude_md_path.exists():
            content = claude_md_path.read_text()
            if "## Trinity Agent System" in content:
                parts = content.split("## Trinity Agent System")
                if len(parts) > 1:
                    new_content = parts[0].rstrip()
                    with open(claude_md_path, "w") as f:
                        f.write(new_content + "\n")
                    files_removed.append("CLAUDE.md (legacy Trinity section)")

        return {
            "status": "reset",
            "files_removed": files_removed,
            "directories_removed": directories_removed
        }

    except Exception as e:
        logger.error(f"Trinity reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
