# setup section scopes-quality-gates v1

In verbose mode, emit `✓ setup/section-scopes-quality-gates v1 loaded` immediately after reading this file.

## Scopes & quality gates

Configure one gate model: changed-file-aware `gate_sets`, scoped `scopes`, or top-level `gates`.
Prefer `gate_sets` when the user wants reusable named checks, selector explanations, staged/rich gates by changed path, or multiple touched areas that union checks deterministically.
Keep `scopes` and top-level `gates` backward-compatible.

For each simple gate ask: gate name, command, optional autofix command, and whether it is independent/read-only enough for `parallel_safe: true`.
Explain that flat gates remain valid and default to `stage: pre-pr`, `kind: sensor`, `execution: computational`, and `mutates: false`.

If the user chooses rich metadata, collect only fields they can answer confidently:

- `stage`: one of `preflight`, `per-edit`, `pre-commit`, `pre-pr`, `post-pr`, `continuous`, `human-interrupt`; default `pre-pr`
- `kind`: default `sensor`
- `execution`: `computational`, `inferential`, or `human`; default `computational`
- `timeout_seconds`, `cost`, `mutates`, `accepts_files`, `required_tools`
- optional exact `evidence_reuse` for deterministic computational sensor gates with `mutates: false`; collect environment variable names and argv-style runtime/dependency probes, and leave it absent by default
- changed-file selector globs under `changed_file_selector.include` / `exclude`
- `output.parser` and `output.agent_summary`
- `failure.retryable`, `failure.max_fix_iterations`, `failure.stop_if_patterns`, and `failure.hint`

For `gate_sets`, collect named sets first (set name, optional cwd, gates), then ordered selectors (selector name, path globs, optional exclude globs, referenced set names).
Explain that multiple matching selectors union gate sets deterministically and orchestrators should report selected/skipped reasons.

For legacy `scopes`, also ask whether the scope needs an optional `setup` command that runs once before any gates in that scope.
Explain that `setup` is for generated code, installs, and other prerequisites, not proof; it runs in the scope cwd and blocks the scope gates if it fails.

Warn that P0 `ready-for-review` and `review-response` run legacy/pre-pr command gates.
Scope-level `setup` runs before those gates and is a prerequisite, not a gate.
Other stages are valid metadata for Rondo/future orchestrators and should not be presented as active blockers in today's PR handoff flows.

Example rich gate:

```beislid:gates
- name: full-tests
  stage: pre-pr
  kind: sensor
  execution: computational
  command: '.venv/bin/python -m pytest'
  timeout_seconds: 600
  cost: expensive
  mutates: false
  evidence_reuse:
    mode: exact
    environment:
      variables: ['CI']
      commands:
        - ['.venv/bin/python', '--version']
        - ['.venv/bin/python', '-m', 'pip', 'freeze', '--all']
  output:
    parser: pytest
  failure:
    retryable: true
    max_fix_iterations: 1
```
