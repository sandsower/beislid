# setup section workflow-signals v1

In verbose mode, emit `✓ setup/section-workflow-signals v1 loaded` immediately after reading this file.

## Workflow signals

Configure the canonical `beislid:workflow_signals` block under `Workflow signals`.
Explain that this is local workflow-state fan-out, not tracker updates, host lifecycle hooks, or quality gates.
The only v1 executable sink is `tmux-glance`; future sink types are reserved.

Ask:

```text
Configure workflow signals? (auto / off / skip)
```

For `auto`, write a `sinks` list with `type: tmux-glance`.
Ask whether to enable the default semantically instrumented skills (`ready-for-review` and `poke-holes`) or customize per-skill overrides.
Valid modes are `off / auto`.

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
skills:
  ready-for-review: auto
  poke-holes: auto
```

Explain that signal emission is best-effort: outside tmux, without `tmux-glance`, or when a sink fails, Beislið continues silently.
Never create duplicate `beislid:workflow_signals` blocks; update or remove the existing one.
