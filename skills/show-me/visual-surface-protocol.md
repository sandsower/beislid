# Beislið visual surface protocol v1

Reusable contract for optional Lavish-backed visual review surfaces. Markdown/chat artifacts remain canonical, while HTML surfaces and visual feedback are supplemental. Phase 2 hardens the typed feedback lane with a small Beislið-owned validation/normalization helper; Lavish remains optional and is never durable proof storage.

## Activation

Only load and apply this protocol when all of the following are true:

1. The repository workflow config contains a valid `beislid:visual_surfaces` block.
2. The effective mode for the current workflow is not `off`.
3. The workflow action is one that can benefit from a review/planning surface.

User-level Lavish plugin state alone never activates visual routing. If repo config is absent, invalid, or `off`, continue in normal Markdown/chat mode and do not claim Lavish routing is active.

Mode behavior:

- `suggest`: mention that a visual surface may help, but keep the canonical workflow in chat/Markdown unless the host/user explicitly routes to visual.
- `prompt`: ask before invoking when interactive; in unattended runs, fall back to Markdown/chat unless the run envelope already grants the workflow permission to open visual surfaces.
- `auto`: the workflow may invoke the configured surface without another prompt when its own action policy permits it.

## Ownership boundary

Beislið owns:

- Repo config shape, effective-mode routing, prompt semantics, typed feedback validation, normalization, fallback language, and the canonical Markdown/chat record it accepts.
- The HTML artifact content it writes before invoking a provider.
- The optional parser/helper contract exposed as `beislid visual-feedback normalize` and implemented in `scripts/visual_feedback.py`; hosts may call it, reimplement the same semantics, or fall back to manual Markdown/chat review.

Lavish owns:

- Local runtime/editor behavior after the configured command is invoked.
- Visual annotation UI, freeform message capture, and any provider-local artifact indexes.
- Provider-specific command options beyond the stable Beislið prompt contract.

Do not make Lavish required for a Beislið workflow. Disabled user plugin state, absent repo config, `mode: off`, missing `npx` or another configured binary, failed deep checks, declined prompts, command invocation failures, editor launch failures, feedback retrieval failures, unavailable parser support, and `manual_review` parser results all fall back to canonical Markdown/chat gates.

## Creating Lavish-ready HTML review surfaces

When visual routing is active, create a repo-local HTML artifact before provider invocation:

1. Resolve `artifact_root` from `beislid:visual_surfaces.artifact_root`, defaulting to `.lavish`.
2. Write a deterministic, human-readable HTML file under that root, grouped by workflow when useful (for example `.lavish/spec/<slug>.html`).
3. Include a visible heading, workflow/action, source context, canonical Markdown artifact path or chat-boundary note, rendered payload, and clear feedback instructions.
4. Keep the file self-contained enough for local review. Relative links to repo files are allowed; external network dependencies are not required.
5. Do not embed secrets, hidden chain-of-thought, auth headers, or unrelated transcript content.
6. Treat the HTML as supplemental. Preserve or discard it according to repo policy; absent explicit preservation config, the canonical record is still Markdown/chat.

Artifact retention policy:

- `artifact_retention: local` or an omitted value keeps supplemental HTML under a gitignored `artifact_root` for local inspection only. Any custom root must also be ignored before local retention is allowed. This is the safe default.
- `artifact_retention: discard` removes supplemental HTML when the workflow closes or when the user declines the visual path; canonical Markdown/chat records and `show-me` decks remain untouched.
- `artifact_retention: preserve-repo` is reserved for explicit workflow intent to commit a supplemental artifact. Use it only with a named docs/example path or gitignore exception; never silently commit `.lavish/` output.

## Spec review surface loop

The Phase 1 `spec` integration uses this protocol only at the approval/revision boundary, after the draft product spec is presentable and before downstream routing. Markdown/chat remains the canonical spec record.

Effective mode handling for `spec`:

