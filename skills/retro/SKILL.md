---
name: retro
description: Use when the user says "retro", "/retro", "retrospect", "post-run retro", "tune workflow", "refine gates", "improve workflow.md", or asks what should change after a run. Reviews available run/session evidence and the whole `.beislid/workflow.md`, then recommends workflow improvements. Does not edit config; route accepted changes through `setup`.
---

# Retro

Turn a run or session into workflow-improvement recommendations. `retro` answers: what should change about this repo's Beislið workflow after what we just learned?

`retro` is recommendation-only. It never edits `.beislid/workflow.md`; `setup` remains the canonical config writer.

Use this for:
- Post-run/session reflection
- Gate tuning suggestions
- Workflow default refinement
- Reviewing skipped, noisy, missing, slow, or ambiguous workflow steps
- Preparing a handoff for a later `setup` run

Do not use this for:
- Checking whether config is valid or probes pass — use `doctor`
- Direct config editing — use `setup`
- Product shaping — use `spec`
- PR readiness gates — use `ready-for-review`

## Process

### 1. Load available context

Inspect before interviewing. Use what the current host and repo provide, then ask only for missing high-value context.

Collect, when available:
- Current user request and any extra notes they supplied
- Current session context, including recent gate/review/setup friction already visible in chat
- Git repo root, branch, status, and changed-file summary
- `<repo>/.beislid/workflow.md` as the current workflow baseline
- `.beislid/checkpoints/latest.json` and readable referenced checkpoint artifacts
- Beislið run-ledger summaries or final reports for relevant recent runs, if the CLI/state is available
- Session-memory or memento notes, if the host exposes memory/search tools
- Recent local evidence such as gate output summaries, skipped checks, accepted risks, or repeated manual prompts

If a source is missing, unavailable, stale, or too expensive to inspect, say so briefly and continue with the evidence you have. Do not fail solely because durable context is absent.

### 2. Compare evidence to workflow config

Review the whole workflow, not just gates. Look for friction in:
- ticket source and branch detection
- scopes, gate sets, gate metadata, cost, selectors, and parallel-safety hints
- lifecycle/checkpoint artifacts
- action policy prompts or unsafe defaults
- PR review/update paths
- final check and review handoff behavior
- model routing disclosures or repeated model-fit issues
- setup/doctor discoverability gaps
- prose in `workflow.md` that should encode a default, warning, or team preference

Keep observations evidence-based. Do not invent changes from taste alone.

### 3. Recommend conversationally

Lead with the practical recommendation, not a scored report. Keep the tone simple:

- **What I would change via setup** — concrete workflow changes worth making
- **What I would leave alone** — friction noticed but not worth config churn
- **What needs your call** — ambiguous choices, each with a suggested default
- **Not project config** — Beislið distro/skill improvements or team/process notes

For ambiguous UX, do not stall immediately. Suggest the default you would choose and ask only when the decision affects the setup handoff.

### 4. Build the setup handoff

If there are project-config recommendations, include a paste-ready handoff for `setup`:

```text
Setup handoff:
- Goal: <one sentence>
- Sections to change: <workflow.md sections>
- Recommended defaults: <concrete values/prose>
- Open decisions: <questions with recommended defaults>
- Evidence: <brief source list>
```

Make it clear that this is input for `setup`, not a patch and not a source of truth.

If the user wants to apply changes now, route to `setup` with the handoff. Do not edit config yourself.

### 5. Optional handoff artifact

Default is no write. After presenting the recommendations, ask at most once:

> Save this retro as a setup handoff note? [y/N]

Only on explicit yes, write a Markdown handoff artifact. Before writing, read `action-policy-protocol.md` when present and evaluate/handle workspace-write policy if the project provides the Beislið CLI.

Default path:

```text
recommendations/retro-{date}-{branch}.md
```

Path rules:
- path must be repo-relative, stay inside the repo, contain no `..`, and end in `.md`
- create parent directories only as part of the approved write
- if the target exists, ask overwrite / choose another path / skip
- never write or modify `.beislid/workflow.md`

Artifact content:
- title and timestamp when known
- evidence sources used and skipped
- recommendation summary
- setup handoff block
- open decisions
- explicit note: `setup remains the canonical workflow.md writer`

### 6. Output and route

Finish with:
- concise recommendation summary
- setup handoff, if any changes are recommended
- artifact status (`not offered`, `skipped`, `written`, or `failed`)
- next step:
  - `setup` when the user wants to apply project config changes
  - `doctor` when config/probe validity is uncertain
  - `spec`/issue capture when the finding is a Beislið product improvement
  - no action when the current workflow should stay as-is

## Guardrails

- Never directly modify `.beislid/workflow.md`.
- Never present a generated config diff as approved truth; label examples as illustrative.
- Do not replace `doctor`; use it when the question is capability health.
- Do not require memento, run ledger, or checkpoints; they enrich the retro but are optional.
- Prefer one conversational pass with suggested defaults over a long upfront interview.
