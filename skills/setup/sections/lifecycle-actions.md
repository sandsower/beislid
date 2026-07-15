# setup section lifecycle-actions v1

In verbose mode, emit `✓ setup/section-lifecycle-actions v1 loaded` immediately after reading this file.

## Lifecycle actions

Configure the canonical `lifecycle_actions` block.
Explain that lifecycle actions are side effects at workflow events, not quality gates.
P0 setup supports ordered CLI actions for `kickoff_start`, artifact actions for `break_spec_approved`, `spec_approved`, and `blueprint_approved` through the Planning artifacts preset, spec tracker-post actions through the same planning preset, optional planning-event CLI side effects for those same approval events, and checkpoint artifact actions through the Checkpoint artifacts preset.

Ask:

```text
Configure lifecycle CLI actions? (kickoff_start / planning approvals / both / skip)
```

For `kickoff_start`, collect one or more ordered actions.
For each action ask: action name, command, approval (`auto` / `prompt`), and optional failure policy (`prompt` / `continue` / `abort`, default `prompt`).
Commands may use `{ticket_id}`, `{id}`, `{branch}`, and `{event}` placeholders; explain that orchestrators argv-pass or shell-quote placeholder values before execution.
Explain that `auto` runs once configured and `prompt` asks before running.
Explain failure policies: `prompt` keeps the current retry / skip-remaining-this-session / abort choice on command failure, `continue` warns and proceeds best-effort, and `abort` stops the workflow.
If the command includes raw user-authored body/title placeholders, redirect the user to `ticket_update` or a future file-based lifecycle action instead.

For planning approvals, ask which event(s): `break_spec_approved`, `spec_approved`, `blueprint_approved`.
For each CLI action ask: action name, command, approval (`auto` / `prompt`), optional failure policy (`prompt` / `continue` / `abort`, default `prompt`), and optional action-policy classes (`workspace-write`, `network-read`, `git-remote`, etc.; blank means the runtime uses `[workspace-write, git-remote]`).
Commands may use `{ticket_id}`, `{id}`, `{branch}`, `{event}`, `{feature}`, `{kind}`, and `{artifact_path}`.
Explain that `{artifact_path}` is the latest artifact written earlier in the same event, or empty when none exists.
If the command needs the approved structure/spec/design body, redirect the user to artifact actions plus `{artifact_path}` or a future file-based provider; never configure raw body/title shell placeholders.

If a `lifecycle_actions` block already exists, merge CLI actions into the existing block and preserve all existing events/actions, including planning and checkpoint artifact actions.
Never create duplicate `beislid:lifecycle_actions` blocks.

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: assign-ticket
        type: cli
        command: 'gh issue edit {id} --add-assignee @me'
        approval: auto
        on_failure: prompt
  spec_approved:
    actions:
      - name: write-spec-artifact
        type: artifact
        approval: prompt
        path: 'plans/{feature}-spec.md'
      - name: run-approved-spec-hook
        type: cli
        command: 'planning-hook {event} {ticket_id} {artifact_path}'
        approval: prompt
        classes: [git-remote]
        on_failure: prompt
```
