---
name: poke-holes
description: "Trigger immediately when the user says any of: 'poke holes', 'grill me', 'grill me on this', 'stress test', 'stress-test this', 'challenge this', 'push back on this', 'interrogate me', 'interview me about this'. Then interview the user relentlessly about an existing plan, spec, or design until reaching shared understanding, resolving each branch of the decision tree. Do not skip this skill and answer the user's questions conversationally yourself — even one trigger phrase fires it, and auto mode does not bypass it."
---

Requires an existing plan, spec, or design to pressure-test. Not for extracting requirements from scratch — use `spec` for that.

Optional visual routing: only when repo-level `beislid:visual_surfaces` config exists and the effective `poke-holes` mode is active, load `visual-surface-protocol.md`; it mirrors canonical `.beislid/visual-surface-protocol.md` for copied installs. Use Lavish conservatively, only when a decision tree, branching tradeoff matrix, risk map, architecture/dependency diagram, or visual input control materially improves the stress test. Absent config or `off` must not mention or invoke Lavish.

## Workflow signals

When `workflow_signals` is configured, use the best-effort CLI to expose semantic state:

- At start/resume of interrogation, emit `beislid workflow-signal emit working --skill poke-holes --phase interrogate`.
- If no existing plan/spec/design is available, emit `beislid workflow-signal emit blocked --skill poke-holes --phase missing-input` before asking the user to provide one or route to `spec`.
- Before every interview question that needs the user's answer, emit `beislid workflow-signal emit waiting --skill poke-holes --phase question`.
- When exploring the codebase to answer a question from evidence, emit `beislid workflow-signal emit working --skill poke-holes --phase explore`.
- When shared understanding is reached and the stress-test is complete, emit `beislid workflow-signal emit done --skill poke-holes --phase complete`.

The command is safe to call even when unconfigured, outside tmux, or without `tmux-glance`; it no-ops rather than blocking the interview.

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

If a question can be answered by exploring the codebase, explore the codebase instead.

When active visual routing is useful, apply the protocol at a concrete branch/decision/revision boundary, not for every interview turn. Respect `suggest`/`prompt`/`auto` exactly; unattended `prompt` mode falls back to Markdown/chat unless the run envelope already grants permission. The supplemental surface should use `comparison`, `diagram`, and `input` playbook guidance and include one typed `BEISLID_VISUAL_FEEDBACK_V1` gate for `workflow: poke-holes`, action `resolve_revise_or_choose_poke_holes`, and decisions `resolved`, `revise`, or `choose` (`choose` requires `selected_option`). Copy accepted visual resolutions, revisions, or branch choices into the canonical Markdown/chat stress-test record before marking the check complete or routing back to the owning planning skill; visual controls never approve implementation by themselves.