- absent config or `off`: do not mention or invoke Lavish; continue with the normal Markdown/chat approval gate.
- `suggest`: mention that a supplemental visual review surface may help compare the problem, desired state, decisions, and acceptance outcomes; do not generate or open one unless the user/host explicitly routes there.
- `prompt`: ask before generating/opening in interactive runs; in unattended runs, fall back to Markdown/chat unless the run envelope has already granted permission to open visual surfaces.
- `auto`: generate/open only inside the configured workflow/action-policy boundary, then visibly tell the user the HTML path and prompt contract before waiting for visual feedback.

A `spec` HTML artifact should use Lavish `plan` and `comparison` playbook guidance without making Lavish required:

- Plan-oriented sections: problem statement, current state, desired state, user stories/acceptance outcomes, key decisions, out of scope, and any Work Contract fields.
- Comparison-oriented sections: side-by-side current vs desired behavior, accepted vs deferred decisions, must-change vs nice-to-have feedback lanes, and a clear approve/revise decision card.
- Controls/prompts: include copyable controls or instructions that emit one typed `BEISLID_VISUAL_FEEDBACK_V1` response with `decision: approve` or `decision: revise`; `request_changes` and similar request-change wording normalize to `revise`. Freeform annotations remain advisory.
- Source context: include the ticket id/title when known, canonical Markdown artifact path when one exists, or a chat-boundary note when approval has not yet been written to a file.

After feedback returns, normalize the typed lane before using it. A visual `approve` response can satisfy the review decision only when it validates as an accepted typed gate response for `workflow: spec` and canonical action `approve_or_revise_spec`; the skill must still visibly record that the Markdown spec is approved. A visual `revise` response means copy the accepted revision request into the canonical Markdown/chat spec, apply `must_change` items, and run another gate. A `manual_review` result, freeform-only feedback, unknown action, unknown decision, malformed payload, or parser-unavailable host continues through the normal Markdown/chat approval/revision gate.

## Show Me deck routing

`show-me` is already a visual artifact generator. Lavish routing must inspect or annotate that existing deck, not replace the renderer or make Lavish a prerequisite.

Effective mode handling for `show-me` happens only after the canonical deck has been created or rendered:

- absent config or `off`: do not mention or invoke Lavish; return the portable `index.html`, `show-me.json`, evidence summary, and missing-capture notes as usual.
- `suggest`: mention that the rendered deck can be opened in Lavish for supplemental inspection; do not create `.lavish/` output or invoke the provider unless the user/host explicitly routes there.
- `prompt`: ask before opening in interactive runs; in unattended runs, fall back to the portable deck unless the run envelope or workflow action policy already grants visual-surface invocation.
- `auto`: may invoke the configured provider with the rendered deck path when action policy permits it; announce the canonical deck path, visual-surface path when different, retention policy, and fallback if invocation fails.

A `show-me` Lavish surface should use the rendered deck `index.html` as the stable source whenever possible. If a wrapper is needed to carry the prompt envelope, write it under `.lavish/show-me/<deck-id>.html` or the configured `artifact_root` equivalent, link to the canonical deck files, and include the prompt envelope with `workflow: show-me`, `action: inspect_show_me_deck`, and `source_paths` pointing at the deck's `index.html`, `show-me.json`, and `manifest.json` when present. The canonical deck directory remains the durable artifact; wrapper HTML and provider-local indexes are supplemental.

Show Me uses the same `BEISLID_VISUAL_PROMPT_V1` envelope header but not the spec typed gate. Until a future workflow defines a Show Me typed decision, set `feedback_contract.typed_gate.required_for_decision: false` or omit the typed-gate fields entirely, and state that annotations are advisory inspection notes. Do not emit `workflow: spec`, `action: approve_or_revise_spec`, or any approve/revise decision requirement for `show-me` deck inspection.

Show Me feedback is advisory unless a future workflow defines a typed gate for it. Freeform Lavish annotations can guide deck revisions, but accepted changes must be copied into the canonical deck source or reported in the final `show-me` result before they matter. Unknown, malformed, freeform-only, or unavailable feedback never changes a deck status or verification claim by itself.

