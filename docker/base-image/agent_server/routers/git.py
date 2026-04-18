"""
Git sync endpoints for GitHub bidirectional sync.
"""
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException

from ..models import GitSyncRequest, GitPullRequest
from .files import _read_persistent_state
from .snapshot import build_snapshot, restore_from_tar

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_pull_branch(current_branch: str, home_dir: Path) -> str:
    """Determine the upstream branch to pull from.

    For trinity/* working branches, pull from main instead of the working
    branch (which nobody pushes to externally). Falls back to current_branch
    if origin/main doesn't exist.
    """
    if not current_branch.startswith("trinity/"):
        return current_branch
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/main"],
        capture_output=True, text=True, cwd=str(home_dir), timeout=10
    )
    return "main" if result.returncode == 0 else current_branch


@router.get("/api/git/status")
async def get_git_status():
    """
    Get git repository status including current branch, changes, and sync state.
    Only available for agents with git sync enabled.
    """
    home_dir = Path("/home/developer")
    git_dir = home_dir / ".git"

    if not git_dir.exists():
        return {
            "git_enabled": False,
            "message": "Git sync not enabled for this agent"
        }

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        # Get status (modified, untracked files)
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        changes = []
        if status_result.returncode == 0 and status_result.stdout.strip():
            for line in status_result.stdout.strip().split('\n'):
                if line:
                    status_code = line[:2]
                    filepath = line[3:]
                    changes.append({
                        "status": status_code.strip(),
                        "path": filepath
                    })

        # Get last commit
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%h|%s|%an|%ai"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        last_commit = None
        if log_result.returncode == 0 and log_result.stdout.strip():
            parts = log_result.stdout.strip().split('|')
            if len(parts) >= 5:
                last_commit = {
                    "sha": parts[0],
                    "short_sha": parts[1],
                    "message": parts[2],
                    "author": parts[3],
                    "date": parts[4]
                }

        # Fetch to update remote refs (required for accurate ahead/behind)
        fetch_result = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=30
        )

        # For trinity/* working branches, compare against origin/main
        pull_branch = _get_pull_branch(current_branch, home_dir)

        ahead_behind_result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"origin/{pull_branch}...HEAD"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        ahead = 0
        behind = 0
        if ahead_behind_result.returncode == 0:
            parts = ahead_behind_result.stdout.strip().split()
            if len(parts) == 2:
                behind = int(parts[0])
                ahead = int(parts[1])

        # Get remote URL (without credentials)
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        remote_url = ""
        if remote_result.returncode == 0:
            url = remote_result.stdout.strip()
            # Remove credentials from URL for display
            if '@github.com' in url:
                remote_url = "https://github.com/" + url.split('@github.com/')[1]
            else:
                remote_url = url

        return {
            "git_enabled": True,
            "branch": current_branch,
            "remote_url": remote_url,
            "last_commit": last_commit,
            "changes": changes,
            "changes_count": len(changes),
            "ahead": ahead,
            "behind": behind,
            "sync_status": "up_to_date" if ahead == 0 and len(changes) == 0 else "pending_sync"
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    except Exception as e:
        logger.error(f"Git status error: {e}")
        raise HTTPException(status_code=500, detail=f"Git status error: {str(e)}")


@router.post("/api/git/sync")
async def sync_to_github(request: GitSyncRequest):
    """
    Sync local changes to GitHub by staging, committing, and pushing.

    Strategies:
    - normal: Stage, commit, push (fails if remote has changes)
    - pull_first: Pull latest, then stage, commit, push
    - force_push: Stage, commit, force push (overwrites remote)

    Steps:
    1. Stage all changes (or specific paths if provided)
    2. Create a commit with the provided message (or auto-generated)
    3. Push to the working branch (based on strategy)

    Returns the commit SHA on success.
    """
    home_dir = Path("/home/developer")
    git_dir = home_dir / ".git"
    strategy = request.strategy or "normal"

    if not git_dir.exists():
        raise HTTPException(status_code=400, detail="Git sync not enabled for this agent")

    try:
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"

        # For pull_first strategy, pull before staging
        if strategy == "pull_first":
            # Fetch first
            fetch_result = subprocess.run(
                ["git", "fetch", "origin"],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=60
            )

            # For trinity/* working branches, pull from main
            pull_branch = _get_pull_branch(current_branch, home_dir)

            # Check if we're behind
            behind_result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..origin/{pull_branch}"],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=10
            )
            commits_behind = int(behind_result.stdout.strip()) if behind_result.returncode == 0 else 0

            if commits_behind > 0:
                # Stash local changes before pull
                status_check = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=str(home_dir),
                    timeout=10
                )
                has_changes = bool(status_check.stdout.strip())

                if has_changes:
                    stash_result = subprocess.run(
                        ["git", "stash", "push", "-m", "Trinity auto-stash before sync"],
                        capture_output=True,
                        text=True,
                        cwd=str(home_dir),
                        timeout=30
                    )
                    stash_created = stash_result.returncode == 0 and "No local changes" not in stash_result.stdout
                else:
                    stash_created = False

                # Pull with rebase (from upstream branch, not working branch)
                pull_result = subprocess.run(
                    ["git", "pull", "--rebase", "origin", pull_branch],
                    capture_output=True,
                    text=True,
                    cwd=str(home_dir),
                    timeout=60
                )

                if pull_result.returncode != 0:
                    subprocess.run(["git", "rebase", "--abort"], cwd=str(home_dir), timeout=10, capture_output=True)
                    if stash_created:
                        subprocess.run(["git", "stash", "pop"], cwd=str(home_dir), timeout=30, capture_output=True)
                    raise HTTPException(
                        status_code=409,
                        detail=f"Pull failed during sync: {pull_result.stderr}",
                        headers={"X-Conflict-Type": "merge_conflict"}
                    )

                # Reapply stash
                if stash_created:
                    pop_result = subprocess.run(
                        ["git", "stash", "pop"],
                        capture_output=True,
                        text=True,
                        cwd=str(home_dir),
                        timeout=30
                    )
                    if pop_result.returncode != 0:
                        logger.warning(f"Failed to reapply stash: {pop_result.stderr}")

        # 1. Stage changes
        if request.paths:
            # Stage specific paths (single git add call for all paths)
            add_result = subprocess.run(
                ["git", "add"] + list(request.paths),
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=30
            )
            if add_result.returncode != 0:
                logger.warning(f"Failed to add paths: {add_result.stderr}")
        else:
            # Stage all changes
            add_result = subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=30
            )
            if add_result.returncode != 0:
                raise HTTPException(status_code=500, detail=f"Git add failed: {add_result.stderr}")

        # Check if there's anything to commit
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )

        staged_changes = [line for line in status_result.stdout.split('\n') if line and line[0] != ' ' and line[0] != '?']
        if not staged_changes:
            return {
                "success": True,
                "message": "No changes to sync",
                "commit_sha": None,
                "files_changed": 0,
                "strategy": strategy
            }

        # 2. Create commit
        commit_message = request.message or f"Trinity sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=30
        )
        if commit_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Git commit failed: {commit_result.stderr}")

        # Get the commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        commit_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None

        # 3. Push to remote based on strategy
        if strategy == "force_push":
            # Force push (overwrites remote)
            push_result = subprocess.run(
                ["git", "push", "--force"],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=60
            )
            if push_result.returncode != 0:
                raise HTTPException(status_code=500, detail=f"Force push failed: {push_result.stderr}")
        else:
            # Normal push or pull_first (after pull, should be safe to push)
            push_result = subprocess.run(
                ["git", "push", "-u", "origin", current_branch],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=60
            )

            if push_result.returncode != 0:
                stderr = push_result.stderr or ""
                stderr_lower = stderr.lower()
                if "has no upstream branch" in stderr_lower:
                    upstream_result = subprocess.run(
                        ["git", "push", "--set-upstream", "origin", current_branch],
                        capture_output=True,
                        text=True,
                        cwd=str(home_dir),
                        timeout=60
                    )
                    if upstream_result.returncode != 0:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Git push failed: {upstream_result.stderr}"
                        )
                    return {
                        "success": True,
                        "message": f"Synced to {current_branch}",
                        "commit_sha": commit_sha,
                        "files_changed": len(staged_changes),
                        "branch": current_branch,
                        "strategy": strategy,
                        "sync_time": datetime.now().isoformat()
                    }
                # Check if it's a rejection due to remote changes
                if "rejected" in stderr_lower or "fetch first" in stderr_lower or "non-fast-forward" in stderr_lower:
                    raise HTTPException(
                        status_code=409,
                        detail="Push rejected: Remote has changes. Use 'Pull First' or 'Force Push' strategy.",
                        headers={"X-Conflict-Type": "push_rejected"}
                    )
                else:
                    raise HTTPException(status_code=500, detail=f"Git push failed: {stderr}")

        return {
            "success": True,
            "message": f"Synced to {current_branch}",
            "commit_sha": commit_sha,
            "files_changed": len(staged_changes),
            "branch": current_branch,
            "strategy": strategy,
            "sync_time": datetime.now().isoformat()
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Git sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Git sync error: {str(e)}")


@router.get("/api/git/log")
async def get_git_log(limit: int = 10):
    """
    Get recent git commits for this agent's branch.
    """
    home_dir = Path("/home/developer")
    git_dir = home_dir / ".git"

    if not git_dir.exists():
        raise HTTPException(status_code=400, detail="Git sync not enabled for this agent")

    try:
        log_result = subprocess.run(
            ["git", "log", f"-{limit}", "--format=%H|%h|%s|%an|%ai"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=30
        )

        if log_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Git log failed: {log_result.stderr}")

        commits = []
        for line in log_result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        "sha": parts[0],
                        "short_sha": parts[1],
                        "message": parts[2],
                        "author": parts[3],
                        "date": parts[4]
                    })

        return {
            "commits": commits,
            "count": len(commits)
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Git log error: {e}")
        raise HTTPException(status_code=500, detail=f"Git log error: {str(e)}")


@router.post("/api/git/pull")
async def pull_from_github(request: GitPullRequest = GitPullRequest()):
    """
    Pull latest changes from the remote branch with conflict resolution strategies.

    Strategies:
    - clean: Try simple pull --rebase (fails if local changes conflict)
    - stash_reapply: Stash local changes, pull, then reapply stash
    - force_reset: Discard local changes and reset to remote (destructive!)
    """
    home_dir = Path("/home/developer")
    git_dir = home_dir / ".git"
    strategy = request.strategy or "clean"

    if not git_dir.exists():
        raise HTTPException(status_code=400, detail="Git sync not enabled for this agent")

    try:
        # Always fetch first to update remote refs
        fetch_result = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=60
        )
        if fetch_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Git fetch failed: {fetch_result.stderr}")

        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"

        # For trinity/* working branches, pull from main instead
        pull_branch = _get_pull_branch(current_branch, home_dir)

        # Check for local uncommitted changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(home_dir),
            timeout=10
        )
        has_local_changes = bool(status_result.stdout.strip())

        # Execute strategy
        if strategy == "force_reset":
            # Discard all local changes and reset to remote
            reset_result = subprocess.run(
                ["git", "reset", "--hard", f"origin/{pull_branch}"],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=60
            )
            if reset_result.returncode != 0:
                raise HTTPException(status_code=500, detail=f"Git reset failed: {reset_result.stderr}")

            # Clean untracked files too
            subprocess.run(
                ["git", "clean", "-fd"],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=30
            )

            return {
                "success": True,
                "message": f"Force reset to origin/{pull_branch}",
                "strategy": "force_reset",
                "local_changes_discarded": has_local_changes
            }

        elif strategy == "stash_reapply":
            stash_created = False
            stash_message = ""

            # Stash local changes if any
            if has_local_changes:
                stash_result = subprocess.run(
                    ["git", "stash", "push", "-m", "Trinity auto-stash before pull"],
                    capture_output=True,
                    text=True,
                    cwd=str(home_dir),
                    timeout=30
                )
                if stash_result.returncode != 0:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Failed to stash local changes: {stash_result.stderr}",
                        headers={"X-Conflict-Type": "stash_failed"}
                    )
                stash_created = "No local changes" not in stash_result.stdout

            # Pull with rebase (from upstream branch, not working branch)
            pull_result = subprocess.run(
                ["git", "pull", "--rebase", "origin", pull_branch],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=60
            )

            if pull_result.returncode != 0:
                # Abort rebase if it failed
                subprocess.run(["git", "rebase", "--abort"], cwd=str(home_dir), timeout=10, capture_output=True)

                # Try to restore stash if we created one
                if stash_created:
                    subprocess.run(["git", "stash", "pop"], cwd=str(home_dir), timeout=30, capture_output=True)

                raise HTTPException(
                    status_code=409,
                    detail=f"Pull failed with conflicts: {pull_result.stderr}",
                    headers={"X-Conflict-Type": "merge_conflict"}
                )

            # Reapply stash if we created one
            if stash_created:
                pop_result = subprocess.run(
                    ["git", "stash", "pop"],
                    capture_output=True,
                    text=True,
                    cwd=str(home_dir),
                    timeout=30
                )
                if pop_result.returncode != 0:
                    # Stash pop failed - likely conflicts with newly pulled changes
                    stash_message = f" (Warning: Could not reapply local changes: {pop_result.stderr.strip()})"

            return {
                "success": True,
                "message": f"Pulled latest changes from origin/{pull_branch}{stash_message}",
                "strategy": "stash_reapply",
                "stash_created": stash_created,
                "output": pull_result.stdout
            }

        else:  # "clean" strategy (default)
            # Check if we're behind remote (using upstream branch)
            behind_result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..origin/{pull_branch}"],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=10
            )
            commits_behind = int(behind_result.stdout.strip()) if behind_result.returncode == 0 else 0

            if commits_behind == 0:
                return {
                    "success": True,
                    "message": "Already up to date",
                    "strategy": "clean",
                    "commits_behind": 0
                }

            # Try simple pull with rebase (from upstream branch)
            pull_result = subprocess.run(
                ["git", "pull", "--rebase", "origin", pull_branch],
                capture_output=True,
                text=True,
                cwd=str(home_dir),
                timeout=60
            )

            if pull_result.returncode != 0:
                # Abort rebase
                subprocess.run(["git", "rebase", "--abort"], cwd=str(home_dir), timeout=10, capture_output=True)

                # Determine conflict type
                conflict_type = "local_uncommitted" if has_local_changes else "merge_conflict"
                error_detail = pull_result.stderr.strip()

                raise HTTPException(
                    status_code=409,
                    detail=f"Pull failed: {error_detail}",
                    headers={"X-Conflict-Type": conflict_type}
                )

            return {
                "success": True,
                "message": f"Pulled {commits_behind} commit(s) from origin/{pull_branch}",
                "strategy": "clean",
                "commits_behind": commits_behind,
                "output": pull_result.stdout
            }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Git pull error: {e}")
        raise HTTPException(status_code=500, detail=f"Git pull error: {str(e)}")


