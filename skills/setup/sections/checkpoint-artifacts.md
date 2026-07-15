# setup section checkpoint-artifacts v1

In verbose mode, emit `✓ setup/section-checkpoint-artifacts v1 loaded` immediately after reading this file.

## Checkpoint artifacts

When the user asks for clear-context, Rondo-style, or checkpoint workflow support, configure checkpoint artifact actions inside the canonical `lifecycle_actions` block.
Explain that this is a lightweight workflow option, not the durable run ledger: skills write human-readable Markdown checkpoints and update `.beislid/checkpoints/latest.json` for rediscovery, and planning artifacts can also be rediscovered later through the same latest-pointer convention when configured, but none of this creates run IDs, event history, gate logs, or automatic resume state.

P0 executable checkpoint events are `kickoff_context_ready` and `implementation_plan_created`.
Reserved events `review_feedback_loaded` and `ready_for_review_pre_submit` may be kept as workflow intent but no P0 skill executes them yet.
For each selected executable event, ask whether to use the default path or customize it.
Defaults are `checkpoints/{event}-{ticket_id}.md` when ticket context is known, otherwise `checkpoints/{event}-{feature}.md`.
Custom paths must be relative `.md` file templates, must not contain `..`, and may only use `{event}`, `{feature}`, `{kind}`, and `{ticket_id}`.
Then ask:

```text
Ask each time, or auto-create when missing? (prompt / auto)
```

Default to `prompt`.
Explain that `auto` creates a missing checkpoint without another prompt, but never overwrites an existing file; existing targets still ask overwrite / choose another path / skip.
Optionally collect `on_failure` (`prompt` / `continue` / `abort`, default `prompt`) when the team wants checkpoint write failures to be best-effort or hard-aborting instead of using the normal prompt.
If a `lifecycle_actions` block already exists, merge checkpoint events into that block and preserve existing events/actions.
Never create duplicate `beislid:lifecycle_actions` blocks.

```beislid:lifecycle_actions
events:
  kickoff_context_ready:
    actions:
      - name: write-kickoff-context-checkpoint
        type: artifact
        approval: prompt
        path: 'checkpoints/{event}-{ticket_id}.md'
  implementation_plan_created:
    actions:
      - name: write-implementation-plan-checkpoint
        type: artifact
        approval: prompt
        path: 'checkpoints/{event}-{ticket_id}.md'
```
