"""
Git sync endpoints for GitHub bidirectional sync.
"""
import json
import os
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException

from ..models import GitSyncRequest, GitPullRequest

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Sync state file (#389 S1a) — small JSON persisted under .trinity/sync-state.json
# so counters survive container restarts. The backend's SyncHealthService
# reads these fields via GET /api/git/status every minute.
# ---------------------------------------------------------------------------

_SYNC_STATE_DEFAULT: Dict = {
    "last_sync_status": "never",
    "last_sync_at": None,
    "last_error_summary": None,
    "consecutive_failures": 0,
}


def _sync_state_path(home_dir: Path) -> Path:
    return home_dir / ".trinity" / "sync-state.json"


def _read_sync_state_file(home_dir: Path) -> Dict:
    """Read `.trinity/sync-state.json` or return defaults on missing/corrupt."""
    path = _sync_state_path(home_dir)
    if not path.exists():
        return dict(_SYNC_STATE_DEFAULT)
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError("sync-state.json root is not an object")
        merged = dict(_SYNC_STATE_DEFAULT)
        merged.update(data)
        return merged
    except (ValueError, json.JSONDecodeError):
        logger.warning("sync-state.json corrupt, returning default")
        return dict(_SYNC_STATE_DEFAULT)


def _write_sync_state_file(
    home_dir: Path,
    last_sync_status: str,
    last_sync_at: Optional[str] = None,
    last_error_summary: Optional[str] = None,
) -> Dict:
    """Persist one sync outcome.

    consecutive_failures is bumped on `failed`, reset on `success`, untouched
    on `never`. last_error_summary is cleared on success, kept on never.
    """
    prior = _read_sync_state_file(home_dir)

    if last_sync_status == "failed":
        prior["consecutive_failures"] = (prior.get("consecutive_failures") or 0) + 1
        prior["last_error_summary"] = last_error_summary
    elif last_sync_status == "success":
        prior["consecutive_failures"] = 0
        prior["last_error_summary"] = None
    # else 'never' — leave counters alone

    prior["last_sync_status"] = last_sync_status
    prior["last_sync_at"] = last_sync_at or datetime.now(timezone.utc).isoformat()

    path = _sync_state_path(home_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prior, indent=2))
    return prior


def _run_auto_sync_once(home_dir: Path) -> Dict:
    """One auto-sync cycle: stage, commit if dirty, push. Records outcome.

    Intentionally minimal — heavy conflict handling stays in the operator-
    initiated `sync_to_github` endpoint. Auto-sync is a heartbeat, not a
    rescue.
    """
    now = datetime.now(timezone.utc).isoformat()
    try:
        # Stage everything.
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(home_dir), capture_output=True, text=True, timeout=30, check=True,
        )

        # Is there anything to commit?
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(home_dir), capture_output=True, text=True, timeout=10,
        )
        if status.stdout.strip():
            commit_msg = f"Trinity auto-sync: {now}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(home_dir), capture_output=True, text=True, timeout=30, check=True,
            )

        push = subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=str(home_dir), capture_output=True, text=True, timeout=60,
        )
        if push.returncode != 0:
            err = _summarize_git_error(push.stderr or push.stdout or "push failed")
            _write_sync_state_file(home_dir, "failed",
                                    last_sync_at=now, last_error_summary=err)
            return {"status": "failed", "error": err}

        _write_sync_state_file(home_dir, "success", last_sync_at=now)
        return {"status": "success"}

    except subprocess.CalledProcessError as exc:
        err = _summarize_git_error(exc.stderr or exc.stdout or str(exc))
        _write_sync_state_file(home_dir, "failed",
                                last_sync_at=now, last_error_summary=err)
        return {"status": "failed", "error": err}
    except Exception as exc:  # defensive — never let the loop crash
        err = _summarize_git_error(str(exc))
        _write_sync_state_file(home_dir, "failed",
                                last_sync_at=now, last_error_summary=err)
        return {"status": "failed", "error": err}


def _summarize_git_error(raw: str) -> str:
    """Trim git stderr to a 240-char one-liner (matches operator-queue field size)."""
    if not raw:
        return "unknown error"
    first = raw.strip().splitlines()[0]
    return first[:240]


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


def _compute_ahead_behind(ref: str, home_dir: Path) -> tuple[int, int]:
    """Return (behind, ahead) for HEAD relative to origin/<ref>.

    Returns (0, 0) when the ref does not exist on origin (e.g. never pushed,
    or the ref name is bogus) — the caller should treat this as "no peer yet",
    not "in sync". Callers that need to distinguish should check ref existence
    separately via `git rev-parse --verify origin/<ref>`.
    """
    result = subprocess.run(
        ["git", "rev-list", "--left-right", "--count", f"origin/{ref}...HEAD"],
        capture_output=True,
        text=True,
        cwd=str(home_dir),
        timeout=10,
    )
    if result.returncode != 0:
        return (0, 0)
    parts = result.stdout.strip().split()
    if len(parts) != 2:
        return (0, 0)
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return (0, 0)


def _dual_ahead_behind_payload(current_branch: str, home_dir: Path) -> dict:
    """Return ahead/behind tuples for both `origin/main` and the working branch.

    Fixes P6 (#389): the old implementation redirected `trinity/*` branches to
    `origin/main` for ahead/behind, hiding external writes to the working
    branch. We now compute BOTH tuples:

    - `ahead_main`/`behind_main`     — against `origin/main` (template sync)
    - `ahead_working`/`behind_working` — against `origin/<current_branch>`
      (peer divergence / P5-style silent clobber)

    Legacy aliases `ahead` and `behind` track the main tuple to preserve
    backward compatibility with clients written against the old response.
    """
    main_behind, main_ahead = _compute_ahead_behind("main", home_dir)
    # Non-trinity branches use the same ref twice; avoid a second subprocess
    # for the common case.
    if current_branch.startswith("trinity/") and current_branch != "main":
        working_behind, working_ahead = _compute_ahead_behind(current_branch, home_dir)
    else:
        working_behind, working_ahead = main_behind, main_ahead

    return {
        "ahead": main_ahead,  # legacy alias
        "behind": main_behind,  # legacy alias
        "ahead_main": main_ahead,
        "behind_main": main_behind,
        "ahead_working": working_ahead,
        "behind_working": working_behind,
    }


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

        # #389 P6: compute ahead/behind against BOTH origin/main and the
        # working branch's own remote, so external writes to trinity/* are
        # visible in the UI. Legacy `ahead`/`behind` keys still alias the
        # main tuple.
        ahead_behind = _dual_ahead_behind_payload(current_branch, home_dir)
        ahead = ahead_behind["ahead"]
        behind = ahead_behind["behind"]

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

        response = {
            "git_enabled": True,
            "branch": current_branch,
            "remote_url": remote_url,
            "last_commit": last_commit,
            "changes": changes,
            "changes_count": len(changes),
            "sync_status": "up_to_date" if ahead == 0 and len(changes) == 0 else "pending_sync",
        }
        # #389: dual ahead/behind tuples plus legacy ahead/behind aliases.
        response.update(ahead_behind)
        # #389: merge auto-sync heartbeat state (may be defaults if never run).
        response["sync_state"] = _read_sync_state_file(home_dir)
        return response

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
