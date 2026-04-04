# Artifact Dependency Graph

A framework for how agents reason about the relationships between project artifacts — code, documentation, tests, scenarios, requirements — and how to behave when they change or conflict.

## The Problem

Agentic projects contain many artifacts with overlapping context: code, docs, tests, requirements, feature flows, user scenarios. When one changes, others may need updating. Today, agents rely on ad-hoc rules ("update docs after code changes") without a structured understanding of *why* or *which direction*.

This leads to:
- Stale documentation no one knows to update
- Conflicting artifacts with no clear resolution
- Agents asking "should I update X or Y?" instead of knowing

## Two Dimensions

Every relationship between two artifacts has two independent properties:

### Dimension 1: Direction (Source → Target)

**Source**: The authoritative artifact. When source and target disagree, the source is correct.
**Target**: The derived artifact. When source and target disagree, the target is stale and must be updated.

Direction answers: **"When these two things conflict, which one is wrong?"**

### Dimension 2: Mode (Prescriptive vs Descriptive)

**Prescriptive**: The artifact defines intent — what *should* be true. Reality conforms to it.
**Descriptive**: The artifact reflects reality — what *currently is* true. It conforms to reality.

Mode answers: **"Does this artifact drive implementation or follow it?"**

### The Four Quadrants

|  | Prescriptive (defines intent) | Descriptive (reflects reality) |
|---|---|---|
| **Source** (authoritative) | Requirements, new user scenarios, TDD tests, acceptance criteria | Running code, production behavior |
| **Target** (derived) | Planned designs pending validation | Feature flows, user docs, architecture docs |

### Lifecycle Transitions

Artifacts move between quadrants. A user scenario starts as **prescriptive source** ("this is how it should work — go build it") and after implementation becomes **descriptive target** ("this documents how it works — update when code changes").

The transition point is typically: implementation complete and validated.

## The Graph

Declare relationships between artifacts explicitly:

```yaml
artifacts:
  requirements.md:
    mode: prescriptive
    direction: source
    description: "Single source of truth for what features exist"
    
  src/backend/:
    mode: descriptive
    direction: source  # for docs; target for requirements
    sources: [requirements.md]
    description: "Implementation — conforms to requirements, drives docs"
    
  docs/user-scenarios/:
    mode: prescriptive  # when new; flips to descriptive after implementation
    direction: source   # drives implementation of new features
    targets: [src/]
    lifecycle:
      after_implementation:
        mode: descriptive
        direction: target
        sources: [src/]
    description: "User task walkthroughs — prescriptive for new, descriptive for existing"
    
  docs/user-docs/:
    mode: descriptive
    direction: target
    sources: [src/backend/, src/frontend/, src/cli/]
    description: "User-facing documentation — always reflects current code"
    
  docs/memory/feature-flows/:
    mode: descriptive
    direction: target
    sources: [src/backend/, src/frontend/]
    description: "Implementation flow documentation — reflects current code paths"
    
  docs/memory/architecture.md:
    mode: descriptive
    direction: target
    sources: [src/, docker/, config/]
    description: "System design overview — reflects current architecture"
```

## Agent Behavior Derived from the Graph

Given the graph, an agent can automatically determine:

| Event | Agent Reasoning |
|-------|----------------|
| File changed in `src/cli/` | Check what lists `src/cli/` as a source → `user-docs/`, `user-scenarios/cli/` (if descriptive) need review |
| New user scenario written | It's prescriptive, targets `src/` → implementation is needed |
| Mismatch found between doc and code | Check direction → update the target, not the source |
| PR review | Check if any targets of changed source files are stale |
| Conflict between two artifacts | Source wins. Flag if both claim to be source (human decision needed) |

## Skills as Direction Enforcers

Each source→target relationship can have a **skill** responsible for maintaining it. The skill's job is to propagate changes from source to target.

```yaml
sync_skills:
  # Code → Feature Flows
  - skill: /sync-feature-flows
    source: [src/backend/, src/frontend/]
    target: [docs/memory/feature-flows/]
    trigger: after code changes
    
  # Code → User Docs  
  - skill: /generate-user-docs
    source: [src/backend/, src/frontend/, src/cli/]
    target: [docs/user-docs/]
    trigger: after feature changes
    
  # Code → Architecture
  - skill: /update-docs
    source: [src/, docker/, config/]
    target: [docs/memory/architecture.md]
    trigger: after structural changes

  # User Scenarios → Code (prescriptive direction)
  - skill: /implement
    source: [docs/user-scenarios/]
    target: [src/]
    trigger: when new prescriptive scenario is approved
    
  # Requirements → Code
  - skill: /implement
    source: [docs/memory/requirements.md]
    target: [src/]
    trigger: when new requirement is approved

  # Code → User Scenarios (descriptive direction, post-implementation)
  - skill: /user-scenario
    source: [src/cli/, src/frontend/, src/backend/]
    target: [docs/user-scenarios/]
    trigger: after implementation changes existing behavior
```

This creates a closed loop:
1. The **graph** declares what depends on what and in which direction
2. **Skills** enforce each direction — propagating changes from source to target
3. **Reviews** validate that targets are in sync with sources before merging
4. **Lifecycle transitions** flip the direction when artifacts change role (prescriptive → descriptive)

## Generalizing Beyond Trinity

This pattern is not project-specific. Any agent with a workspace containing multiple overlapping artifacts can benefit from:

1. **Declaring the graph** — what artifacts exist and how they relate
2. **Assigning direction** — which is source, which is target
3. **Tagging mode** — prescriptive or descriptive
4. **Binding skills** — which skill maintains each edge
5. **Detecting staleness** — on change, walk the graph to find affected targets

The graph becomes part of the agent's operating context — loaded alongside CLAUDE.md and other configuration — giving the agent structured reasoning about its own workspace rather than relying on ad-hoc instructions.
