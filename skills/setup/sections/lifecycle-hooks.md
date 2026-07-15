# setup section lifecycle-hooks v1

In verbose mode, emit `✓ setup/section-lifecycle-hooks v1 loaded` immediately after reading this file.

## Lifecycle hooks

Configure custom phase-boundary hooks? (skip / yes)

Use hooks when a repo needs checks or integrations before/after `spec`, `blueprint`, `implement`, `verify`, `review`, `fresh-eyes`, `ready-for-review`, or `review-response`.
For each selected phase, ask whether the hook runs `before`, `after`, or both, then collect ordered actions and optional trigger rules.
Trigger rules may use `paths`, `exclude`, `scopes`, and `branch_pattern`.
Hooks use the same approval posture as lifecycle actions: `auto` runs without a prompt unless action policy or runtime safety requires one; `prompt` asks first.

If a `lifecycle_hooks` block already exists, merge new phases/actions into the existing block and preserve all existing events and hooks.
Never create duplicate `beislid:lifecycle_hooks` blocks.

```beislid:lifecycle_hooks
phases:
  implement:
    before:
      actions:
        - name: repo-health-check
          type: cli
          command: 'python3 scripts/check_workflow_signals_consistency.py'
          approval: auto
          when:
            paths: ['skills/**', '.beislid/**']
```