# ---------------------------------------------------------------------------
# Reset-preserve-state (S3, #384)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def reset_to_main_preserve_state_impl(
    home_dir: Path,
    read_allowlist: Callable[[], list[str]] = _read_persistent_state,
    skip_push: bool = False,
) -> dict:
    """Adopt origin/main as the new baseline, preserving allowlisted files.

    The safe-recovery primitive for the parallel-history deadlock (P2/P3
    in the git-improvements proposal). Composes three steps:

    1. Read the persistent-state allowlist (#383 / S4).
    2. Snapshot matching files to `.trinity/backup/<iso-ts>/` so the
       destructive reset is always recoverable from inside the container.
    3. `git reset --hard origin/main`, overlay the snapshot, commit with
       the spec's exact message, and `git push --force-with-lease`.

    `skip_push=True` is used by tests so the full sequence can be
    verified without needing a writable remote.
    """
    if not (home_dir / ".git").exists():
        return {"error": "no_git_config"}
    if _git(["remote", "get-url", "origin"], home_dir).returncode != 0:
        return {"error": "no_git_config"}

    _git(["fetch", "origin", "main"], home_dir, timeout=120)
    if _git(["rev-parse", "--verify", "origin/main"], home_dir).returncode != 0:
        return {"error": "no_remote_main"}

    current = _git(["rev-parse", "--abbrev-ref", "HEAD"], home_dir)
    if current.returncode != 0:
        return {"error": "no_git_config"}
    working_branch = current.stdout.strip()

    patterns = read_allowlist()
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    backup_rel = Path(".trinity/backup") / iso
    backup_dir = home_dir / backup_rel
    backup_dir.mkdir(parents=True, exist_ok=True)

    tar_bytes, files_preserved = build_snapshot(home_dir, patterns)
    (backup_dir / "snapshot.tar").write_bytes(tar_bytes)
    (backup_dir / "files.txt").write_text("\n".join(files_preserved) + "\n")

    reset_res = _git(["reset", "--hard", "origin/main"], home_dir)
    if reset_res.returncode != 0:
        return {"error": "reset_failed", "stderr": reset_res.stderr}

    restored, _skipped = restore_from_tar(home_dir, tar_bytes, patterns)

    _git(["add", "-A"], home_dir)
    commit_res = _git(
        ["commit", "-m", "Adopt main baseline, preserve state", "--allow-empty"],
        home_dir,
    )
    if commit_res.returncode != 0:
        return {"error": "commit_failed", "stderr": commit_res.stderr}

    commit_sha = _git(["rev-parse", "HEAD"], home_dir).stdout.strip()

    if not skip_push:
        push_res = _git(
            [
                "push",
                "--force-with-lease",
                "origin",
                f"HEAD:{working_branch}",
            ],
            home_dir,
            timeout=120,
        )
        if push_res.returncode != 0:
            return {
                "error": "push_failed",
                "stderr": push_res.stderr,
                "commit_sha": commit_sha,
            }

    return {
        "snapshot_dir": str(backup_rel) + "/",
        "files_preserved": restored,
        "commit_sha": commit_sha,
        "working_branch": working_branch,
    }


