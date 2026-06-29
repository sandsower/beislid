---
name: break-spec
description: "Break an approved spec/PRD or Work Contract into phased vertical slices. Use when the user says 'break this spec down', 'phase this', 'create a plan from this', 'decompose this feature', or when spec/kickoff classifies work as multi_slice/project slice planning."
---

# Break Spec

Takes an approved spec/PRD or Work Contract and produces a phased implementation structure using vertical slices. Each phase cuts through all layers end-to-end rather than building horizontal slabs.

## Step 1: Load the spec

If the handoff includes an explicit Work Contract or spec artifact path, read it as the primary input. Otherwise, check for artifacts in order: `plans/*work-contract*.md`, `plans/*-spec.md`, `plans/*-spec-*.md`, `plans/*-prd*.md`, a tracker document/issue linked in conversation, or spec content in the current session. For each `plans/` glob, use the file if exactly one match exists; if multiple matches exist, ask the user which file to use before falling back to the next source. Keep the narrower spec globs ahead of the PRD fallback so generated structure files like `break-spec-structure.md` are not treated as specs. If nothing is found, ask the user where it is.

## Step 2: Check scope classification

If the input includes `scope_classification`, use it before phasing:

- `multi_slice`: proceed with vertical slice decomposition.
- `project`: first identify the missing milestones, contract boundaries, or ownership decisions. If those are not approved, route back to spec refinement instead of inventing slices. Do not scaffold by default.
- `atomic` or `single_pr`: push back before decomposing; ask why this needs a split and proceed only with explicit user approval.
- `unknown`: route back to spec refinement; do not create child slices from an unknown classification.

Low-confidence or approval-required classifications are a hard gate before slice planning: present the classifier and proposed route, wait for explicit approval, record approved/declined, and do not decompose until approved. Recommend refinement questions when clearer boundaries could avoid unnecessary decomposition.

Examples: decompose a `multi_slice` settings revamp into shippable vertical phases; for a `project` such as a new product/repo, first name milestones and ownership boundaries before slice planning; for `atomic`/`single_pr`, decline decomposition unless the user explicitly expands scope.

## Step 3: Identify durable decisions

Before phasing, call out the architectural decisions that span the entire feature and must be resolved first: routes, database schema, data models, auth boundaries, service interfaces. These are the skeleton everything else hangs on.

Quiz the user on any unresolved decisions. For each, present your recommendation and why.

## Step 4: Slice into vertical phases

Each phase is a tracer bullet that cuts through every layer (UI, API, data, tests) for a thin but complete slice of functionality. The first phase should be the thinnest possible end-to-end path — the "walking skeleton."

<vertical-slice-rules>
- Each phase delivers something testable and, ideally, demoable
- No phase should be purely "set up infrastructure" — infrastructure comes along with the first feature that needs it
- Later phases widen the path, not deepen a single layer
- If a phase touches only one layer, it's horizontal — rethink it
</vertical-slice-rules>

## Step 5: Classify each phase

For each phase, note:
- **HITL** (human-in-the-loop): needs user decisions, design review, or manual testing
- **AFK** (away-from-keyboard): can run autonomously with clear acceptance criteria

## Step 6: Run `break_spec_approved` artifact actions

If inside a git repo with `.beislid/workflow.md`, read only the `beislid:lifecycle_actions` block and execute supported `events.break_spec_approved.actions[]` entries after the structure is approved. If no workflow exists, preserve standalone usefulness by offering a local write to `plans/<feature-name>-structure.md` after explicit approval. If a workflow exists but no `break_spec_approved` artifact action is configured, do not write a structure file automatically; workflow config controls artifacts.

Supported P0 action shape:

```yaml
- name: write-structure-artifact
  type: artifact
  approval: prompt # optional; prompt when omitted, auto creates missing target
  path: 'plans/{feature}-structure.md' # optional default
```

Execute only `type: artifact` under `break_spec_approved`; skip other providers as reserved. Multiple artifact actions are allowed and run in order. `approval: prompt` asks write/skip and shows action name, resolved path, and parent directory creation. `approval: auto` writes automatically only when the target does not exist. Existing targets always prompt: overwrite / choose another path / skip. Skip and reserved actions do not block routing. A failed write blocks progression and downstream routing until the write succeeds or the user explicitly overrides; stop later artifact actions for that event when a failure occurs.

Default path: `plans/{feature}-structure.md`. Supported placeholders are `{feature}`, `{kind}` (`structure`), and `{ticket_id}` when ticket context is known. Derive `{feature}` from the approved structure title, then the approved spec/Work Contract title, then the ticket title, then the branch name; ask for a filename stem if none is available. Slug values by lowercasing, replacing non-alphanumeric runs with `-`, collapsing repeats, stripping edge `-`, and keeping names readable (about 60 chars). If `{ticket_id}` is used without ticket context, ask for another path or skip. Paths must be relative, stay inside the repo root (or cwd for standalone fallback), contain no `..`, and end in `.md`. Create parent directories only as part of an approved or auto write.

Artifact content must be the approved structure as primary content. It may add a clearly labeled `## Artifact Context` section with known source event, ticket, branch, and related artifact status. Do not alter approved decisions. Treat written structure artifacts as checkpoint-compatible state seeds for fresh-context handoff into `blueprint`.

Record artifact results as `written`, `auto-written`, `skipped`, `not configured`, or `failed`, with paths when available.

## Step 7: Output and route

Print the approved structure summary, artifact status/path list, and routing recommendation.

Then route by `scope_classification` when present:
- `multi_slice`: hand off to `blueprint` with the approved structure and any artifact path written in this session. Use the selected phase if one was chosen.
- `project`: recommend `spec_refinement` until project boundaries are approved, then return to `break-spec`/slice planning; do not scaffold by default.
- `atomic` or `single_pr`: push back and ask why this needs decomposition unless explicit approval was obtained.
- `unknown`: keep refining; do not hand off as approved.
- If invoked by `kickoff`, return the approved structure, artifact status/path, and routing recommendation to `kickoff`.

This structure is the handoff to `blueprint` for the selected phase. Only hand directly to `implement` when the user explicitly says the implementation design is already approved.
