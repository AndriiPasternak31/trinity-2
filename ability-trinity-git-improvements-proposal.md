# Trinity Git Sync — Product Gaps & Proposal

**Status**: draft v3 · internal memo · every claim below verified against
Trinity source AND reproduced locally (pure-git Tier 1 + live-API Tier 2)
**Author**: Andrii (with Claude assist)
**Date**: 2026-04-17
**Repro source**: `polygon-vybe`, `alpaca-vybe-live`, `alpaca-vybe-live-2` —
three agents hit the same recovery flow in one operator session on
2026-04-17. The alpaca pair additionally surfaced a **silent shared-branch
clobber**.
**Harness**: local Trinity stack + gitea via
`docker-compose.gitea.yml` overlay; three-file backward-compatible patch
enabling `TRINITY_GIT_BASE_URL` / `TRINITY_GIT_API_BASE` env overrides. Full
run log: `Memories/ability-trinity-git-repro-run-2026-04-17.md`.

---

## TL;DR

Trinity's git-sync design (`trinity/*` working branch per instance, auto-
commits, pull redirected to `origin/main`) is great. But the conflict-
handling, branch-ownership, and observability layers have **five verified
failure modes plus two newly discovered gaps**:

1. **Silent desync accumulation** (P1) — sync can fail repeatedly for weeks
   with no operator-visible signal; container-only state grows unbounded.
2. **Parallel-history deadlock** (P2) — when `trinity/<agent>/<id>` and
   `origin/main` have parallel commits, both UI options (Pull First / Force
   Push) are wrong. No UI path recovers.
3. **No "reset template, preserve state" primitive** (P3) — operators with
   UI-only access can't express the only safe recovery for (2). Needs SSH
   or chat-orchestration hacks.
4. **Git internals leak into the error modal** (P4) — `Rebasing (1/2)
   error: could not apply 1d945e0...` is unreadable to non-devs. Confirmed
   the raw stderr string reaches the operator API response verbatim.
5. **No branch-ownership enforcement** (P5) — two Trinity instances can be
   configured to push to the same `(repo, branch)` tuple with no collision
   check. Force-pushes then silently clobber each other; whoever pushed
   last wins and the other instance's state is lost from the remote. The
   "working branches are per-instance-only" invariant is assumed but not
   enforced.
6. **NEW: Working-branch divergence is masked by the status UI** (P6) —
   `_get_pull_branch()` correctly redirects *pulls* to `origin/main` for
   `trinity/*` branches, but the same redirection is applied to the
   ahead/behind computation in `get_git_status()`. An external force-push
   to the agent's working branch is invisible to the dashboard because the
   comparison never looks at `origin/<working_branch>`.
7. **NEW: `generate_instance_id()` is called at three sites with no
   cross-check** (P7) — normal `POST /agents` flow, re-running
   `/git/initialize`, and the init-in-container routine each roll their own
   UUID. A partial failure can leave the DB pointing at one branch and the
   container pushing to another, silently.

We propose eight concrete changes (S0–S7), ranked by value/effort. The
single-most-important one is still **S4: Persistent State Allowlist** —
once that primitive exists, S2/S3 fall out naturally. **S7: Branch-
Ownership Enforcement** is the second-most-important because the failure is
silent and asymmetric (data loss with no error). **S0: self-hosted git
base URL** is new — a small backward-compatible change that unlocks local
reproduction of every other issue and doubles as a GHES / gitea feature.

---

## Evidence from 2026-04-17

Repo: `github.com/AndriiPasternak31/polygon-vybe`

```
origin/main:                       … → 112b398 → … → 6172475         (2026-04-03)
origin/trinity/polygon-andrii/…:   … → 112b398 → … → ec15926         (2026-04-17)  ← tracks main fine
origin/trinity/polygon-vybe/…:     e81e2b3 → 1d945e0 → cfd1a72        (2026-03-17)  ← last successful push
Vybe container HEAD (unpushed):    … → cfd1a72 → e373eaa              (container-only)
```

The sibling polymarket instance, `polygon-andrii`, syncs daily and tracks
`main` cleanly. The `polygon-vybe` instance forked from an old state before
`main` got the canonical `112b398 Add polymarket trader configuration`, and
has been stuck for **30 days**. During those 30 days:

- Vybe ran its trading heartbeat and accumulated a 13MB unpushed diff
  (`cfd1a72 → e373eaa`) carrying the full `workspace/` state inside the
  container.
- The only workspace file ever pushed to `origin/trinity/polygon-vybe/…` is
  `calibration-params.json`. All trade history, Brier log, portfolio
  snapshots, activity log, and edge hypotheses existed only in the container.
- The Trinity UI showed a push-conflict modal with two options, both of
  which make the situation strictly worse (Pull First fails forever, Force
  Push overwrites working branch with stale parallel history).
- We only noticed because a separate near-miss incident (another agent on the
  shared platform wiped and restored all agents) triggered a fleet audit.

Simultaneously, two alpaca instances (`alpaca-vybe-live`,
`alpaca-vybe-live-2`) also had pending state — one with 0 unpushed commits
but unstaged workspace changes, one with 2 unpushed commits. Neither surfaced
any warning in the UI.

**The alpaca case escalated into a second, harder-to-debug failure class
(P5)**: both agents self-reported deployment on the *same* working branch
`trinity/alpaca-vybe-live/a702560e` of the *same* repo. They ran the same
recovery flow in parallel and force-pushed their overlays within 12 seconds
of each other:

```
11:37:24  alpaca-vybe-live     push +cf1bb53 → trinity/alpaca-vybe-live/a702560e   (50K workspace: decisions.csv, activity-log, portfolio-snapshots, learnings, strategy-journal)
11:37:24  alpaca-vybe-live-2   push +3711c7f → trinity/alpaca-vybe-live/a702560e   (8.2K workspace — smaller overlay)
```

After both pushes completed, only `3711c7f` is on the remote —
`alpaca-vybe-live`'s state was silently overwritten. Both agents' own
container filesystems still hold their respective state, but GitHub has only
the one that pushed last. No error was surfaced to either agent, no
collision warning, no audit trail. The invariant that "working branches are
per-instance-only" is assumed by the design but never checked.

