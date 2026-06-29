---
name: spec
description: "Trigger immediately when the user says any of: 'spec it out', 'spec this out', 'before you build', 'before we build', 'before implementation', 'let's discuss before building', 'discuss and spec', 'PRD this', 'shape this', 'product spec', 'lightweight spec'. Also use for brainstorming, vague tickets, product shaping, or writing a lightweight product spec/PRD when the problem, scope, desired behavior, or success criteria are unclear. Do not skip this skill and answer conversationally yourself — if a trigger phrase appears, route here even if the request seems clear or auto mode is active. Do not use for implementation design when requirements are already clear; use blueprint instead."
---

# Spec

Shape an idea, vague ticket, or open product question into a lightweight product spec. This is the product/requirements gate, not the implementation-design gate.

Use this for:
- Open-ended brainstorming
- Vague tickets that are not ready for implementation design
- Product behavior, scope, and acceptance criteria discovery
- Writing a lightweight spec/PRD before `blueprint`

Do not use this for:
- Implementation design when the requirement is already clear — use `blueprint`
- Breaking an approved spec into implementation phases — use `break-spec`
- Writing code or scaffolding

<HARD-GATE>
Do NOT design implementation details, invoke `implement`, write code, or scaffold until the product behavior and scope are approved or the user explicitly routes to `blueprint`.
</HARD-GATE>

You may skip steps if the current conversation or `kickoff` already supplied enough context.

## Step 1: Load context

Collect any supplied context:
- User idea or prompt
- Ticket title/body/comments
- Codebase findings from `kickoff`, if provided
- Existing plans/specs in `plans/`
- Relevant docs or recent commits

If working inside a repo, do light codebase exploration before asking detailed questions. Search for existing patterns, data models, API boundaries, and test coverage that affect the product decision. Record facts, not opinions.

Optional visual routing: only when repo-level `beislid:visual_surfaces` config exists and the effective `spec` mode is active, load the per-skill auxiliary `visual-surface-protocol.md` before the Step 5 approval/revision surface. It mirrors canonical `.beislid/visual-surface-protocol.md` so copied skill installs stay readable. When active, lean toward proposing a supplemental Lavish surface for any non-trivial spec whose requirements, options, flows, data/state models, scope boundaries, acceptance outcomes, or decisions can be communicated visually; do not reserve visual routing for UI changes. Use its `BEISLID_VISUAL_PROMPT_V1` envelope for supplemental Lavish HTML review; keep Markdown/chat spec text canonical, treat freeform visual annotations as advisory, and accept only typed workflow-gate responses that validate/normalize to `approve` or `revise`. Unknown, malformed, or freeform-only visual feedback falls back to manual Markdown/chat review.

## Step 2: Identify unknowns

Write down 5–10 targeted questions about what you do not know. Frame them as questions, not statements. Focus on:
- The problem and who feels it
- Desired behavior
- Success criteria
- Scope boundaries
- Constraints and risks
- Product decisions that block implementation design

## Step 3: Interview the user

Ask questions one at a time. Prefer multiple choice when possible. If a question can be answered by the codebase or supplied ticket context, answer it from evidence instead of asking.

For each unresolved question, present:
- What the codebase/ticket suggests
- Your recommended answer
- What decision remains for the user

## Step 4: Propose product directions

When there are multiple plausible interpretations or solutions, propose 2–3 product directions with trade-offs and your recommendation. Keep this at the product behavior level. Do not choose file-level implementation details here.

If the requirement is already obvious and only minor details were clarified, this can be a short paragraph.

## Step 5: Present the spec for approval

Before writing an artifact, present the proposed spec in concise sections and ask for approval or corrections:
- Problem statement
- Current state
- Desired state
- User stories / acceptance outcomes
- Key decisions
- Out of scope
- Work Contract fields when downstream automation needs a stable handoff

Do not proceed until the user approves the product direction.

Optional Lavish review loop: if Step 1 found active `beislid:visual_surfaces` routing for `spec`, apply `visual-surface-protocol.md` here. Default to proposing the surface for visually-communicable specs; skip only when the spec is trivial, purely linear prose, or the effective mode/fallback rules prohibit routing. Respect the effective mode exactly: `suggest` only mentions the option; `prompt` asks before generating/opening and falls back to Markdown/chat if declined or unattended without permission; `auto` may generate/open only within action-policy boundaries and must announce the HTML path before waiting for feedback. The generated surface is supplemental and should use the protocol's `review_spec` prompt, plan/comparison layout guidance, and approve/revise typed gate controls. Normalize typed feedback with the protocol contract or `beislid visual-feedback normalize` semantics; `manual_review`, unknown action/decision, malformed payload, freeform-only feedback, or parser-unavailable hosts continue through Markdown/chat. Copy accepted visual revisions into the Markdown spec, visibly record accepted visual approvals in the canonical Markdown/chat spec, then ask for or record explicit approval of the canonical Markdown/chat spec; never let a visual control bypass this approval gate.

## Step 6: Finalize the approved spec

Use this template for the approved spec text. Do NOT include exact file paths or code snippets unless the user explicitly wants an implementation-adjacent note; those belong in `blueprint`.

<spec-template>
# [Feature Name]

## Problem Statement
What's broken or missing. Who it affects.

## Current State
How things work today. What patterns exist.

## Desired State
What the world looks like after this is released.

## User Stories
- As a [role], I want [thing] so that [outcome]

## Key Decisions
Decisions already resolved during the interview, with rationale.

## Out of Scope
What this spec explicitly does not cover.
</spec-template>

The approved spec text is the source for any artifact. Do not add implementation details while writing an artifact.

When the next workflow needs stable requirements, finalize a `work-contract-v1` section in or alongside the spec.