@router.post("/api/git/reset-to-main-preserve-state")
async def reset_to_main_preserve_state():
    """Adopt origin/main as the baseline, preserving allowlisted files (S3, #384).

    The sync-time counterpart to the persistent-state allowlist (#383).
    Snapshots every file matching the allowlist to `.trinity/backup/<ts>/`
    before running `git reset --hard origin/main`, then overlays the
    snapshot back, commits `Adopt main baseline, preserve state`, and
    pushes with `--force-with-lease`.

    Backend must verify the agent is not running a task before calling this
    endpoint; the check lives there because this server has no view of the
    activity service.
    """
    home_dir = Path("/home/developer")
    try:
        result = reset_to_main_preserve_state_impl(home_dir)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")

    err = result.get("error")
    if err == "no_git_config":
        raise HTTPException(
            status_code=409,
            detail="Agent has no git configuration",
            headers={"X-Conflict-Type": "no_git_config"},
        )
    if err == "no_remote_main":
        raise HTTPException(
            status_code=409,
            detail="Remote origin has no main branch",
            headers={"X-Conflict-Type": "no_remote_main"},
        )
    if err:
        stderr = result.get("stderr", "")
        detail = f"{err}: {stderr[:500]}" if stderr else err
        raise HTTPException(status_code=500, detail=detail)
    return result
