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

Low-confidence or approval-required classifications are a hard gate before slice planning: present the classifier and proposed route, keep progress prose approval-free, wait for explicit approval in the final response, record approved/declined, and do not decompose until approved. Recommend refinement questions when clearer boundaries could avoid unnecessary decomposition.

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

## Step 6: Run `break_spec_approved` lifecycle actions

If inside a git repo with `.beislid/workflow.md`, read only the `beislid:lifecycle_actions` block and execute supported `events.break_spec_approved.actions[]` entries in order after the structure is approved. If no workflow exists, preserve standalone usefulness by offering a local write to `plans/<feature-name>-structure.md` after explicit approval. If a workflow exists but no `break_spec_approved` action is configured, do not write a structure file or run a side effect automatically; workflow config controls lifecycle actions.

Supported P0 action shapes:

```yaml
- name: write-structure-artifact
  type: artifact
  approval: prompt # optional; prompt when omitted, auto creates missing target
  on_failure: prompt # optional; prompt when omitted, or continue | abort
  path: 'plans/{feature}-structure.md' # optional default
- name: run-approved-structure-hook
  type: cli
  command: 'planning-hook {event} {ticket_id} {artifact_path}'
  approval: prompt # required for cli
  classes: [git-remote] # optional action-policy classes
```

Execute `type: artifact` and `type: cli` under `break_spec_approved`; skip other providers as reserved. Multiple actions are allowed and run in order. Before each supported action, evaluate action policy with action id `lifecycle.break_spec_approved.<name>`: artifact actions use class `workspace-write`; CLI actions use configured `classes` or the conservative default `[workspace-write, git-remote]`. A policy denial records `denied` and skips that action; a policy `ask` boundary must be handled before running.

For artifact actions, `approval: prompt` asks write/skip and shows action name, resolved path, and parent directory creation. `approval: auto` writes automatically only when the target does not exist. Existing targets always prompt: overwrite / choose another path / skip. Default path: `plans/{feature}-structure.md`. Supported artifact placeholders are `{feature}`, `{kind}` (`structure`), and `{ticket_id}` when ticket context is known. Derive `{feature}` from the approved structure title, then the approved spec/Work Contract title, then the ticket title, then the branch name; ask for a filename stem if none is available. Slug values by lowercasing, replacing non-alphanumeric runs with `-`, collapsing repeats, stripping edge `-`, and keeping names readable (about 60 chars). If `{ticket_id}` is used without ticket context, ask for another path or skip. Paths must be relative, stay inside the repo root (or cwd for standalone fallback), contain no `..`, and end in `.md`. Create parent directories only as part of an approved or auto write.

Artifact content must be the approved structure as primary content. It may add a clearly labeled `## Artifact Context` section with known source event, ticket, branch, and related lifecycle status. Do not alter approved decisions. Treat written structure artifacts as checkpoint-compatible state seeds for fresh-context handoff into `blueprint`.

For CLI actions, `approval` is required. `approval: prompt` asks run/skip and shows action name, command summary, placeholders used, and action-policy classes. `approval: auto` runs once configured after policy allows it. Supported CLI placeholders are `{ticket_id}`, `{id}` (alias), `{branch}`, `{event}` (`break_spec_approved`), `{feature}`, `{kind}` (`structure`), and `{artifact_path}` (latest written/auto-written artifact path for this event, or empty). Pass placeholder values through argv construction when available or shell-quote them before execution; never splice raw branch/ticket text into a shell and never expose the approved structure body as a command-line placeholder.

`on_failure` may be `prompt`, `continue`, or `abort`; omitted means `prompt`. On failed actions, `prompt` asks retry / skip or explicitly override / abort and stops later actions until resolved, `continue` warns and routes onward without that side effect, and `abort` stops downstream routing.

Record lifecycle results as `written`, `auto-written`, `ran`, `skipped`, `denied`, `reserved`, `not configured`, or `failed`, with paths/action names when available.

## Step 7: Output and route

Print the approved structure summary, lifecycle status/path list, and routing recommendation.

Then route by `scope_classification` when present:
- `multi_slice`: hand off to `blueprint` with the approved structure and any lifecycle artifact path written in this session. Use the selected phase if one was chosen.
- `project`: recommend `spec_refinement` until project boundaries are approved, then return to `break-spec`/slice planning; do not scaffold by default.
- `atomic` or `single_pr`: push back and ask why this needs decomposition unless explicit approval was obtained.
- `unknown`: keep refining; do not hand off as approved.
- If invoked by `kickoff`, return the approved structure, lifecycle status/path, and routing recommendation to `kickoff`.

This structure is the handoff to `blueprint` for the selected phase. Only hand directly to `implement` when the user explicitly says the implementation design is already approved.