Required structure:
- Headings: `Kind`, `Status`, `Source`, `Problem`, `Desired Outcome`, `Constraints`, `Acceptance Outcomes`, `Unknowns / Human Decisions`, `Risk Classification`, `Extension Slots`, and `Ownership Boundary`.
- `Extension Slots` YAML keys: `scope_classification`, `proof_requirements`, `slice_plan`, and `children`.

Population rules:
- `scope_classification` must include `kind`, `confidence`, `rationale`, `recommended_route`, `requires_human_approval`, `requires_split`, and `split_reason`.
- Valid kinds are `atomic`, `single_pr`, `multi_slice`, `project`, and draft-only `unknown`; valid confidence values are `low`, `medium`, and `high`.
- Use `atomic` only for bounded, clear, low-branching work; use `single_pr` for one coherent PR; use `multi_slice` for multiple independently shippable slices; use `project` when milestones/contracts/ownership boundaries are needed before execution.
- `unknown` is allowed only for `draft` or `needs-human-decision` contracts and routes to `spec_refinement` with `requires_human_approval: true`.
- Show the classifier before using it to route downstream work. `requires_human_approval: true` means an extra approval boundary beyond normal spec/blueprint approval.
- Require extra approval when classification triggers decomposition, fanout, project planning, contradicts the user's route, or has low-confidence, high-consequence impact. When true, stop, present the classifier and proposed route, wait for explicit approval, record approved/declined, and do not invoke downstream automation until approved. Prefer refinement questions that reduce approval burden over under-classifying.
- `proof_requirements` uses `proof-requirement-v1`; use `[]` only when no proof has been identified.
- `slice_plan: null` and `children: []` are reserved for #58.
- Broad/project work should not jump directly to scaffolding by default.
- Missing product decisions belong under `Unknowns / Human Decisions`; do not invent them to unblock `blueprint`.
- Work Contracts are Beislið planning semantics, not Rondo execution/proof/run state or Memento curated memory.

Examples: typo-level doc fix with no branching → `atomic`; one coherent skill behavior update → `single_pr`; multiple shippable workflow slices → `multi_slice`; broad new-product or cross-system initiative needing milestones/boundaries → `project`.

## Step 7: Run `spec_approved` artifact and tracker actions

If inside a git repo with `.beislid/workflow.md`, read only the `beislid:lifecycle_actions` block and execute supported `events.spec_approved.actions[]` entries. If no workflow exists, preserve standalone usefulness by offering a local write to `plans/<feature-name>-spec.md` after explicit approval. If a workflow exists but no `spec_approved` action is configured, do not ask for ad-hoc tracker/local destinations; workflow config controls artifacts.

Supported P0 action shapes:

```yaml
- name: write-spec-artifact
  type: artifact
  approval: prompt # optional; prompt when omitted, auto creates missing target
  on_failure: prompt # optional; prompt when omitted, or continue | abort
  path: 'plans/{feature}-spec.md' # optional default
```

```yaml
- name: post-spec-body-to-tracker
  type: tracker
  approval: prompt # optional; posts approved spec body through ticket_update.issue_tool / issue_command
  on_failure: prompt # optional; prompt when omitted, or continue | abort
```

Execute `type: artifact` actions first to write the approved spec. Execute `type: tracker` actions after that to post the approved spec body into the tracker ticket body through the configured `ticket_update` issue channel; tracker actions must evaluate `ticket.update` policy before posting. Skip other providers as reserved. Multiple actions are allowed and run in order. `approval: prompt` asks write/skip and shows action name, resolved path or tracker target, and parent directory creation when applicable. `approval: auto` writes automatically only when the target does not exist. Existing targets always prompt: overwrite / choose another path / skip. Skip and reserved actions do not block routing. `on_failure` may be `prompt`, `continue`, or `abort`; omitted means `prompt`. On failed actions, `prompt` asks retry / skip or explicitly override / abort, `continue` warns and routes onward without that side effect, and `abort` stops downstream routing.

Default path: `plans/{feature}-spec.md`. Supported placeholders are `{feature}`, `{kind}` (`spec`), and `{ticket_id}` when ticket context is known. Derive `{feature}` from the approved spec title, then ticket title, then branch name; ask for a filename stem if none is available. Slug values by lowercasing, replacing non-alphanumeric runs with `-`, collapsing repeats, stripping edge `-`, and keeping names readable (about 60 chars). If `{ticket_id}` is used without ticket context, ask for another path or skip. Paths must be relative, stay inside the repo root (or cwd for standalone fallback), contain no `..`, and end in `.md`. Create parent directories only as part of an approved or auto write.

Artifact content must be the approved spec as primary content. Tracker actions must use the approved spec body, including the canonical `## Validation/Test Plan` section, as the tracker update body; they may add a clearly labeled `## Artifact Context` section with known source event, ticket, branch, and related artifact status when writing files. Do not alter approved decisions. Treat written spec artifacts and tracker posts as checkpoint-compatible state seeds for fresh-context handoff into `break-spec` or `blueprint`.

Record action results as `written`, `auto-written`, `skipped`, `not configured`, or `failed`, with paths or tracker targets when available.

## Step 8: Output and route

Print the approved spec summary, artifact status/path list, and routing recommendation.

Then route by `scope_classification` when present:
- `atomic` or `single_pr`: hand off to `blueprint` with the approved spec/Work Contract and any artifact path written in this session.
- `multi_slice`: hand off to `break-spec` with the approved spec/Work Contract and any artifact path written in this session.
- `project`: recommend `spec_refinement` until project boundaries are approved, then hand off to `break-spec`/slice planning; do not scaffold by default.
- `unknown`: keep refining; do not hand off to automation as approved.
- If invoked by `kickoff`, return the approved spec or Work Contract, artifact status/path, and routing recommendation to `kickoff`.
