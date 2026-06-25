# BEI-6 planning visual surfaces dry-run

This dry-run documents the expected Phase 4 behavior for `blueprint` and `poke-holes` Lavish routing. Markdown/chat design, stress-test, and approval records remain canonical in every scenario.

## Scenario 1: absent repo config

- Given: `.beislid/workflow.md` has no `beislid:visual_surfaces` block.
- When: `blueprint` presents an implementation design with two options.
- Then: the skill does not mention Lavish, does not write `.lavish/blueprint/*.html`, does not invoke a provider, and continues through the normal Markdown/chat approval gate.

## Scenario 2: blueprint suggest mode

```yaml
provider: lavish-axi
mode: suggest
workflows:
  blueprint: suggest
```

- Given: the design contains an architecture/data-flow sketch and a tradeoff table where visual comparison would materially help.
- Then: `blueprint` may say a supplemental visual surface could help compare the options.
- But: it does not generate/open Lavish unless the user/host explicitly routes there.
- Canonical result: the final design approval is still recorded in Markdown/chat before `implement` runs.

## Scenario 3: blueprint auto mode with typed choice

```yaml
provider: lavish-axi
mode: auto
artifact_root: .lavish
workflows:
  blueprint: auto
```

Expected surface content:
- title, ticket/spec context, and canonical design summary;
- 2-3 implementation options with recommendation and tradeoffs;
- architecture/data-flow diagram only when it clarifies the design;
- explicit note that visual choice is not implementation approval;
- one `BEISLID_VISUAL_PROMPT_V1` envelope with `workflow: blueprint` and review/choice instructions.

Representative typed feedback:

```yaml
schema: BEISLID_VISUAL_FEEDBACK_V1
workflow: blueprint
action: approve_revise_or_choose_blueprint
decision: choose
selected_option: Option B - protocol and skill documentation update
approval_note: Keeps runtime behavior unchanged while expanding planning gates.
```

Expected normalized outcome:
- accepted `decision: choose` only because `selected_option` is present;
- copy the selected option into the canonical Markdown/chat design;
- continue to explicit blueprint approval before implementation.

## Scenario 4: poke-holes prompt mode in unattended run

```yaml
provider: lavish-axi
mode: prompt
workflows:
  poke-holes: prompt
```

- Given: no run envelope grants visual-surface invocation.
- When: `poke-holes` finds a branching decision tree.
- Then: it does not ask a human in the unattended run; it records that prompt-mode visual routing was skipped and continues in Markdown/chat.

## Scenario 5: poke-holes auto mode with resolved stress test

```yaml
provider: lavish-axi
mode: auto
artifact_root: .lavish
workflows:
  poke-holes: auto
```

Expected surface content:
- source plan/spec/design path or chat-boundary summary;
- assumptions, blocking questions, open branches, recommended answers;
- risk/tradeoff matrix and dependency diagram only when useful;
- one typed feedback control for `workflow: poke-holes`.

Representative typed feedback:

```yaml
schema: BEISLID_VISUAL_FEEDBACK_V1
workflow: poke-holes
action: resolve_revise_or_choose_poke_holes
decision: resolved
approval_note: All blocking branches have recommended answers and no plan changes are required.
```

Expected normalized outcome:
- accepted `decision: resolved`;
- copy the resolution and any remaining non-blockers into the canonical Markdown/chat stress-test record;
- do not treat the stress-test resolution as implementation approval.

## Context and privacy checks

Generated planning surfaces should include enough context for a reviewer to understand the decision: ticket id/title, canonical artifact paths when available, source excerpts or summaries, options/tradeoffs, and explicit gates. They should not include unrelated transcript content, hidden reasoning, auth headers, secrets, or provider-local state.
