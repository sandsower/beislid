---
name: break-spec
description: "Break an approved spec/PRD into phased vertical slices. Use when the user says 'break this spec down', 'phase this', 'create a plan from this', 'decompose this feature', or when spec/kickoff finds work too large for one coherent PR."
---

# Break Spec

Takes an approved spec/PRD and produces a phased implementation structure using vertical slices. Each phase cuts through all layers end-to-end rather than building horizontal slabs.

## Step 1: Load the spec

If the handoff includes an explicit spec artifact path, read it as the primary input. Otherwise, check for artifacts in order: `plans/*-spec.md`, `plans/*-prd.md`, a tracker document/issue linked in conversation, or spec content in the current session. For each `plans/` glob, use the file if exactly one match exists; if multiple matches exist, ask the user which spec file to use before falling back to the next source. If nothing is found, ask the user where it is.

## Step 2: Identify durable decisions

Before phasing, call out the architectural decisions that span the entire feature and must be resolved first: routes, database schema, data models, auth boundaries, service interfaces. These are the skeleton everything else hangs on.

Quiz the user on any unresolved decisions. For each, present your recommendation and why.

## Step 3: Slice into vertical phases

Each phase is a tracer bullet that cuts through every layer (UI, API, data, tests) for a thin but complete slice of functionality. The first phase should be the thinnest possible end-to-end path — the "walking skeleton."

<vertical-slice-rules>
- Each phase delivers something testable and, ideally, demoable
- No phase should be purely "set up infrastructure" — infrastructure comes along with the first feature that needs it
- Later phases widen the path, not deepen a single layer
- If a phase touches only one layer, it's horizontal — rethink it
</vertical-slice-rules>

## Step 4: Classify each phase

For each phase, note:
- **HITL** (human-in-the-loop): needs user decisions, design review, or manual testing
- **AFK** (away-from-keyboard): can run autonomously with clear acceptance criteria

## Step 5: Write the structure

Output to `plans/<feature-name>-structure.md`. Keep it under 2 pages.

```
# [Feature] — Implementation Structure

## Durable Decisions
- [decision]: [resolution and rationale]

## Phase 1: [Walking skeleton] (HITL/AFK)
Cuts through: [layers]
Delivers: [what's testable]
Validates: [what assumption this proves]

## Phase 2: [Next slice] (HITL/AFK)
...

## Phase N: [Final slice] (HITL/AFK)
...
```

This structure is the handoff to `blueprint` for the selected phase. Only hand directly to `implement` when the user explicitly says the implementation design is already approved.
