"""
Git synchronization service for GitHub-native agents (Phase 7).

Handles:
- Creating working branches for new agents
- Syncing agent changes to GitHub
- Managing git configuration in the database
- Initializing git in agent containers
"""
import asyncio
import httpx
import sqlite3
import uuid
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from database import db, AgentGitConfig, GitSyncResult
from services.docker_service import get_agent_container, execute_command_in_container

logger = logging.getLogger(__name__)


# S7 Layer 0: how many times reserve_and_generate_instance_id retries on
# a remote/DB collision before giving up. 5 is generous — with a 32-bit
# UUID prefix the probability of a single collision is ~0 and the probability
# of five in a row is astronomically small, so this catches only real bugs
# (e.g. the caller feeding us a non-unique repo).
MAX_INSTANCE_ID_RETRIES = 5


def generate_instance_id() -> str:
    """Generate a unique instance ID for an agent.

    NOTE (S7 Layer 0): this returns a raw UUID prefix with no remote/DB
    collision check. New call sites should use
    ``reserve_and_generate_instance_id`` instead; this is kept only for
    helpers that need the raw generator (e.g. inside the reserve helper).
    """
    return uuid.uuid4().hex[:8]


def generate_working_branch(agent_name: str, instance_id: str) -> str:
    """Generate a working branch name for an agent instance."""
    return f"trinity/{agent_name}/{instance_id}"


async def check_remote_branch_exists(github_repo: str, branch: str) -> bool:
    """Return True if ``refs/heads/<branch>`` exists on the remote.

    Uses ``git ls-remote`` so the check does not require the GitHub REST API
    or a specific auth mode — anything that can `git fetch` can also
    `git ls-remote`. Returns False on network/command errors: the caller
    treats that as "proceed with caution", since a stale "false" only costs
    us an extra DB-insert collision which Layer 2 catches.

    S7 Layer 0 — part of the pre-flight for ``reserve_and_generate_instance_id``.
    """
    # Prefer https://github.com/<repo>.git so the command works whether or
    # not the backend has a PAT configured. Public repos answer ls-remote
    # unauthenticated; private repos fall through to False and Layer 2
    # catches any duplicate insert.
    remote_url = f"https://github.com/{github_repo}.git"
    ref = f"refs/heads/{branch}"

    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "ls-remote",
            "--heads",
            "--exit-code",
            remote_url,
            ref,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning(
                "git ls-remote timed out for %s %s — treating as 'not present'",
                github_repo,
                branch,
            )
            return False
    except FileNotFoundError:
        logger.warning("git not installed on backend host; skipping remote branch check")
        return False
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "git ls-remote failed for %s %s: %s — treating as 'not present'",
            github_repo,
            branch,
            exc,
        )
        return False

    # --exit-code: 0 = ref found, 2 = not found. Anything else is an error
    # we log and treat as "not present" (Layer 2 catches real duplicates).
    if proc.returncode == 0:
        return bool(stdout.strip())
    if proc.returncode == 2:
        return False
    logger.warning(
        "git ls-remote %s %s exited %s — treating as 'not present'",
        github_repo,
        branch,
        proc.returncode,
    )
    return False


