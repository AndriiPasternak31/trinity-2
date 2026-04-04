---
name: groom
description: Backlog grooming — audit board coverage, rank unranked issues, review priority ordering, apply changes with approval
automation: gated
allowed-tools: [Bash, Read, Write, Edit]
user-invocable: true
---

# Backlog Grooming

Interactive backlog grooming session for the Trinity Roadmap GitHub Project board.

## Purpose

Ensure all open issues are on the board with correct rank, tier, and priority ordering. Surfaces gaps, suggests re-prioritization, and applies rank updates after user approval.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| GitHub Issues | `abilityai/trinity` | Yes | No | All open issues |
| GitHub Project #6 | `abilityai` org, project 6 | Yes | Yes | Trinity Roadmap board — Rank, Tier, Status fields |
| Project Constants | This skill | Yes | No | Project ID, field IDs |

### Project Constants

```
PROJECT_ID    = PVT_kwDOB8r7us4BRY6-
PROJECT_NUM   = 6
RANK_FIELD_ID = PVTF_lADOB8r7us4BRY6-zg_O1jU
TIER_FIELD_ID = PVTSSF_lADOB8r7us4BRY6-zg_O1kA
```

## Prerequisites

- `gh` CLI authenticated with access to `abilityai/trinity`
- Project board field IDs current (verify if mutations fail)

## Process

### Step 1: Audit Board Coverage

Find open issues that are NOT on the project board.

```bash
gh issue list --repo abilityai/trinity --state open --limit 200 \
  --json number,title,labels,projectItems \
  --jq '.[] | select(.projectItems | length == 0) | "#\(.number)\t\([.labels[].name] | join(", "))\t\(.title)"'
```

If any are found, add them to the board:

```bash
gh project item-add 6 --owner abilityai --url https://github.com/abilityai/trinity/issues/NNN
```

Report findings:
- Count of issues not on board
- List each with issue number, labels, title
- Add missing issues to board before continuing

### Step 2: Detect Unranked Items

Query all Todo items and identify those without a rank.

```bash
gh project item-list 6 --owner abilityai --format json --limit 200 | python3 -c "
import json, sys
data = json.load(sys.stdin)
unranked = []
for item in data['items']:
    c = item.get('content', {})
    num = c.get('number', 0)
    status = item.get('status', '')
    rank = item.get('rank')
    tier = item.get('tier', '')
    title = c.get('title', '')[:65]
    if status == 'Todo' and rank is None:
        unranked.append((num, tier, title))
unranked.sort(key=lambda x: ({'P1a': 0, 'P1b': 1, 'P1c': 2}.get(x[1], 3), x[0]))
print(f'Unranked Todo items: {len(unranked)}')
for num, tier, title in unranked:
    print(f'  #{num} [{tier or \"NO TIER\"}] {title}')
"
```

Also detect items missing a Tier label (should have P1a/P1b/P1c):

```bash
gh project item-list 6 --owner abilityai --format json --limit 200 | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data['items']:
    c = item.get('content', {})
    status = item.get('status', '')
    tier = item.get('tier', '')
    if status == 'Todo' and not tier:
        print(f'  #{c.get(\"number\",\"?\")} [NO TIER] {c.get(\"title\",\"\")[:65]}')
"
```

### Step 3: Review Current Ordering

Display the full ranked Todo backlog for review.

```bash
gh project item-list 6 --owner abilityai --format json --limit 200 | python3 -c "
import json, sys
data = json.load(sys.stdin)
items = [i for i in data['items'] if i.get('status') == 'Todo']
items.sort(key=lambda x: x.get('rank') or 9999)
print(f'Todo backlog ({len(items)} items):\n')
print(f'| Rank | Issue | Tier | Title |')
print(f'|------|-------|------|-------|')
for item in items:
    c = item['content']
    tier = item.get('tier', '')
    rank = item.get('rank', '?')
    print(f'| {rank} | #{c[\"number\"]} | {tier or \"—\"} | {c[\"title\"][:60]} |')
"
```

Present observations:
- Are P1a items ranked highest?
- Are bugs ranked above features within the same tier?
- Are there stale items that should be closed?
- Are there items that seem mis-tiered?