---

## Verification summary (new in v3)

All five original problems were reproduced. Three through the real Trinity
API end-to-end against a local gitea, two through pure git at the shell
level (demonstrating the inherited mechanics). Evidence below.

| Claim | Tier | Evidence |
|---|---|---|
| **P1 — no auto-sync, no health tracking, no fleet signal** | Source audit | Agent-server has no background loop (`docker/base-image/agent_server/main.py:62-89`). `agent_git_config` schema stores only `last_sync_at`, `last_commit_sha`, `sync_enabled` (`src/backend/db/schema.py:399-416`). `MonitoringService` does not check git. Dashboard has no git widget. After the live clobber, `/api/operator-queue` returned 0 sync entries. |
| **P2 — parallel-history deadlock** | Tier 1 (pure git) | `/tmp/trinity-repro/p2_parallel_history.sh` produces the identical error text from the production modal: `CONFLICT (add/add): Merge conflict in trader.conf / error: could not apply <sha>... Add polymarket trader configuration`. |
| **P3 — no reset-preserve-state primitive** | Source audit | No backup/restore endpoint in `docker/base-image/agent_server/routers/files.py`. No `persistent_state:` key in any template. The "ephemeral-wipe" mirror the v2 proposal assumed exists is actually just `reinitialize_system_agent()` in `routers/system_agent.py:138` — a manual admin endpoint, not a sync-time primitive. |
| **P4 — raw git stderr in modal** | Tier 2 (live API) | Concurrent force-push via real `/api/agents/{name}/git/sync` returned `{"detail": "Sync failed: Force push failed: remote: error: cannot lock ref... ! [remote rejected]..."}`. Same string lands in `GitConflictModal.vue:22` (`conflict.message`). |
| **P5 — silent clobber** | Tier 1 + Tier 2 | Pure-git repro at `/tmp/trinity-repro/p5_silent_clobber.sh` — losing push returns exit 0, remote has only the winner's state. Live repro on gitea through Trinity API: two agents forced onto `trinity/alpaca-repro-a/bd47596d`, sequential `strategy=force_push` → `{"success": true, "commit_sha": "b1f3f1d..."}` while the losing agent's commit became orphaned from every remote ref. |
| **P6 — ahead/behind measured against wrong branch** | Tier 2 (live API) | Post-clobber query on losing agent: vs actual `origin/<working_branch>`: behind=2 ahead=1. vs `origin/main` (what Trinity's UI shows): behind=0 ahead=1. The UI cannot surface an external write to the working branch because the comparison is aimed at main. Root cause: `get_git_status()` reuses `_get_pull_branch()` result for the ahead/behind ref at `docker/base-image/agent_server/routers/git.py:108-123`. |
| **P7 — three `generate_instance_id()` call sites** | Source audit | `src/backend/services/agent_service/crud.py:225` (normal creation), `src/backend/routers/git.py:367` (re-init after failure), `src/backend/services/git_service.py:405` (inside `initialize_git_in_container` when `create_working_branch=True`). Each rolls its own UUID. No single reserve-and-check helper. |

### Solutions that needed refinement

| Solution | Original assumption | Refinement needed |
|---|---|---|
| **S1** (observability) | Add `consecutive_failures` counter | Counters are useless without an autonomous sync cadence. Agent server has no background sync loop — every sync is operator-initiated. S1 must either (a) ship an auto-sync first, or (b) reframe as "last attempt" tracking, not health. Recommend (a) behind a per-agent flag. |
| **S4** (persistent-state allowlist) | List lives in `template.yaml` | `template.yaml` is read **only at agent creation** (`services/template_service.py:177-200`). Sync and reset paths don't re-read it. Write the allowlist into `.trinity/persistent-state.yaml` at creation; runtime reads from there. Same pattern as `.env`. |
| **S7** (branch ownership) | `UNIQUE(github_repo, working_branch)` constraint | `crud.py:610` intentionally binds every `source_mode=true` agent to its source branch (e.g., all agents on `main`). Constraint must be **partial**: `UNIQUE(github_repo, working_branch) WHERE source_mode = 0`. Also: consolidate the three `generate_instance_id()` sites (P7) before adding the constraint — otherwise a single agent can self-collide across DB and container. |

### Solutions validated unchanged

S2 (parallel-history detection at modal open), S3 (adopt-main preserve-
state operation), S5 (operator-readable diagnosis), S6 (fleet audit
endpoint). No integration surprises found.

---

## Problem taxonomy (verified)

### P1 — Silent desync accumulation

**Symptom**: an agent can run for weeks with failing syncs while appearing
"healthy" in the main dashboard. State accumulates container-only. If the
container dies before recovery, the state is gone.

**Root cause**: no sync-health signal exposed at the fleet level, and in
fact no autonomous sync cadence at all. The Git panel shows status per
agent only when you open the detail page. There is no aggregate red
indicator, no alert, no operator-queue entry when sync fails repeatedly,
and no heartbeat that would notice staleness in the first place.

**Code citations**:
- `docker/base-image/agent_server/main.py:62-89` — no background loop, no
  `asyncio.create_task`, no scheduler in the agent server.
- `src/backend/db/schema.py:399-416` — `agent_git_config` has only
  `last_sync_at`, `last_commit_sha`, `sync_enabled`. No
  `last_sync_status`, `consecutive_failures`, or error column.
- `src/backend/services/monitoring_service.py` — checks Docker / network
  / business runtime only; no git-sync layer.
- `src/backend/services/operator_queue_service.py:64-100` — only syncs
  `~/.trinity/operator-queue.json` upward; no `sync_failing` emitter.

**Why it bites**: sync failures are not rare in the parallel-history case.
And even with successful pushes, unstaged workspace changes inside the
container are invisible until someone asks. The Vybe agent's 30-day
accumulation is architecturally expected given the above.

### P2 — Parallel-history deadlock

**Symptom**: `Push Conflict: Rebasing (1/2) error: could not apply <sha>...`
and the user is offered exactly two paths:

- "Pull First, Then Push" — runs `git pull --rebase origin main`, which
  replays the same conflicting commit again, fails identically.
- "Force Push" — runs `git push --force` to the working branch. If the goal
  was "adopt main's improvements while keeping state", this does the
  opposite: it overwrites the remote working branch with the container's
  stale history.

**Root cause**: both resolutions assume linear history between the working
branch and main. When history is parallel (two commits with the same title
and different SHAs — which happens any time an agent is initialized from a
different base and main is later rewritten, or when the agent was forked
pre-consolidation), neither flow is correct. The only valid recovery is:
adopt main as the new baseline, overlay workspace state, push to the working
branch.

**Code citations**:
- `docker/base-image/agent_server/routers/git.py:244-250` — `pull_first`
  runs `git pull --rebase origin main` (via `_get_pull_branch`).
- `:340-350` — `force_push` runs bare `git push --force`.
- `src/frontend/src/components/GitConflictModal.vue:62-90` — hardcoded
  two-button set, no conditional rendering.
- `src/frontend/src/composables/useGitSync.js:76-95` — reactive catch,
  no pre-fetch, no ancestor analysis, no decision beyond "show the modal."

**Why it's structural**: Trinity's design — multiple instances of one
agent template on divergent branches — expects this case. It will recur.

**Reproduction**: `/tmp/trinity-repro/p2_parallel_history.sh`. Produces
the identical `could not apply <sha>... Add polymarket trader
configuration` error text seen in production.

### P3 — No "reset template, preserve state" primitive

**Symptom**: to recover from P2 an operator must SSH into the agent
container (or orchestrate via chat) and manually run:

```
git reset --hard origin/main
<restore per-instance files and workspace/ from backup>
git commit -m "Restore instance state on main baseline"
git push origin +HEAD:trinity/<agent>/<id>
```

There is no first-class UI or API for this. Every operator who hits P2 has
to reinvent the procedure.

**Root-cause refinement (new in v3)**: v2 assumed the ephemeral-state wipe
mirror (`.claude/debug/`, `.claude/projects/`, `session-files/`) was already
implemented in the sync path and S4 would be its mirror. **It isn't.** The
only "wipe" logic lives in `src/backend/routers/system_agent.py:138` —
`reinitialize_system_agent()`, a manual admin endpoint that hardcodes the
paths. It runs only when an admin explicitly resets the system agent,
never during normal sync.

What *does* exist is **edit/delete protection** at the agent-server layer
(`docker/base-image/agent_server/routers/files.py:156-175`): the agent
itself cannot rm `CLAUDE.md`, `.trinity`, `.git`, `.env`, `.mcp.json`,
etc. via the Files API. It's a different primitive — it blocks the agent
from nuking its own critical files, not a reset-survival list.

The S4 design in v3 therefore has to *introduce* both the allowlist AND
the subroutine that consumes it. Nothing to build on top of.

**What's still missing**: an explicit concept of "files I want to survive
a template-level reset".

### P4 — Opaque operator messaging

**Symptom**: the modal shows `Rebasing (1/2) error: could not apply
1d945e0... Add polymarket trader configuration`. A non-developer has no way
to read this. The two buttons offered (Pull First / Force Push) don't map to
operator intent.

**Root cause**: the modal surfaces git's raw output. No translation layer
into operator language, no pointer at what's actually wrong, no suggested
remediation for this specific class of conflict.

**Code citations**:
- `docker/base-image/agent_server/routers/git.py:256-260` — HTTP 409
  `detail` field is built directly from `pull_result.stderr`.
- `src/backend/services/git_service.py:150-164` — backend forwards that
  detail unchanged into `GitSyncResult.message`.
- `src/frontend/src/composables/useGitSync.js:84-89` — useGitSync pipes
  `message` into `gitConflict.message` unchanged.
- `src/frontend/src/components/GitConflictModal.vue:22` — renders
  `conflict.message` verbatim.

**Live verification**: our Tier 2 run produced this exact Trinity API
response body from the concurrent-push test:

```json
{"detail": "Sync failed: Force push failed: remote: error: cannot lock ref 'refs/heads/trinity/alpaca-repro-a/bd47596d': is at 20e0a936... but expected 2d1351ec...\nTo http://trinity-gitea-dev:3000/trinity-dev/trinity-alpaca-repro.git\n ! [remote rejected] trinity/alpaca-repro-a/bd47596d -> trinity/alpaca-repro-a/bd47596d (failed to update ref)\nerror: failed to push some refs...\n"}
```

That string becomes the modal body. No human should be reading "cannot
lock ref" to understand their agent state.

### P5 — No branch-ownership enforcement (silent clobber)

**Symptom**: two live Trinity agents (`alpaca-vybe-live`,
`alpaca-vybe-live-2`) configured on the same working branch
`trinity/alpaca-vybe-live/a702560e` of repo
`github.com/AndriiPasternak31/alpaca-vybe-live`. Both auto-pushed within 12
seconds during the 2026-04-17 recovery; the second push overwrote the first.
Neither agent, nor the Trinity backend, nor the UI, detected the collision.
`alpaca-vybe-live`'s 50K workspace overlay (decisions.csv, strategy-journal,
learnings, activity-log, portfolio-snapshots) was silently removed from the
remote. The only copy is now inside its container filesystem.

