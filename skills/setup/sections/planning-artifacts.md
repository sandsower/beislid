# setup section planning-artifacts v1

In verbose mode, emit `✓ setup/section-planning-artifacts v1 loaded` immediately after reading this file.

## Planning artifacts

Configure approved structure/spec/design files as `type: artifact` actions inside the canonical `lifecycle_actions` block.
This is a preset over lifecycle actions, not a separate fenced key.
Planning approval events may also carry `type: cli` side-effect actions, but this preset only writes local Markdown artifacts.
Also mention that checkpoint artifacts use the same `lifecycle_actions` block but are configured separately for different workflow events such as `kickoff_context_ready` and `implementation_plan_created`.

Ask:

```text
Configure user-approved planning artifacts? (structure / spec / blueprint / any combination / skip)
```

Use `structure` for `break_spec_approved`.

For each selected event, ask whether to use the default path or customize it.
Defaults are `plans/{feature}-structure.md` for `break_spec_approved`, `plans/{feature}-spec.md` for `spec_approved`, and `plans/{feature}-design.md` for `blueprint_approved`.
Custom paths must be relative `.md` file templates, must not contain `..`, and may only use `{feature}`, `{kind}`, and `{ticket_id}`.
Tell the user these templates stay rediscoverable later because downstream skills resolve them from the workflow config and latest pointer context.
Then ask:

```text
Ask each time, or auto-create when missing? (prompt / auto)
```

Default to `prompt`.
Explain that `auto` creates a missing artifact without another prompt after approval, but never overwrites an existing file; existing targets still ask overwrite / choose another path / skip.
Optionally collect `on_failure` (`prompt` / `continue` / `abort`, default `prompt`) when the team wants artifact/tracker failures to be best-effort or hard-aborting instead of using the normal prompt.
If `spec` is selected, also ask whether the approved spec body should be posted back to the tracker body through the existing `ticket_update` issue channel; when yes, add a `type: tracker` action under `spec_approved`.

If a `lifecycle_actions` block already exists, merge these events/actions into that block; never create a duplicate `beislid:lifecycle_actions` block.
Preserve existing events/actions.
If an artifact action already exists under `break_spec_approved`, `spec_approved`, or `blueprint_approved`, offer keep / replace / add another, default keep.
Show the diff before writing.

```beislid:lifecycle_actions
events:
  break_spec_approved:
    actions:
      - name: write-structure-artifact
        type: artifact
        approval: prompt
        path: 'plans/{feature}-structure.md'
  spec_approved:
    actions:
      - name: write-spec-artifact
        type: artifact
        approval: prompt
        path: 'plans/{feature}-spec.md'
      - name: post-spec-body-to-tracker
        type: tracker
        approval: prompt
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        path: 'plans/{feature}-design.md'
```
