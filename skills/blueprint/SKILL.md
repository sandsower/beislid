---
name: blueprint
description: "Trigger immediately when the user says any of: 'design this', 'plan the implementation', 'plan this out', 'how should we build', 'implementation plan', 'before I write code', 'design the feature', 'figure out how to build'. Also use for implementation design once desired behavior is known: before creating features, building components, adding functionality, or modifying behavior. Do not skip this skill and start coding directly — if a trigger phrase appears, route here even if auto mode is active. Do not use for open-ended product brainstorming or vague requirements; use spec first. No code until design is approved."
---

# Blueprint

## Project guidance preflight

If `.beislid/workflow.md` has `beislid:skill_guidance`, load `all` and `blueprint` guidance before proceeding; stop on missing/empty `must-read`; report loaded/missing.

No code until the implementation design is approved. `blueprint` turns a clear ticket/spec/phase into an implementation approach. It does not decide what product should exist; `spec` does that.

Use this when:
- Desired behavior is known
- You need to choose an implementation approach
- You need to identify files/modules/data flow/tests
- A `spec`, approved Work Contract, or `break-spec` phase is ready for implementation design

Do not use this when:
- The problem, user/workflow, or success criteria are unclear — route to `spec`
- `scope_classification.kind` is `multi_slice`, `project`, or `unknown` without an approved selected phase/slice — route to `break-spec` or `spec` refinement as appropriate

<HARD-GATE>
Do NOT write any implementation code, scaffold, or take implementation actions until you have presented an implementation design and the user has approved it. This is non-negotiable.
</HARD-GATE>

## Process

1. **Load context** — if the handoff includes an explicit Work Contract, spec/PRD, or phase artifact path, read it as your primary input. Otherwise, if a handoff artifact exists in `plans/` (Work Contract, spec, PRD, phase structure), read it as your primary input. Otherwise, check relevant files, docs, recent commits.
2. **Requirements check** — if product behavior or acceptance criteria are unclear, stop and route to `spec` with the missing questions. When a Work Contract is present, proceed only when `Status` is `approved`; route `draft` or `needs-human-decision` back to `spec`. Treat unknowns as blocking when they affect implementation approach or acceptance criteria. Verify `scope_classification` has the seven #56 keys (`kind`, `confidence`, `rationale`, `recommended_route`, `requires_human_approval`, `requires_split`, `split_reason`), `proof_requirements` is a list (possibly empty), and reserved slots still match defaults (`slice_plan: null`, `children: []`) unless later tickets explicitly populated them. Broad/project work should not jump directly to scaffolding by default. Do not patch over vague requirements with implementation guesses.
3. **Scope check** — use `scope_classification` when present. `atomic` and `single_pr` may proceed. `multi_slice` must route to `break-spec` unless a selected phase/slice is already provided. `project` must route to spec refinement/project boundary approval first in P0, then slice planning; do not scaffold by default. `unknown` or low-confidence high-consequence classifications route back to `spec` for refinement.
4. **Ask implementation questions one at a time** — prefer multiple choice. Focus on architecture, data flow, boundaries, edge cases, and tests.
5. **Propose 2–3 implementation approaches** — include trade-offs and your recommendation. Lead with the recommended option and say why.
6. **Present the design** — scale to complexity. A few sentences for simple changes, detailed sections for complex ones. Get approval section by section. Offer: "Want to stress-test this design before we finalize?" (invokes `poke-holes`).
7. **Run `blueprint_approved` artifact actions** — after the design is approved, execute configured artifact lifecycle actions for the approved design. Do not auto-write design files outside this lifecycle behavior in configured repos.
8. **Transition** — normally invoke `implement` to create the implementation plan and include any artifact status/path. If invoked by `kickoff`, return the approved design plus artifact status/path to `kickoff` instead; kickoff must record discoveries and update the ticket first.

## Scaling to Complexity

- **Small change** (config, rename, simple fix): 1–2 questions, 1 paragraph design, lifecycle artifact only when configured or explicitly useful in standalone mode.
- **Medium feature** (new component, API endpoint): architecture + data flow + testing approach.
- **Large feature** (new subsystem, multi-file): route to `break-spec` before implementation design.

## In Existing Codebases

- Explore current structure before proposing changes. Follow existing patterns.
- If existing code has problems that affect the work, include targeted improvements in the design.
- Don't propose unrelated refactoring.

## Principles

- **Implementation design, not product shaping** — route vague product questions to `spec`.
- **One question at a time** — don't overwhelm.
- **YAGNI ruthlessly** — remove unnecessary features from designs.
- **Explore alternatives** — always propose 2–3 approaches before settling.
- **Incremental validation** — present design, get approval before moving on.

## Artifact lifecycle actions

If inside a git repo with `.beislid/workflow.md`, read only the `beislid:lifecycle_actions` block and execute supported `events.blueprint_approved.actions[]` entries after the user approves the implementation design. If no workflow exists, preserve standalone usefulness by offering a local design artifact for larger/spec-originated work after explicit approval. If a workflow exists but no `blueprint_approved` artifact action is configured, do not write a design file automatically; workflow config controls artifacts.

Supported P0 action shape:

```yaml
- name: write-design-artifact
  type: artifact
  approval: prompt # optional; prompt when omitted, auto creates missing target
  path: 'plans/{feature}-design.md' # optional default
```

Execute only `type: artifact` under `blueprint_approved`; skip other providers as reserved. Multiple artifact actions are allowed and run in order. `approval: prompt` asks write/skip and shows action name, resolved path, and parent directory creation. `approval: auto` writes automatically only when the target does not exist. Existing targets always prompt: overwrite / choose another path / skip. Skip, failed writes, and reserved actions do not block the transition to `implement` or back to `kickoff`.

Default path: `plans/{feature}-design.md`. Supported placeholders are `{feature}`, `{kind}` (`design`), and `{ticket_id}` when ticket context is known. Derive `{feature}` from the approved design title, then spec artifact title, then ticket title, then branch name; ask for a filename stem if none is available. Slug values by lowercasing, replacing non-alphanumeric runs with `-`, collapsing repeats, stripping edge `-`, and keeping names readable (about 60 chars). If `{ticket_id}` is used without ticket context, ask for another path or skip. Paths must be relative, stay inside the repo root (or cwd for standalone fallback), contain no `..`, and end in `.md`. Create parent directories only as part of an approved or auto write.

Artifact content must be the approved design as primary content. It may add a clearly labeled `## Artifact Context` section with known source event, ticket, branch, spec artifact path, and related artifact status. Do not add unapproved design decisions. Treat written design artifacts as checkpoint-compatible state seeds for fresh-context handoff into `implement`.

Record artifact results as `written`, `auto-written`, `skipped`, `not configured`, or `failed`, with paths when available. Pass written artifact paths in handoff context so `implement` can read custom paths in the same session.

## Terminal State

The only normal next step after design approval and artifact handling is `implement`. Do not invoke unrelated implementation skills. If `kickoff` invoked this skill, return control to kickoff with the approved design and artifact status/path.