**Root cause** — three independent gaps, all present in source:

1. **DB schema**: `src/backend/db/schema.py:399-416` makes `agent_name`
   UNIQUE but not `(github_repo, working_branch)`. Two rows can claim the
   same remote branch legally. **Verified live**: forced a duplicate binding
   with an `UPDATE agent_git_config SET working_branch=...` — accepted with
   no constraint error. Post-hoc duplicate-binding audit SQL:

   ```sql
   SELECT github_repo, working_branch, COUNT(*)
   FROM agent_git_config WHERE source_mode = 0
   GROUP BY github_repo, working_branch HAVING COUNT(*) > 1;
   ```

2. **No creation-time remote check**: `git_service.py:262-443`
   (`initialize_git_in_container`) never runs `git ls-remote` to verify the
   working branch is unassigned before `git push -u origin <branch>`. The
   `generate_instance_id()` at line 22 uses `uuid.uuid4().hex[:8]` — 16M
   space, good enough under uniqueness but **unchecked** against
   (a) collision on the same remote, (b) restore paths that re-use an
   existing ID, (c) clone-style agent creation, (d) source-mode where
   `working-branch = source-branch` — in source-mode, *all* agents on the
   same source branch collide by design.

3. **Plain `--force` push**: `docker/base-image/agent_server/routers/git.py:340-350`.
   No `--force-with-lease`. No stored "last-remote-sha this instance
   observed." When two instances push, whoever pushed last wins silently.