### Step 4: Propose Changes (APPROVAL GATE)

Based on the audit, propose specific changes:

1. **Rank assignments** for unranked items — slot by tier (P1a first, then P1b, then P1c, then untiered)
2. **Tier suggestions** for items missing tier labels
3. **Re-ordering suggestions** for items that seem mis-prioritized
4. **Close candidates** for stale or resolved items

**Ranking strategy:**
- Within each tier, prioritize: bugs > security > features > refactors
- Within same type, order by issue number (older first, unless context says otherwise)
- Use fractional ranks (e.g., 8.1, 8.2) to slot between existing ranked items without displacing them

Present the proposal as a table and **wait for user approval or adjustments** before proceeding.

```
## Proposed Changes

### Rank Assignments (N items)
| Issue | Tier | Proposed Rank | Rationale |
|-------|------|---------------|-----------|

### Tier Suggestions (N items)
| Issue | Current | Proposed | Rationale |
|-------|---------|----------|-----------|

### Re-ordering (N items)
| Issue | Current Rank | Proposed Rank | Rationale |
|-------|-------------|---------------|-----------|

### Close Candidates (N items)
| Issue | Reason |
|-------|--------|

Approve these changes? (You can modify any row before I apply)
```

### Step 5: Apply Approved Changes

After user approves (with any modifications), apply via GraphQL mutations.

**Set rank (number field):**

```bash
gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwDOB8r7us4BRY6-",
    itemId: "ITEM_NODE_ID",
    fieldId: "PVTF_lADOB8r7us4BRY6-zg_O1jU",
    value: {number: RANK_VALUE}
  }) { projectV2Item { id } }
}'
```

**Batch mutations** (up to 10 per GraphQL call):

```bash
gh api graphql -f query='mutation {
  a1: updateProjectV2ItemFieldValue(input: {projectId: "...", itemId: "...", fieldId: "...", value: {number: N}}) { projectV2Item { id } }
  a2: updateProjectV2ItemFieldValue(input: {projectId: "...", itemId: "...", fieldId: "...", value: {number: N}}) { projectV2Item { id } }
}'
```

**To get item node IDs** (needed for mutations), query via GraphQL since `item-list` doesn't expose them:

```bash
gh api graphql -f query='
{
  organization(login: "abilityai") {
    projectV2(number: 6) {
      items(first: 100) {
        nodes {
          id
          content { ... on Issue { number } }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}'
```

Paginate if >100 items (use `after: "CURSOR"` parameter).

After applying, re-query and display the updated backlog to confirm.

## Completion Checklist

- [ ] All open issues are on the project board
- [ ] All Todo items have a rank
- [ ] All Todo items have a tier (P1a/P1b/P1c) or are intentionally untiered
- [ ] P1a items ranked highest, then P1b, then P1c
- [ ] Bugs ranked above features within same tier
- [ ] User approved all changes before they were applied
- [ ] Final backlog displayed for confirmation

## Error Recovery

| Error | Recovery |
|-------|----------|
| GraphQL mutation fails | Verify project/field IDs haven't changed. Re-query field IDs from Step 2 of State Dependencies |
| Item not found | Issue may have been closed or removed from board. Skip and note |
| Rate limit | Wait and retry. GitHub GraphQL rate limit is 5000 points/hour |
| Pagination miss | Always check `pageInfo.hasNextPage` and follow cursors |

## Self-Improvement

After completing this skill's primary task, consider tactical improvements:

- [ ] **Review execution**: Were there friction points, unclear steps, or inefficiencies?
- [ ] **Identify improvements**: Could error handling, step ordering, or instructions be clearer?
- [ ] **Scope check**: Only tactical/execution changes — NOT changes to core purpose or goals
- [ ] **Apply improvement** (if identified):
  - [ ] Edit this SKILL.md with the specific improvement
  - [ ] Keep changes minimal and focused
- [ ] **Version control** (if in a git repository):
  - [ ] Stage: `git add .claude/skills/groom/SKILL.md`
  - [ ] Commit: `git commit -m "refactor(groom): <brief improvement description>"`
