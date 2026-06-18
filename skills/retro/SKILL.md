---
name: retro
description: Use when the user says "retro", "/retro", "retrospect", "post-run retro", "tune workflow", "refine gates", "improve workflow.md", or asks what should change after a run. Reviews evidence, classifies learnings by consumer, and recommends workflow/guidance/product improvements without bloating workflow.md.
---

# Retro

Turn a run or session into durable improvement recommendations. `retro` answers: what should change after what we just learned, and where should that learning live?

`retro` never edits `.beislid/workflow.md`; `setup` remains the canonical config writer. It may edit user-selected host guidance or project docs only after showing an exact diff and receiving explicit approval.

Use this for:
- Post-run/session reflection
- Gate, action-policy, checkpoint, PR, or handoff tuning
- Guidance routing for agents or Beislið skills
- Local-vs-Beislið product-improvement classification
- Preparing a handoff for later `setup`

Do not use this for:
- Capability health/probe audits — use `doctor`
- Direct workflow.md editing — use `setup`
- Product shaping — use `spec`
- PR readiness gates — use `ready-for-review`

## Project guidance preflight

If `.beislid/workflow.md` has `beislid:skill_guidance`, load `all` and `retro` guidance before proceeding. Read `when: always` files in order. Stop on missing, unreadable, or empty `must-read` files; missing `read-if-present` files are non-blocking. Briefly report loaded/missing project guidance.

## Process

### 1. Load available context

Inspect before interviewing. Collect, when available:
- Current user request and notes
- Current session friction visible in chat
- Git repo root, branch, status, and changed-file summary
- `<repo>/.beislid/workflow.md` as the workflow baseline, including `agent_guidance` and `skill_guidance`
- Current resolved host when inferable (Pi, Claude Code, Codex, or unknown)
- Existing host guidance files named by `agent_guidance`
- `.beislid/checkpoints/latest.json` and referenced checkpoint artifacts
- Beislið run-ledger summaries or final reports
- Session-memory/memento notes if exposed
- Recent local evidence such as gate output summaries, skipped checks, accepted risks, or repeated prompts

If a source is missing, unavailable, stale, or too expensive to inspect, say so briefly and continue. Do not fail solely because durable context is absent.

### 2. Classify each learning by consumer

Do not default to `.beislid/workflow.md`. For each recommendation, choose the smallest durable surface that changes the right future behavior:

1. **Executable workflow behavior** — route to `.beislid/workflow.md` through `setup` only. Examples: gates, action policy, lifecycle artifacts, ticket/PR providers, babysit policy, guidance pointers. Workflow stores config/pointers, not bulky guidance content.
2. **Every-run agent guidance** — use configured host-native startup guidance from `beislid:agent_guidance` (for example `AGENTS.md` or `CLAUDE.md`). Guidance must be visible to the host that loads it, not hidden in Beislið docs.
3. **Skill-scoped soft guidance** — use project-owned guidance files referenced by `beislid:skill_guidance` when a Beislið skill should read guidance on demand. `all` applies to consuming skills broadly; a skill key applies to that skill only.
4. **Project reference knowledge** — use visible docs only when there is an explicit consumer, read trigger, expected behavior change, and link/update path. Do not claim archived knowledge improves behavior without a consumer contract.
5. **Beislið product improvement** — classify local-only vs watch vs candidate distro improvement before drafting anything upstream. Default to local-only/watch unless evidence likely generalizes.
6. **No durable destination** — one-off or low-value observations are intentionally not saved.

Host-specific guidance rules:
- Claude Code guidance must follow Claude best practices: concise, durable, high-signal, not tutorial/bloat; use Claude-only features only in Claude-scoped text.
- Pi guidance must use Pi-supported concepts such as `AGENTS.md`/`CLAUDE.md` context files, skills, `/compact`, `/tree`, and `!!` hidden shell output. Do not recommend Claude-only plan mode/hooks/subagents/permission modes unless a Pi extension/package provides them.
- Unknown host: use configured `agent_guidance.default` or ask once before editing.