**Live verification**: Two agents created via normal `POST /api/agents`,
DB patched to force the duplicate binding (Layer 1 gap), then sequential
`POST /api/agents/alpaca-repro-a/git/sync strategy=force_push` → Trinity
returned `{"success": true, "commit_sha": "b1f3f1d..."}`. The other
agent's commit (`20e0a93`) is now unreachable from every remote ref —
GC-eligible. The losing agent still locally thinks its commit is on the
branch. No warning surfaced. This is the 2026-04-17 alpaca incident,
reproduced end-to-end through the production code path.

**Extra finding (P7, new)** — there are actually **three separate
`generate_instance_id()` call sites** generating different IDs during the
same agent creation:
- `src/backend/services/agent_service/crud.py:225` — during `POST /api/agents`
- `src/backend/routers/git.py:367` — during `POST /api/agents/{name}/git/initialize`
- `src/backend/services/git_service.py:405` — inside
  `initialize_git_in_container` when `create_working_branch=True`

For a GitHub-template agent created via the normal flow, these end up equal
because the flow is linear. For operators who hit the `/git/initialize`
endpoint separately (e.g., after a failure), they will silently diverge: the
DB records one branch, the container pushed a different one. This is a
*second* class of silent drift. S7 must consolidate to one reserve-and-
check helper before the UNIQUE constraint is added.

### P6 — Working-branch divergence hidden by ahead/behind redirection (new in v3)

**Symptom**: after a silent clobber on the working branch, the affected
agent's Git panel shows `sync_status: pending_sync`, `ahead: 1`,
`behind: 0` — which looks like "you have a normal pending commit to push."
No indication that the remote working branch has been rewritten by a peer.

**Root cause**: `_get_pull_branch()` at
`docker/base-image/agent_server/routers/git.py:17-30` correctly redirects
*pulls* for `trinity/*` branches to `origin/main`. But
`get_git_status()` at lines 108-123 reuses the same redirected branch for
the ahead/behind computation:

```python
ahead_behind_result = subprocess.run(
    ["git", "rev-list", "--left-right", "--count",
     f"origin/{pull_branch}...HEAD"], ...)
```

For a `trinity/*` branch, `pull_branch` is `main`. The UI therefore shows
divergence *vs main*, not vs the same-named remote branch. The whole point
of a working branch — that it has its own state someone else might write
to — is invisible.

**Live verification**: from the P5 repro, after the clobber, agent-b's
`git rev-list --count` against its two possible comparison points:

