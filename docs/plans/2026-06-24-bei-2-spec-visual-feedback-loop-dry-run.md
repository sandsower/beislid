# BEI-2 spec visual feedback loop dry-run transcript

This dry-run documents the expected `spec` behavior for Lavish visual-surface routing modes. In all cases, the Markdown/chat spec remains canonical and downstream routing waits for an explicit spec approval record.

## 1. Absent repo config

- Given: `.beislid/workflow.md` has no `beislid:visual_surfaces` block.
- Agent: presents the draft spec in chat/Markdown and asks for approve/revise feedback.
- Agent must not say Lavish is active, generate `.lavish/spec/*.html`, invoke a provider, or wait for visual feedback.

## 2. `suggest`

```yaml
provider: lavish-axi
mode: suggest
workflows:
  spec: suggest
```

- Agent: presents the draft spec and says a visual surface may help compare current vs desired behavior and decisions.
- Agent does not generate/open Lavish unless the user or host explicitly routes there.
- Approval still happens through the Markdown/chat spec gate.

## 3. `prompt`

```yaml
provider: lavish-axi
mode: prompt
workflows:
  spec: prompt
```

- Interactive run: agent asks before generating/opening the HTML review surface.
- Declined provider path: agent records that visual review was declined and continues with the normal Markdown/chat approve/revise gate.
- Unattended run without an envelope granting permission: agent does not ask a human; it falls back to Markdown/chat and records that prompt-mode visual routing was skipped.

## 4. `auto`

```yaml
provider: lavish-axi
mode: auto
artifact_root: .lavish
workflows:
  spec: auto
```

- Agent writes a supplemental artifact such as `.lavish/spec/<feature>.html` only inside action-policy boundaries.
- Agent announces the HTML path and visible prompt contract before polling or expecting feedback.
- If a typed visual response returns `decision: approve`, the agent records the canonical Markdown/chat spec approval before routing to `blueprint` or `break-spec`.

## 5. Unavailable provider

- Given: config is active, but command resolution/invocation/polling fails.
- Agent: reports the artifact path when one was created, says visual feedback is unavailable, and continues with the Markdown/chat approve/revise gate.
- Agent does not make Lavish required and does not treat missing visual feedback as approval.

## Prompt envelope check

The HTML surface should contain one copyable prompt envelope with enough source context for approval/revision feedback. Example shape:

```yaml
schema: BEISLID_VISUAL_PROMPT_V1
workflow: spec
action: review_spec
artifact:
  html_path: .lavish/spec/example.html
  title: Example spec review
source_context:
  canonical_record: markdown_chat
  source_paths: []
  ticket_id: BEI-2
payload:
  format: markdown
  summary: Review this draft product spec for approval or revision.
  body: |-
    Problem: ...
    Current state: ...
    Desired state: ...
    Acceptance outcomes: ...
feedback_contract:
  freeform:
    purpose: annotations_messages_only
    instruction: Freeform comments are advisory context, not workflow approval.
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

## Markdown-primary approval check

- Freeform visual annotations can inform edits but never count as approval.
- Typed `revise` feedback must be copied/resolved into the Markdown/chat spec before another gate.
- Typed `approve` feedback can satisfy the visual review decision only when it matches `workflow: spec` and `action: approve_or_revise_spec`; the agent still records the final approved spec in Markdown/chat before proceeding.
