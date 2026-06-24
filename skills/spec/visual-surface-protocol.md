# Beislið visual surface protocol v1

Reusable contract for optional Lavish-backed visual review surfaces. This protocol is intentionally convention-level: Markdown/chat artifacts remain canonical, while HTML surfaces and visual feedback are supplemental unless a future repo config explicitly preserves them.

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

- Repo config shape, effective-mode routing, prompt semantics, and fallback language.
- The canonical Markdown/chat record and any typed workflow-gate decision it accepts.
- The HTML artifact content it writes before invoking a provider.

Lavish owns:

- Local runtime/editor behavior after the configured command is invoked.
- Visual annotation UI, freeform message capture, and any provider-local artifact indexes.
- Provider-specific command options beyond the stable Beislið prompt contract.

Do not make Lavish required for a Beislið workflow. If command resolution, invocation, editor launch, or feedback retrieval fails, record the fallback in chat and continue with canonical Markdown/chat gates.

## Creating Lavish-ready HTML review surfaces

When visual routing is active, create a repo-local HTML artifact before provider invocation:

1. Resolve `artifact_root` from `beislid:visual_surfaces.artifact_root`, defaulting to `.lavish`.
2. Write a deterministic, human-readable HTML file under that root, grouped by workflow when useful (for example `.lavish/spec/<slug>.html`).
3. Include a visible heading, workflow/action, source context, canonical Markdown artifact path or chat-boundary note, rendered payload, and clear feedback instructions.
4. Keep the file self-contained enough for local review. Relative links to repo files are allowed; external network dependencies are not required.
5. Do not embed secrets, hidden chain-of-thought, auth headers, or unrelated transcript content.
6. Treat the HTML as supplemental. Preserve or discard it according to repo policy; absent explicit preservation config, the canonical record is still Markdown/chat.

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

The `BEISLID_VISUAL_PROMPT_V1` prompt text should be visible in the HTML surface and, when the provider supports an agent-message channel, sent there as well. Quote paths, do not shell-interpolate user feedback directly, and do not run deep provider checks unless the workflow explicitly requested them. If the workflow cannot safely determine the provider's exact command form, do not improvise; print the artifact path and continue through Markdown/chat fallback.

If the provider cannot be invoked safely or its response cannot be read, continue through the normal Markdown/chat workflow gate and mention that visual feedback was unavailable.

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
      workflow: spec
      action: approve_or_revise_spec
      decision: approve | revise
      approval_note: optional short approval rationale
      revision_summary: optional short revision request
      must_change: []
      nice_to_have: []
fallback:
  canonical_if_unavailable: Continue in Markdown/chat and ask for the same approve/revise gate there.
```

The prompt may add human-readable instructions before or after the YAML, but the single schema token and field names above are the portable contract.

## Feedback semantics

Visual feedback has two lanes:

- **Freeform annotations/messages**: comments, highlights, sketches, and chat-like notes created in the visual editor. These are useful revision evidence but never count as approval, rejection, or a workflow-gate answer by themselves.
- **Typed workflow-gate input**: an explicit `BEISLID_VISUAL_FEEDBACK_V1` response with `workflow`, `action`, `decision`, and revision/approval fields. Beislið may use this as the workflow gate only when it matches the current workflow/action and the decision is unambiguous.

For the Phase 1 `spec` loop, `decision: approve` means the spec may proceed to the next workflow using the canonical Markdown/chat spec text. `decision: revise` means apply the typed `must_change` items first, then present the revised canonical spec for another gate. Freeform annotations can inform revisions, but the typed gate decides whether the workflow advances.