Show Me fallback and preservation rules:

- disabled user plugin state, missing command binaries, unavailable `npx`, command failures, editor launch failures, declined prompts, and missing feedback are non-fatal; return the normal deck paths and record the visual fallback.
- do not run `beislid plugin status lavish --check` or any deep provider check unless explicitly requested; normal routing must not require network access.
- keep `.lavish/` and `.beislid/show-me/` ignored by default. Commit a generated deck or supplemental wrapper only when explicit workflow intent opts into publication and the gitignore exception is intentional.
- apply `artifact_retention` to supplemental Lavish wrappers only. Never discard the canonical `show-me` deck because visual routing was declined or unavailable.

## Provider invocation expectations

Resolve the command in this order:

1. `beislid:visual_surfaces.command` when present.
2. Enabled local Lavish plugin state.
3. `npx -y lavish-axi` as the documented fallback command.

Invocation is local and best-effort. For Lavish v1, the stable file-path session identity is the HTML artifact path:

```bash
<configured-command> <html_path>          # open or resume the local review surface
<configured-command> poll <html_path>     # wait for feedback when the workflow is allowed to poll
<configured-command> end <html_path>      # optional cleanup when the review is finished
```

The `BEISLID_VISUAL_PROMPT_V1` prompt text should be visible in the HTML surface and, when the provider supports an agent-message channel, sent there as well. Quote paths, do not shell-interpolate user feedback directly, and do not run deep provider checks unless the workflow explicitly requested them. The light `beislid plugin status lavish` check only resolves the first command binary; `beislid plugin status lavish --check` may invoke `npx -y lavish-axi` or another configured command and may touch npm/network/cache. If the workflow cannot safely determine the provider's exact command form, do not improvise; print the artifact path and continue through Markdown/chat fallback.

If the provider cannot be invoked safely, the user declines a `prompt`-mode path, or the provider response cannot be read, continue through the normal Markdown/chat workflow gate and mention that visual feedback was unavailable.

## Prompt envelope

Every Lavish prompt created by Beislið must include a readable YAML block whose `schema` field is `BEISLID_VISUAL_PROMPT_V1`. Do not repeat the schema token elsewhere in the prompt; keep one portable envelope per provider invocation.

```yaml
schema: BEISLID_VISUAL_PROMPT_V1
workflow: spec                 # Beislið workflow/skill name, e.g. spec
action: review_spec            # workflow-local action being requested
artifact:
  html_path: .lavish/spec/example.html
  title: Example spec review
source_context:
  canonical_record: markdown_chat # markdown_chat | markdown_file | issue | checkpoint
  source_paths: []                # repo-relative canonical artifact/source paths when available
  ticket_id: null                 # optional tracker key, e.g. BEI-3
payload:
  format: markdown                # markdown | html | json | mixed
  summary: Short description of what to review
  body: |-
    Canonical payload or pointer summary. Do not include hidden reasoning.
feedback_contract:
  freeform:
    purpose: annotations_messages_only
    instruction: Freeform comments, highlights, and annotations are advisory context, not workflow approval.
  typed_gate:
    required_for_decision: true
    response_schema: BEISLID_VISUAL_FEEDBACK_V1
    allowed_decisions: [approve, revise]
    fields:
      schema: BEISLID_VISUAL_FEEDBACK_V1
      workflow: spec
      action: approve_or_revise_spec
      decision: approve | revise
      approval_note: optional short approval rationale
      revision_summary: optional short revision request
      must_change: []
      nice_to_have: []
    backward_compatibility:
      omitted_schema: accepted only for legacy Phase 1 flat payloads with workflow/action/decision
      action_aliases:
        review_spec: approve_or_revise_spec
      decision_aliases:
        request_changes: revise
        changes_requested: revise
        request_revision: revise
fallback:
  canonical_if_unavailable: Continue in Markdown/chat and ask for the same approve/revise gate there.
```