### 3. Recommend conversationally

Lead with the practical recommendation. Group output as:
- **Workflow config via setup** — executable config/pointer changes only
- **Agent guidance** — resolved host, target path, proposed concise edit, and why the host should load it
- **Skill guidance overlays** — target skill(s), guidance path(s), `read-if-present` or `must-read`, and why the skill needs it
- **Project reference docs** — consumer contract only when useful
- **Product improvement candidates** — local-vs-general classification
- **Leave alone** — friction noticed but not worth durable encoding

For every recommendation include:

```text
Recommended destination:
Why this destination:
Consumer:
When it should be read:
Expected behavior change:
Proposed action:
```

For agent guidance include:

```text
Resolved host:
Resolved guidance path:
File exists:
Current host is expected to load it:
Proposed edit:
```

For reference knowledge include:

```text
Destination:
Intended consumers:
Read trigger:
Expected behavior change:
Link/update needed so consumers can find it:
```

For Beislið product candidates include:

```text
Primitive/workflow affected:
Local evidence:
Why this might generalize:
Why local guidance/config is insufficient:
Suggested change:
Confidence: low / medium / high
Recommended action: local only / watch / draft issue / create issue after approval
```

### 4. Build handoffs and approved edits

For workflow config recommendations, include a paste-ready setup handoff:

```text
Setup handoff:
- Goal: <one sentence>
- Sections to change: <workflow.md sections>
- Recommended defaults: <concrete values/prose>
- Open decisions: <questions with recommended defaults>
- Evidence: <brief source list>
```

Make clear this is input for `setup`, not a patch/source of truth. If the user wants to apply workflow config, route to `setup`; do not edit workflow.md yourself.

For host guidance or project-doc recommendations, let the user choose: edit the resolved target, override target this time, save as draft/handoff only, or do nothing. If they choose an edit:
- read `action-policy-protocol.md` when present and evaluate `file.write` with class `workspace-write` when the Beislið CLI is available
- show the exact diff before writing
- require explicit approval
- keep edits concise; do not turn guidance files into tutorials

For `skill_guidance`, do not leave `must-read` pointing at a missing/empty file. Create/update the guidance doc first with approval, then route the workflow pointer change through `setup`.

### 5. Optional handoff artifact

Default is no write. After recommendations, ask at most once:

> Save this retro as a setup/guidance handoff note? [y/N]

Only on explicit yes, write a Markdown artifact after action-policy handling. Default path: `recommendations/retro-{date}-{branch}.md`. Path must be repo-relative, stay inside repo, contain no `..`, and end in `.md`. Never write or modify `.beislid/workflow.md`.

Artifact content:
- title and timestamp when known
- evidence sources used and skipped
- recommendation summary by destination
- setup handoff block when relevant
- proposed guidance/doc edits or draft paths
- product-improvement classification
- explicit note: `setup remains the canonical workflow.md writer`

### 6. Output and route

Finish with:
- concise recommendation summary
- setup handoff if workflow changes are recommended
- guidance/doc edit status (`not offered`, `skipped`, `written`, or `failed`)
- artifact status (`not offered`, `skipped`, `written`, or `failed`)
- next step: `setup`, `doctor`, approved guidance edit, `spec`/ticket draft, or no action

## Guardrails

- Never directly modify `.beislid/workflow.md`.
- Never mutate Beislið-distributed skill files during normal repo retros.
- Never hide every-run guidance in Beislið docs; use host-native startup guidance.
- Never claim a knowledge/doc move improves behavior without an explicit consumer contract.
- Never create or post upstream Beislið issues without explicit approval; default local-only/watch.
- Do not replace `doctor`; use it when capability health is uncertain.
- Do not require memento, run ledger, or checkpoints; they enrich retro but are optional.
- Prefer one conversational pass with suggested defaults over a long upfront interview.