async def reserve_and_generate_instance_id(
    agent_name: str,
    github_repo: str,
    source_branch: str = "main",
    source_mode: bool = False,
    sync_paths: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """Atomically reserve a fresh working branch for an agent.

    S7 Layer 0 — single entry point for generating an instance ID. Combines:
      1. UUID generation
      2. ``git ls-remote`` probe against the remote (Layer 1)
      3. DB insert into ``agent_git_config`` under the partial UNIQUE index
         ``UNIQUE(github_repo, working_branch) WHERE source_mode = 0`` (Layer 2)

    Retries on either a remote hit or a DB IntegrityError up to
    ``MAX_INSTANCE_ID_RETRIES`` times, then raises ``RuntimeError``.

    For ``source_mode=True`` the branch is the source branch (e.g. ``main``),
    the remote probe is skipped (intentional shared-branch mode), and the DB
    insert bypasses the partial UNIQUE index by design.

    Returns:
        A ``(instance_id, working_branch)`` tuple. The DB row is already
        persisted when this function returns.

    Raises:
        RuntimeError: if ``MAX_INSTANCE_ID_RETRIES`` consecutive reservations
            collide on either the remote or the DB.
    """
    last_error: Optional[BaseException] = None

    for attempt in range(1, MAX_INSTANCE_ID_RETRIES + 1):
        if source_mode:
            # Source-mode agents share the source branch intentionally.
            instance_id = generate_instance_id()
            working_branch = source_branch
        else:
            instance_id = generate_instance_id()
            working_branch = generate_working_branch(agent_name, instance_id)

            if await check_remote_branch_exists(github_repo, working_branch):
                logger.warning(
                    "reserve_and_generate_instance_id: remote collision for %s "
                    "(attempt %d/%d)",
                    working_branch,
                    attempt,
                    MAX_INSTANCE_ID_RETRIES,
                )
                continue

        try:
            config = db.create_git_config(
                agent_name=agent_name,
                github_repo=github_repo,
                working_branch=working_branch,
                instance_id=instance_id,
                sync_paths=sync_paths,
                source_branch=source_branch,
                source_mode=source_mode,
            )
        except sqlite3.IntegrityError as exc:
            last_error = exc
            # The partial UNIQUE index on (github_repo, working_branch) WHERE
            # source_mode = 0 fired — another agent already owns this branch.
            # Retry with a fresh UUID.
            logger.warning(
                "reserve_and_generate_instance_id: DB collision for %s "
                "(attempt %d/%d): %s",
                working_branch,
                attempt,
                MAX_INSTANCE_ID_RETRIES,
                exc,
            )
            continue

        if config is None:
            # create_git_config returns None on a plain agent_name UNIQUE
            # violation — this is a different bug (agent already has config)
            # and should not be silently retried. Surface immediately.
            raise RuntimeError(
                f"reserve_and_generate_instance_id: agent_git_config already "
                f"exists for agent {agent_name!r}"
            )

        return instance_id, working_branch

    raise RuntimeError(
        f"reserve_and_generate_instance_id: could not reserve a fresh working "
        f"branch for {agent_name!r} in {github_repo!r} after "
        f"{MAX_INSTANCE_ID_RETRIES} retries (last error: {last_error!r})"
    )


async def create_git_config_for_agent(
    agent_name: str,
    github_repo: str,
    instance_id: Optional[str] = None
) -> AgentGitConfig:
    """
    Create git configuration for a new agent.

    Args:
        agent_name: Name of the agent
        github_repo: GitHub repository (e.g., "Abilityai/agent-ruby")
        instance_id: Optional instance ID (generated if not provided)

    Returns:
        AgentGitConfig with the configuration
    """
    if not instance_id:
        instance_id = generate_instance_id()

    working_branch = generate_working_branch(agent_name, instance_id)

    # Create the database record
    config = db.create_git_config(
        agent_name=agent_name,
        github_repo=github_repo,
        working_branch=working_branch,
        instance_id=instance_id
    )

    return config


async def get_git_status(agent_name: str) -> Optional[Dict[str, Any]]:
    """
    Get git status for an agent by calling the agent's internal API.

    Returns git status including branch, changes, and sync state.
    """
    container = get_agent_container(agent_name)
    if not container or container.status != "running":
        return None

    try:
        # Call the agent's internal git status endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://agent-{agent_name}:8000/api/git/status"
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Error getting git status for {agent_name}: {e}")
        return None


async def sync_to_github(
    agent_name: str,
    message: Optional[str] = None,
    paths: Optional[list] = None,
    strategy: Optional[str] = "normal"
) -> GitSyncResult:
    """
    Sync agent changes to GitHub.

    Calls the agent's internal sync endpoint to stage, commit, and push changes.

    Args:
        agent_name: Name of the agent
        message: Optional custom commit message
        paths: Optional specific paths to sync (default: all)
        strategy: Sync strategy - "normal", "pull_first", "force_push"

    Returns:
        GitSyncResult with sync outcome
    """
    container = get_agent_container(agent_name)
    if not container:
        return GitSyncResult(
            success=False,
            message="Agent not found"
        )

    if container.status != "running":
        return GitSyncResult(
            success=False,
            message="Agent must be running to sync"
        )

    try:
        # Call the agent's internal sync endpoint
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {"strategy": strategy}
            if message:
                payload["message"] = message
            if paths:
                payload["paths"] = paths

            response = await client.post(
                f"http://agent-{agent_name}:8000/api/git/sync",
                json=payload
            )

            if response.status_code == 200:
                data = response.json()

                # Update database with sync result
                if data.get("commit_sha"):
                    db.update_git_sync(agent_name, data["commit_sha"])

                return GitSyncResult(
                    success=data.get("success", False),
                    commit_sha=data.get("commit_sha"),
                    message=data.get("message", "Sync completed"),
                    files_changed=data.get("files_changed", 0),
                    branch=data.get("branch"),
                    sync_time=datetime.fromisoformat(data["sync_time"]) if data.get("sync_time") else datetime.utcnow()
                )
            elif response.status_code == 409:
                # Conflict - return with conflict info
                data = response.json()
                conflict_type = response.headers.get("X-Conflict-Type", "unknown")
                return GitSyncResult(
                    success=False,
                    message=data.get("detail", "Sync conflict"),
                    conflict_type=conflict_type
                )
            else:
                error_detail = response.json().get("detail", "Sync failed")
                return GitSyncResult(
                    success=False,
                    message=f"Sync failed: {error_detail}"
                )
    except Exception as e:
        return GitSyncResult(
            success=False,
            message=f"Sync error: {str(e)}"
        )


async def get_git_log(agent_name: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """
    Get recent git commits for an agent.

    Returns list of commits with SHA, message, author, and date.
    """
    container = get_agent_container(agent_name)
    if not container or container.status != "running":
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://agent-{agent_name}:8000/api/git/log",
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Error getting git log for {agent_name}: {e}")
        return None


async def pull_from_github(agent_name: str, strategy: Optional[str] = "clean") -> Dict[str, Any]:
    """
    Pull latest changes from GitHub to the agent.

    Args:
        agent_name: Name of the agent
        strategy: Pull strategy - "clean", "stash_reapply", "force_reset"

    Returns:
        Dict with pull result and conflict info if applicable
    """
    container = get_agent_container(agent_name)
    if not container:
        return {"success": False, "message": "Agent not found"}

    if container.status != "running":
        return {"success": False, "message": "Agent must be running to pull"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"http://agent-{agent_name}:8000/api/git/pull",
                json={"strategy": strategy}
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 409:
                # Conflict detected
                data = response.json()
                conflict_type = response.headers.get("X-Conflict-Type", "unknown")
                return {
                    "success": False,
                    "message": data.get("detail", "Pull conflict"),
                    "conflict_type": conflict_type
                }
            else:
                error_detail = response.json().get("detail", "Pull failed")
                return {"success": False, "message": f"Pull failed: {error_detail}"}
    except Exception as e:
        return {"success": False, "message": f"Pull error: {str(e)}"}


def get_agent_git_config(agent_name: str) -> Optional[AgentGitConfig]:
    """Get git configuration for an agent from the database."""
    return db.get_git_config(agent_name)


def delete_agent_git_config(agent_name: str) -> bool:
    """Delete git configuration when an agent is deleted."""
    return db.delete_git_config(agent_name)


# ============================================================================
# Git Initialization in Container
# ============================================================================

@dataclass
class GitInitResult:
    """Result of git initialization in container."""
    success: bool
    git_dir: str
    working_branch: Optional[str] = None
    error: Optional[str] = None


async def initialize_git_in_container(
    agent_name: str,
    github_repo: str,
    github_pat: str,
    create_working_branch: bool = True,
    working_branch: Optional[str] = None,
) -> GitInitResult:
    """
    Initialize git in an agent container.

    Performs:
    1. Detect git directory (workspace or home)
    2. Create .gitignore
    3. Initialize git repo
    4. Configure remote
    5. Create initial commit
    6. Push to GitHub
    7. Create working branch (optional; prefer the pre-reserved path)

    Args:
        agent_name: Name of the agent container
        github_repo: Full repo name (e.g., "owner/repo")
        github_pat: GitHub PAT for authentication
        create_working_branch: DEPRECATED (S7 Layer 0 / #382). When True the
            helper generates an instance ID internally, bypassing the
            `reserve_and_generate_instance_id` collision check. New callers
            MUST pre-reserve via `reserve_and_generate_instance_id` and pass
            `create_working_branch=False, working_branch=<reserved>` instead.
        working_branch: Pre-reserved working branch name (e.g.
            ``trinity/<agent>/<id>``). Required when
            ``create_working_branch=False``. Mutually exclusive with
            internal generation — when set, this function just checks out /
            pushes that branch.

    Returns:
        GitInitResult with status and branch info
    """
    container_name = f"agent-{agent_name}"

    # Step 1: Determine git directory
    # NOTE: All agents use /home/developer as their home directory.
    # The /home/developer/workspace check is LEGACY support for agents created before 2026-02.
    # New agents should never have a workspace subdirectory.
    check_workspace = await execute_command_in_container(
        container_name=container_name,
        command='bash -c "[ -d /home/developer/workspace ] && find /home/developer/workspace -mindepth 1 -maxdepth 1 | head -1 | wc -l"',
        timeout=5
    )

    workspace_has_content = (
        check_workspace.get("exit_code") == 0 and
        "1" in check_workspace.get("output", "")
    )

    if workspace_has_content:
        # Legacy agent with workspace subdirectory
        git_dir = "/home/developer/workspace"
        logger.info(f"[LEGACY] Using workspace directory with existing content: {git_dir}")
    else:
        # Standard path for all current agents
        git_dir = "/home/developer"
        logger.info(f"Using home directory: {git_dir}")

    # Step 2: Create .gitignore (if using home directory)
    if git_dir == "/home/developer":
        gitignore_content = """# Exclude sensitive and temporary files
.bash_logout
.bashrc
.profile
.bash_history
.cache/
.local/
.npm/
.ssh/
"""
        await execute_command_in_container(
            container_name=container_name,
            command=f'bash -c "cat > {git_dir}/.gitignore << \'GITIGNORE_EOF\'\n{gitignore_content}\nGITIGNORE_EOF\n"',
            timeout=5
        )

    # Step 3: Initialize git and try to preserve remote history
    # Commands marked required=True will abort on failure;
    # optional commands (like fetch) may fail for empty repos.
    setup_commands: list[tuple[str, bool]] = [
        ('git config --global user.email "trinity@agent.local"', True),
        ('git config --global user.name "Trinity Agent"', True),
        ('git config --global init.defaultBranch main', True),
        ('git init', True),
        (f'git remote get-url origin >/dev/null 2>&1 && '
         f'git remote set-url origin https://oauth2:{github_pat}@github.com/{github_repo}.git || '
         f'git remote add origin https://oauth2:{github_pat}@github.com/{github_repo}.git', True),
        ('git fetch origin', False),  # Optional — remote may be empty
    ]

    for cmd, required in setup_commands:
        result = await execute_command_in_container(
            container_name=container_name,
            command=f'bash -c "cd {git_dir} && {cmd}"',
            timeout=60
        )
        if result.get("exit_code", 0) != 0 and required:
            output = result.get("output", "")
            return GitInitResult(
                success=False,
                git_dir=git_dir,
                error=f"Git command failed: {cmd}\nOutput: {output}"
            )

    # Check if remote has commits on main (to preserve history)
    check_main = await execute_command_in_container(
        container_name=container_name,
        command=f'bash -c "cd {git_dir} && git rev-parse --verify origin/main"',
        timeout=10
    )
    remote_has_main = check_main.get("exit_code", 1) == 0

    if remote_has_main:
        # Preserve remote history: reset index to origin/main, then stage
        # the current workspace on top of it and fast-forward push.
        commit_commands = [
            'git reset origin/main',
            'git add .',
            'git commit -m "Initial commit from Trinity Agent" || echo "Nothing to commit"',
            # Always set upstream; no-op when there is nothing new to push.
            'git push -u origin main',
        ]
    else:
        # Empty repo: force push creates the initial history.
        commit_commands = [
            'git add .',
            'git commit -m "Initial commit from Trinity Agent" || echo "Nothing to commit"',
            'git push -u origin main --force',
        ]

    for cmd in commit_commands:
        result = await execute_command_in_container(
            container_name=container_name,
            command=f'bash -c "cd {git_dir} && {cmd}"',
            timeout=60
        )
        if result.get("exit_code", 0) != 0:
            output = result.get("output", "")
            if "Nothing to commit" not in output:
                return GitInitResult(
                    success=False,
                    git_dir=git_dir,
                    error=f"Git command failed: {cmd}\nOutput: {output}"
                )

    # Step 4: Create (or check out) the working branch.
    # S7 Layer 0 (#382): prefer the pre-reserved path — callers pass
    # `working_branch=<reserved>` and `create_working_branch=False`. The
    # legacy `create_working_branch=True` path falls back to an internal
    # `generate_instance_id()` call and is deprecated; it's kept so older
    # callers don't break, but emits a warning on every use.
    if working_branch is not None:
        branch_commands = [
            f"git checkout -b {working_branch}",
            f"git push -u origin {working_branch}",
        ]
        for cmd in branch_commands:
            result = await execute_command_in_container(
                container_name=container_name,
                command=f'bash -c "cd {git_dir} && {cmd}"',
                timeout=60,
            )
            if result.get("exit_code", 0) != 0:
                logger.warning(
                    "Failed to create pre-reserved working branch %s: %s",
                    working_branch,
                    result.get("output", ""),
                )
    elif create_working_branch:
        # Deprecated path — no caller should hit this after S7 rolls out.
        logger.warning(
            "initialize_git_in_container(create_working_branch=True) is "
            "deprecated (S7 / #382). Pre-reserve via "
            "reserve_and_generate_instance_id and pass working_branch "
            "explicitly."
        )
        instance_id = generate_instance_id()
        working_branch = generate_working_branch(agent_name, instance_id)

        branch_commands = [
            f'git checkout -b {working_branch}',
            f'git push -u origin {working_branch}'
        ]

        for cmd in branch_commands:
            result = await execute_command_in_container(
                container_name=container_name,
                command=f'bash -c "cd {git_dir} && {cmd}"',
                timeout=60
            )
            if result.get("exit_code", 0) != 0:
                # Working branch creation is optional - log but don't fail
                logger.warning(f"Failed to create working branch: {result.get('output', '')}")

    # Step 5: Verify
    verify_result = await execute_command_in_container(
        container_name=container_name,
        command=f'bash -c "cd {git_dir} && git rev-parse --git-dir"',
        timeout=5
    )

    if verify_result.get("exit_code", 0) != 0:
        return GitInitResult(
            success=False,
            git_dir=git_dir,
            error="Git initialization verification failed"
        )

    logger.info(f"Git initialization verified successfully in {git_dir}")

    return GitInitResult(
        success=True,
        git_dir=git_dir,
        working_branch=working_branch
    )


async def check_git_initialized(agent_name: str) -> Optional[str]:
    """
    Check if git is initialized in an agent container.

    Args:
        agent_name: Name of the agent

    Returns:
        The git directory path if initialized, None otherwise
    """
    container_name = f"agent-{agent_name}"

    # NOTE: The workspace check is LEGACY support for agents created before 2026-02.
    # New agents use /home/developer directly.
    result = await execute_command_in_container(
        container_name=container_name,
        command='bash -c "[ -d /home/developer/workspace/.git ] && echo workspace || ([ -d /home/developer/.git ] && echo home || echo notexists)"',
        timeout=5
    )

    output = result.get("output", "").strip()

    if "workspace" in output:
        # Legacy agent with workspace subdirectory
        return "/home/developer/workspace"
    elif "home" in output:
        # Standard path for all current agents
        return "/home/developer"

    return None