The prompt may add human-readable instructions before or after the YAML, but the single prompt schema token and field names above are the portable contract. The YAML block above is the spec approval/revision variant; advisory `show-me` inspection uses `workflow: show-me`, `action: inspect_show_me_deck`, deck source paths, and no required typed gate unless a later protocol version defines one.

## Feedback validation and normalization

Visual feedback has three outcomes:

- `accepted`: one typed workflow-gate input validates for the current workflow/action and normalizes to an allowed decision.
- `manual_review`: no typed gate is present, the payload is malformed, the schema/workflow/action does not match, or the decision is unknown. Manual review is safe fallback, not failure approval.
- `unavailable`: the visual provider or host parser cannot return feedback. Continue in Markdown/chat.

The optional repository helper is dependency-free and does not invoke Lavish:

```bash
beislid visual-feedback normalize --expected-workflow spec --expected-action approve_or_revise_spec feedback.txt
```

It prints a lossless normalized JSON event for the typed contract, including `status`, `reason`, canonical `workflow`, canonical `action`, canonical `decision` when accepted, original action/decision fields, `approval_note`, `revision_summary`, `must_change`, `nice_to_have`, `canonical_update_required`, and a short raw-feedback excerpt. Hosts may call this helper or apply the same rules inline; when parsing or normalizing feedback, preserve those audit fields so the accepted decision or manual-review fallback can be copied into the canonical Markdown/chat record. The helper accepts JSON, fenced JSON/YAML, or the small flat YAML shape shown above; it is not a general YAML parser.

For v1, the canonical action vocabulary is intentionally small:

| Workflow | Canonical typed action | Accepted decisions | Backward-compatible aliases |
| --- | --- | --- | --- |
| `spec` | `approve_or_revise_spec` | `approve`, `revise` | legacy Phase 1 flat payloads may omit `schema` when `workflow`/`action`/`decision` are present; action `review_spec`; decisions `request_changes`, `changes_requested`, `request_revision` → `revise` |

Unknown workflows, actions, decisions, duplicate fields, multiple typed payloads, or mixed valid/malformed payloads must produce `manual_review`. They must never silently approve, auto-route downstream, or bypass action-policy gates.

## Feedback semantics

Visual feedback has two lanes:

- **Freeform annotations/messages**: comments, highlights, sketches, and chat-like notes created in the visual editor. These are useful revision evidence but never count as approval, rejection, or a workflow-gate answer by themselves.
- **Typed workflow-gate input**: an explicit `BEISLID_VISUAL_FEEDBACK_V1` response with `workflow`, `action`, `decision`, and revision/approval fields. Beislið may use this as the workflow gate only when it validates against the current workflow/action and the decision is unambiguous.

For the Phase 1 `spec` loop, `decision: approve` means the spec may proceed to the next workflow using the canonical Markdown/chat spec text after the approval is visibly recorded there. `decision: revise` means apply the typed `must_change` items first, then present the revised canonical spec for another gate. Freeform annotations can inform revisions, but the typed gate decides whether the workflow advances; visual controls never bypass the explicit spec approval record or action-policy gates.

## Canonical record audit requirements

When a workflow consumes visual feedback, the canonical Markdown/chat record must include an auditable note before proceeding:

- visual surface path when known;
- typed feedback status (`accepted`, `manual_review`, or `unavailable`);
- accepted `workflow`, `action`, `decision`, and any `approval_note`, `revision_summary`, `must_change`, or `nice_to_have` fields;
- fallback/manual-review reason for freeform-only, malformed, unknown, mismatched, or parser-unavailable feedback;
- the downstream decision: approved canonical Markdown, revised canonical Markdown, or continued manual Markdown/chat gate.

This record is what downstream Beislið workflows consume. Lavish runtime state and local annotations are supporting context only unless a future repo policy explicitly preserves them.