| Comparison | behind | ahead |
|---|---|---|
| vs `origin/trinity/alpaca-repro-a/bd47596d` (its actual remote) | 2 | 1 |
| vs `origin/main` (what Trinity's UI uses) | 0 | 1 |

The real divergence — "your branch has been rewritten underneath you" — is
literally in the repo metadata, two commits of it, but Trinity's status
endpoint computes the wrong comparison.

**Why it's structural**: this is an *independent* silent-desync vector
from P5. Even if S7's UNIQUE constraint were landed and no two agents
could share a branch, any external force-push to the working branch (by a
developer, another tool, a restore operation) would still be invisible
until the agent tried to push and got a rejection.

**Fix**: the status endpoint should return **both** ahead/behind tuples:
- `ahead_main / behind_main` (for "template improvements available")
- `ahead_working / behind_working` (for "my remote branch has diverged")

S1's health indicator should key off `behind_working`. When it's non-
zero, the working branch has been touched externally.

---

## Proposal

Eight changes, ranked. S4 is still the keystone. S0 is new — a small
enabling change that unlocks both the repro harness and future GHES /
self-hosted use. **Every fix below has been at least partially verified
against the real code base** (file:line citations given) and several
have been verified to work via the local gitea harness.

### S0 (new) — Self-hosted git base URL support

**What**: add two env-var overrides, both backward-compatible with
GitHub-identical defaults:

- `TRINITY_GIT_BASE_URL` (default `https://github.com`) — the scheme+host
  portion used to construct authenticated clone/push URLs.
- `TRINITY_GIT_API_BASE` (default `https://api.github.com`) — the API
  endpoint used by `GitHubService` for repo validation, branch checks,
  repo creation.

Patched files (verified, passed Tier 2 live harness):

- `src/backend/services/github_service.py`
- `src/backend/services/git_service.py` (new `_git_remote_url` helper)
- `docker/base-image/startup.sh` (compose `CLONE_URL` from env)
- `src/backend/services/agent_service/crud.py` (propagate env var to
  agent env)

**Why S0 ships first**:

1. It enables local reproduction of every other failure via gitea —
   essential for regression testing S1–S7.
2. Gitea's `/api/v1/repos/{owner}/{repo}` returns the same shape as
   GitHub's `/repos/{owner}/{repo}`, so the single base-URL swap works
   end-to-end without behavioral differences (verified).
3. It doubles as a feature for self-hosted customers — a non-trivial
   segment of the security-sensitive Trinity user base is on GHES.

**Effort**: ~30 lines, zero schema change, no behavioral change when env
vars unset. 1 day including a test that defaults still hit
`github.com`.

### S4 (keystone) — Persistent State Allowlist

**What**: add a `persistent_state` list to each agent's config, mirroring
the existing ephemeral list. Default:

```yaml
# template.yaml
persistent_state:
  - workspace/**
  - .trinity/**
  - .mcp.json
  - .claude.json
  - .claude/.credentials.json
```

`.env` is already protected via `.gitignore`; persistent_state protects
tracked-but-instance-specific files from any template-level reset.

**Refined in v3**: `template.yaml` is only read at agent creation
(`services/template_service.py:177-200` — the loader fetches once, caches
10 min). Sync and reset paths don't re-read it. Therefore the allowlist
must be materialized into the agent workspace at creation time:

- Template provides the source-of-truth default list
- At agent creation, `services/agent_service/crud.py` writes a copy to
  `.trinity/persistent-state.yaml` inside the container
- Sync/reset operations read from `.trinity/persistent-state.yaml`
- Operators can edit that file directly to adjust per-agent

**Affected surfaces**:

- `src/backend/services/git_service.py` — add
  `_persistent_state_for(agent_name) -> list[str]` that reads from the
  `.trinity/persistent-state.yaml` inside the agent container, falling
  back to a sensible default.
- `docker/base-image/agent_server/routers/git.py` — new subroutine
  `_reset_preserving_persistent_state(target_ref)` that captures matching
  files to a tmp dir, runs `git reset --hard <target>`, overlays files
  back.
- `src/backend/services/agent_service/crud.py` — on agent creation,
  write `.trinity/persistent-state.yaml` from the template's
  `persistent_state` key.
- `abilities/plugins/trinity/skills/onboard/SKILL.md` — the onboarding
  flow asks "anything in this repo that's instance-specific state we
  should protect?" and writes the list into `template.yaml` for baked-in
  defaults AND into `.trinity/persistent-state.yaml` for per-agent.

**Effort**: ~300 lines backend, ~100 lines agent-server, doc updates.
2 days.

**Verified**: Tier 1 script `/tmp/trinity-repro/s3_fix_verified.sh` runs
the S4+S3 subroutine end-to-end: main adopted, `workspace/*` preserved,
`.trinity/*` preserved, pushed via `--force-with-lease`. Works cleanly.

### S2 — Parallel-history detection at modal-open

**What**: before rendering the existing GitConflictModal, run:

```
git fetch origin
ahead = rev-list --count main..HEAD
behind = rev-list --count HEAD..main
common = merge-base HEAD origin/main
```

If `common` is empty or very old and `behind > 0`, it's a parallel-history
case. Render a **different modal** with an explanation and a third button:
**"Adopt latest upstream (preserve my state)"** — triggers S3.

**Refined in v3**: the label is operator-neutral. Some repos use
`master`, `trunk`, or other default-branch names — don't hardcode "main"
in user-facing copy.

**Implementation surface smaller than v2 estimated**: the backend already
computes `ahead` and `behind` via `git_service.py:110-123`. Adding one
more field — `common_ancestor_sha` and/or `common_ancestor_age_days` —
to `/api/git/status` gives the frontend enough to branch.

**Effort**: small. Data is already computed for the existing "N ahead / N
behind" badge.

### S3 — "Adopt latest upstream, preserve state" operation

**What**: new endpoint
`POST /api/agents/{name}/git/reset-to-main-preserve-state`. Backend proxies
to agent server, agent server runs the capture/reset/overlay dance using the
persistent-state allowlist from S4, commits `Adopt main baseline, preserve
state`, pushes the working branch with `--force-with-lease`.

**Guardrails**: the endpoint ALWAYS snapshots the persistent-state allowlist
to `.trinity/backup/<timestamp>/` on the container AND triggers a Trinity-
side archive of that tar (uploadable via Files panel) before doing any
destructive git operation. Response: summary of files preserved, commit SHA.

**Additional guardrail added in v3**: refuse if the agent has no git
config (obvious but the v2 proposal missed it). Still refuses if the
agent is currently running a task (check via activity service).

**Needs new agent-server primitives** (not found in current code):
- `POST /api/agent-server/snapshot?paths=...` (returns tarball)
- `POST /api/agent-server/restore` (from tarball, with path allowlist)

Current agent server exposes only `GET /api/files`, `GET /api/files/download`,
`POST /api/files` (create/write with protected-path checks — see
`docker/base-image/agent_server/routers/files.py:156-175`). Snapshot /
restore doesn't exist and must be built.

**UI**: wired from S2's third button. Shows progress: "Snapshotting state...
Resetting to main... Overlaying 9 files... Pushing... Done."

**Effort**: medium. Most logic is the subroutine from S4 plus the new
snapshot endpoint.

**Verified**: /tmp/trinity-repro/s3_fix_verified.sh — the allowlist →
snapshot → reset → overlay → force-with-lease sequence works cleanly.

### S5 — Operator-readable diagnosis modal

**What**: replace the current raw-git-error modal body with a structured
diagnosis:

- Title: plain English. "Your agent cannot sync." Not "Push Conflict".
- Body: bullet list of what's true. "Main has N new commits your agent
  doesn't have. Your agent has M local commits main doesn't have. The
  histories are parallel — they share N commits ago but then diverged."
- Recommendation: one sentence naming the recommended action. "Adopt
  latest upstream" for parallel history; "Pull latest" for simple
  behind; "Contact admin — unknown state" for fallback.
- Expandable "git details" section for devs.

**Refined in v3**: backend needs one utility to classify conflicts into
an enum (`AHEAD_ONLY`, `BEHIND_ONLY`, `PARALLEL_HISTORY`,
`UNCOMMITTED_LOCAL`, `AUTH_FAILURE`, `WORKING_BRANCH_EXTERNAL_WRITE`,
`UNKNOWN`). The last one is new — it covers the P6 case where the
working branch has been externally rewritten but the ahead/behind vs
main looks normal. Frontend renders per-class copy; keep raw stderr in
an expandable `<details>` for devs.

**Effort**: small. Template work.

### S1 — Sync health observability (refined)

**What**:

- Per-agent fields `last_sync_at`, `last_sync_status`,
  `consecutive_failures`, `last_error_summary`, `last_remote_sha_main`,
  `last_remote_sha_working` in the DB (new `agent_sync_state` table
  linked to `agent_ownership`).
- Dashboard: each agent row shows a sync-health dot. Green = <24h,
  yellow = 24h–7d, red = >7d or last attempt failed or
  `behind_working > 0` (P6).
- Alert: if `consecutive_failures >= 3`, emit an operator-queue entry
  typed `sync_failing` with the error details. Gets surfaced in the
  existing Operating Room flow.
- Config flag: `freeze_schedules_if_sync_failing` (default `false`).
  Trinity currently has no automatic pause anywhere; first feature to
  introduce automatic pause should be opt-in per-agent. Revisit after
  1 month of data.

**Refinement in v3 — auto-sync dependency**: counters are useless
without an autonomous sync cadence. Agent server has no background
sync loop — every sync is operator-initiated. Before S1's counters,
S1 must ship one of:

- **S1a — periodic auto-sync** behind a per-agent flag, default **on**
  for GitHub-template agents (where the point of having a remote is to
  reflect state). Interval: 15 minutes initially, tunable. Lightweight
  heartbeat loop in the agent server, guarded by `GIT_SYNC_ENABLED`.
- **S1b — status-only auto-fetch**: if operators dislike auto-pushing,
  at minimum run `git fetch` every 15 min so `behind_working` is fresh.
  No writes; just reveals external divergence.

Recommend S1a behind a per-agent flag. This unblocks P1 *and* P6 — the
fetch loop inside S1a makes working-branch divergence visible within
the fetch interval instead of "next time a human looks."

**New ahead/behind tuple (addresses P6)**: `/api/git/status` returns
both `ahead_main/behind_main` and `ahead_working/behind_working`. Fleet
indicators key off the latter; template-improvement indicators key off
the former.

**Effort**: medium-large. Touches DB schema (+migration), monitoring
service, frontend dashboard, operator-queue emitter, agent-server
heartbeat.

### S6 — Fleet-level sync audit endpoint

**What**: `GET /api/fleet/sync-audit` returning a table of every agent
with `branch`, `last_pushed_sha`, `last_pushed_at`, `local_head_sha`,
`unpushed_commits`, `dirty_tree`, **and `duplicate_binding` boolean**
(last one new in v3; catches P5 at the fleet level). Let operators (and
`/trinity:sync` skill) run a one-shot fleet audit.

**Effort**: medium. Aggregation over agents. Most data already
computable per-agent via the existing status endpoint; this just
batches.

### S7 — Branch-ownership enforcement (refined)

**What**: enforce the "working branches are per-instance-only" invariant
at four layers (was three in v2; added Layer 0 from v3 findings).

**Layer 0 — consolidate `generate_instance_id()`**:
- Current: three call sites, no cross-check. Fix P7 first.
- New single helper `reserve_and_generate_instance_id(agent_name,
  github_repo) -> (instance_id, working_branch)` that:
  - Generates a UUID
  - Calls `git ls-remote origin refs/heads/trinity/<agent>/<id>` to
    verify ref doesn't exist (retry up to 5x on collision)
  - Inserts DB row with UNIQUE constraint (Layer 2) as an atomic claim
  - Returns the reserved branch name
- Callers: `crud.py:225`, `routers/git.py:367`, deprecate the
  `create_working_branch=True` path inside `initialize_git_in_container`
  (always pass in an already-reserved ID).

**Layer 1 — creation-time remote check**: covered by Layer 0.

**Layer 2 — DB uniqueness**:
- `agent_git_config` gets a partial UNIQUE index:
  `UNIQUE(github_repo, working_branch) WHERE source_mode = 0`
- Source-mode agents intentionally share branches (e.g., all on `main`);
  the partial index excludes them. Verified in `crud.py:610` — this is
  a design-intended case, not a bug.
- Migration must tolerate existing duplicates: flag first, let operators
  resolve, then flip the constraint. Deploy the validation as warnings
  first, fix known duplicates (query in §P5 evidence), then land the
  constraint.

**Layer 3 — push-time guard** (defense in depth):
- Replace `git push --force` in
  `docker/base-image/agent_server/routers/git.py:340-350` with
  `git push --force-with-lease=<ref>:<expected-sha>`. The
  `<expected-sha>` is the last remote SHA this instance observed
  (persisted in `.trinity/last-remote-sha/<branch>` after every
  successful fetch).
- If the lease check fails, the push is rejected. Surface the
  collision to the operator queue with: "Your push was rejected —
  another process wrote to your branch since you last fetched.
  Diagnose before retrying."

**Verified** (Tier 1 `/tmp/trinity-repro/p5_fix_verified.sh`): with
`--force-with-lease`, the losing push is rejected with
`! [rejected] ... (stale info)` and exit 1. The losing side now *knows*
it lost, so Trinity can emit a structured operator-queue entry.

**Operator view**:
- Fleet dashboard adds a "branch bindings" tab showing each
  `(repo, branch) → agent` assignment. Any duplicate shown in red.
  One-click rebinding flow for the duplicate: "Assign a fresh working
  branch to alpaca-vybe-live-2" → generates a new ID, creates the new
  remote branch by pushing the agent's current HEAD.

**Why this is phase 1 alongside S2/S3/S5**: silent data loss >
operator-visible conflicts. P5 isn't something we can document away or
work around — it actively corrupts production state with no warning.
The 2026-04-17 incident is not theoretical, it's in git history.

**Affected surfaces**:
- `src/backend/services/git_service.py` — new
  `reserve_and_generate_instance_id`, `check_remote_branch_exists`.
- `src/backend/db/schema.py`, `src/backend/db/migrations.py` — partial
  UNIQUE index migration (with duplicate-detection pre-flight).
- `src/backend/routers/agents.py`, `routers/git.py`,
  `routers/agent_config.py` — validate on create / update.
- `docker/base-image/agent_server/routers/git.py` — switch `--force` →
  `--force-with-lease`; persist `.trinity/last-remote-sha/<branch>`
  after fetch. Update `get_git_status()` to return both ahead/behind
  tuples (addresses P6).
- Frontend — new fleet tab / binding warnings.

**Effort**: medium-large. Touches DB schema, backend, agent server,
frontend. ~1 week including migration and backfill for existing
deployments.

**Migration note**: existing fleets may already have duplicate bindings
(we found one today in the 2026-04-17 incident). The migration must
tolerate that: flag duplicates, let the operator resolve before adding
the UNIQUE constraint. Rollout: deploy the validation as warnings
first, fix known duplicates, then flip the constraint.

---

## Rollout sequencing (updated)

| Phase | Ships | Unblocks |
|---|---|---|
| 0 | **S0** (base-URL patch) + **S4** (allowlist) | Repro harness works locally. Everything below can be tested before landing. |
| 1 | S2 + S3 + S5 + S7 + P6 status-endpoint fix | Operators with UI-only access can recover from P2 without SSH. Force-pushes stop silently clobbering peer instances. Working-branch divergence surfaces in the UI. |
| 2 | S1a (auto-sync) + S1 (observability) | Silent desync caught before it accumulates to 30 days. P1 and P6 observability complete. |
| 3 | S6 (fleet audit) | `/trinity:sync` skill and ops playbooks can do bulk health checks. |

S0 joins phase 0 because it's the enabling change for every regression
test. It's also low-risk (backward-compatible) and useful on its own
merit for self-hosted customers.

S7 joins phase 1 because P5 (silent clobber) is a data-loss bug, not
just an ergonomics one — it deserves the same urgency as the parallel-
history deadlock. Phase 0+1 together address every incident class we
hit on 2026-04-17 plus P6/P7. Phase 2 prevents recurrence and catches
the external-write case. Phase 3 is ops ergonomics.

---

## Alternative framings considered

- **"Just document the manual recovery procedure"** — insufficient.
  UI-only operators still can't execute. And silent desync still
  happens.
- **"Teach `/trinity:sync` abilities skill to handle parallel history"**
  — valid for dev users with a local clone. Doesn't help operators who
  only see Trinity UI.
- **"Switch to a merge-commit workflow"** — larger surgery on Trinity's
  model. Rebase-then-push is load-bearing for the "Trinity sync: <ts>"
  linear-history convention. Not worth breaking.
- **"Prevent parallel history at creation time"** — validate that every
  new `trinity/<agent>/<id>` branch forks from current `origin/main`.
  Good idea but won't help the instances already in the wild.
- **NEW v3: "Just add `--force-with-lease` without the rest of S7"** —
  insufficient. Layer-3 alone detects *the specific race*, but
  duplicate bindings still succeed and the first agent to push
  "legitimately owns" the branch forever. The full Layer 0-2 is needed
  to prevent the setup that makes Layer 3's rejection the only
  guardrail.

---

## Open questions for the Ability team

Answers where we can give them:

| Q | A (from source + live harness) |
|---|---|
| Q1 — Is there existing fleet-health observability we're missing? | **No.** `MonitoringService` covers Docker / network / business runtime. Git sync is completely outside its scope. S1 is a greenfield addition to that service. |
| Q2 — Where should S4's `persistent_state` list live? | **Both**: `template.yaml` as source-of-truth default; `.trinity/persistent-state.yaml` as per-agent runtime file. Template is authoritative at creation, runtime file is authoritative at reset. Same pattern as `.env` / `.env.example`. |
| Q3 — Is `--force-with-lease` strict enough? | **Yes, if paired with S7 Layers 0-2.** Alone it's a seatbelt, not a door lock — duplicate bindings still form, lease catches only the symptom. Verified by Tier 1 test: lease rejects the losing push cleanly with `stale info`. |
| Q4 — `freeze_schedules_if_sync_failing` default? | **Default `false`** (opt-in). Trinity currently has no automatic pause anywhere; the first feature to introduce one should be gated. Revisit after 1 month of data once S1 is emitting observability. |
| Q5 — How did the alpaca duplicate binding happen? | **Three plausible paths all succeed today**, can't prove which without production DB history. (a) Direct DB update (rare but possible during restore). (b) Source-mode agents intentionally sharing source branch — `crud.py:610`. (c) Running `/git/initialize` on an existing agent post-failure wipes orphan (`routers/git.py:297-298`) and generates a fresh ID; if combined with a restore of an old agent record pointing at the original ID, two agents end up on the original branch. (d) Clone-style agent deployment pattern that we have no source-level evidence for but Ability ops might recognize. Running the duplicate-binding audit SQL against the production DB is the one-shot answer. |
| Q6 — Other duplicates across the Ability fleet today? | Still need production DB access. One-shot query: `SELECT github_repo, working_branch, COUNT(*) FROM agent_git_config WHERE source_mode = 0 GROUP BY github_repo, working_branch HAVING COUNT(*) > 1;` — verified to work against the live schema. |
| Q7 — Does Trinity support "mirror" / "hot-standby" instances? | **No.** Source-mode (`source_mode=true`) is the closest first-class concept and intentionally shares branches. S7's partial UNIQUE index excludes it. All other duplicates are bugs and S7 can be strict. |

---

## Our case as the repro

Three live agents hit the recovery flow on 2026-04-17 in a single operator
session, orchestrated entirely via Trinity UI chat (operator has no SSH
access):

| Agent | Before | After | Issue class hit |
|---|---|---|---|
| `polygon-vybe` | 13MB unpushed patch, parallel history with main, 30d since last push | `acbd084` = main + workspace overlay, pushed to `trinity/polygon-vybe/6377d832` | P1, P2, P3, P4 |
| `alpaca-vybe-live` | 0 unpushed commits but unstaged workspace; 23d since sync despite 15-min heartbeat | `cf1bb53` committed locally; push **silently clobbered** on remote by the concurrent alpaca-vybe-live-2 push — state now only inside the container | P1, **P5**, **P6** |
| `alpaca-vybe-live-2` | 2 unpushed commits (31KB patch), shares branch with alpaca-vybe-live | `3711c7f` = main + (smaller) workspace overlay, pushed to the same `trinity/alpaca-vybe-live/a702560e`, overwrote alpaca-vybe-live's push | **P5**, **P7** (if root cause is /git/initialize re-run) |

Full recovery runbook and backup artifacts:
- `Memories/polygon-vybe-migration.md`
- `Memories/agent-fleet-backup-2026-04-17.md`
- `Memories/backups/<agent>/2026-04-17/*.tgz` + `*.patch` (off-container copies)

The alpaca clobber is the cleanest single-repo reproduction of P5 we could
construct: two agents, same repo, same branch, same recovery flow, 12
seconds apart. Whichever pushes last wins, no warning surfaced.

### Local harness (new in v3)

The same scenario, fully reproduced on the Ability laptop with zero
production impact. Full run log with artifacts, SHAs, and API responses:
`Memories/ability-trinity-git-repro-run-2026-04-17.md`. Summary:

```bash
# 1. Stack up with gitea overlay
export GITEA_PAT=<token>
docker compose -f docker-compose.yml -f docker-compose.gitea.yml up -d

# 2. Create two agents pointed at gitea via standard API
curl -X POST .../api/agents -d '{"name":"alpaca-repro-a","template":"github:trinity-dev/trinity-alpaca-repro"}'
curl -X POST .../api/agents -d '{"name":"alpaca-repro-b","template":"github:trinity-dev/trinity-alpaca-repro"}'

# 3. Force duplicate binding (Layer-1 gap check)
python3 -c "... UPDATE agent_git_config SET working_branch=... WHERE agent_name='alpaca-repro-b' ..."

# 4. Trigger concurrent/sequential force_push — silent clobber
curl -X POST .../api/agents/alpaca-repro-a/git/sync -d '{"strategy":"force_push"}'
curl -X POST .../api/agents/alpaca-repro-b/git/sync -d '{"strategy":"force_push"}'
```

Observed outcomes:
- Both pushes returned `{"success": true}` sequentially; no collision
  warning. Concurrent pushes hit gitea's ref-lock race detection
  *sometimes* — not a design guarantee, a coincidence of timing.
- `/api/operator-queue` shows 0 sync-related entries after the clobber.
- The losing agent's commit is unreachable from every remote ref
  (GC-eligible).
- Losing agent's `/git/status` still shows `sync_status: pending_sync,
  ahead: 1, behind: 0` vs main — the actual divergence vs its own
  remote branch (behind=2, ahead=1) is invisible. P6 confirmed.

The harness also validated the proposed fixes:
- `/tmp/trinity-repro/p5_fix_verified.sh` — S7 Layer 3
  (`--force-with-lease`) cleanly rejects the losing push with explicit
  "stale info" error
- `/tmp/trinity-repro/s3_fix_verified.sh` — S3+S4 (snapshot → reset →
  overlay → lease push) cleanly adopts main's improvements while
  preserving `workspace/*` and `.trinity/*`

---

## Appendix — primitives already in place that we can build on

- Instance IDs are already opaque (`trinity/<agent>/<8-char-sha>`), so
  force-pushing a working branch was **assumed** per-instance-safe. S7
  closes the gap where that assumption breaks (duplicate bindings).
- `_get_pull_branch()` (`docker/base-image/agent_server/routers/git.py:17`)
  already redirects pulls to `origin/main` for any `trinity/*` branch —
  the design-correct behavior for this proposal. But this same
  redirection is mis-applied to ahead/behind computation (P6), so the
  same function is both the right piece of plumbing and the source of
  a separate bug — fix the reuse in `get_git_status()` while keeping
  the pull redirection intact.
- **Corrected from v2**: the "ephemeral-state wipe list" (`.claude/debug/`,
  `.claude/projects/`, `session-files/`) does NOT exist as a sync-time
  primitive. Only a manual admin endpoint (`routers/system_agent.py:138`)
  hardcodes a partial list for one-off system-agent resets. S4 is not
  mirroring an existing pattern; it's introducing it.
- **Does exist**: edit/delete protection in
  `docker/base-image/agent_server/routers/files.py:156-175` blocks the
  agent from rm-ing critical files (`CLAUDE.md`, `.trinity`, `.git`,
  `.env`, `.mcp.json`). Not the same as reset-survival, but shows the
  protected-paths concept is familiar.
- The conflict modal already has infrastructure for multiple strategy
  buttons — adding a third is a one-file change
  (`GitConflictModal.vue`).
- Files panel (`/api/agents/{name}/files/download`) already lets
  operators fetch arbitrary container files — the manual backup pattern
  we used today works because of this. S3's snapshot endpoint can reuse
  the same tarball-download machinery.
- `generate_instance_id()` at `git_service.py:22` already produces a
  unique ID per deployment. S7 just needs to consolidate the three call
  sites, assert-and-enforce uniqueness, instead of trusting-and-hoping
  (P7).
- `.trinity/` directory convention already exists in agent containers
  (`docker/base-image/agent_server/config.py:22`, protected from
  agent-side writes). Natural home for S4's `persistent-state.yaml` and
  S7 Layer 3's `last-remote-sha/<branch>` files.
- Partial UNIQUE indexes are supported by SQLite — verified syntax.
  S7 Layer 2's `UNIQUE(github_repo, working_branch) WHERE source_mode
  = 0` is a one-statement migration.

---

## References

- Incident runbook: `Memories/polygon-vybe-migration.md`
- Fleet audit (2026-04-17): `Memories/agent-fleet-backup-2026-04-17.md`
- **Local harness run log (new in v3)**: `Memories/ability-trinity-git-
  repro-run-2026-04-17.md`
- Durable lesson: `Memories/long-term.md` (Trinity autonomous-git-sync
  protocol section)
- Plan file: `~/.claude/plans/okay-so-that-s-what-curried-lerdorf.md`
- Trinity source (all citations above use these paths):
  - `trinity/src/backend/services/git_service.py:22-476`
  - `trinity/src/backend/services/github_service.py:67` (`API_BASE`)
  - `trinity/src/backend/services/agent_service/crud.py:225,406-428,610`
  - `trinity/src/backend/db/schema.py:399-416`
  - `trinity/src/backend/db/migrations.py` (where the S7 migration
    would land)
  - `trinity/docker/base-image/agent_server/routers/git.py:17-668`
  - `trinity/docker/base-image/startup.sh:15-22`
  - `trinity/src/frontend/src/components/GitConflictModal.vue`
  - `trinity/src/frontend/src/composables/useGitSync.js`
- Abilities skill to update alongside:
  `abilities/plugins/trinity/skills/sync/SKILL.md`
- Tier 1 pure-git repros (cross-platform, no Docker required):
  - `/tmp/trinity-repro/p5_silent_clobber.sh`
  - `/tmp/trinity-repro/p5_fix_verified.sh`
  - `/tmp/trinity-repro/p2_parallel_history.sh`
  - `/tmp/trinity-repro/s3_fix_verified.sh`
- Tier 2 live-API repro: `docker-compose.gitea.yml` (new, dev-only
  overlay) + S0 patch to three Trinity files (all backward-compatible).
