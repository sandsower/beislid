# Agent smoke harness

This harness runs Beislið skill smoke scenarios in isolated fixture repos while temporarily pointing a host's Beislið skill symlinks at the worktree under test.

Current host support: Claude and Codex. Pi support is intentionally left for a later phase because Pi uses package/session configuration rather than a simple skills directory.

## Run a scenario non-interactively

For local PR handoff gates, run hosts AFK with broad fixture permissions. This is budgeted, broad-permission work: do not run it from `ready-for-review` unless the user explicitly answered yes to the workflow prompt. When possible, launch it in a background subagent/task so the main session can continue side-effect-free review or PR-body work, then join before any push/PR creation. The harness creates run dirs, points host skill symlinks at the worktree under test, passes the scenario prompt directly to each host, captures logs, verifies, and restores symlinks. Multiple hosts run in parallel by default:

```bash
python3 tests/agent-smoke/run.py gate ready-for-review --hosts claude,codex --timeout 900
python3 tests/agent-smoke/run.py gate walk-the-diff --hosts claude,codex --timeout 900
python3 tests/agent-smoke/run.py gate walk-the-diff-wrap --hosts claude,codex --timeout 900
```

Use `--changed-only` from the Beislið workflow prompt to skip unless Beislið skill/smoke files changed:

```bash
python3 tests/agent-smoke/run.py gate ready-for-review --hosts claude,codex --timeout 900 --changed-only
```

Broad permissions are host-specific and intended only for isolated fixture repos: Claude uses non-interactive `--dangerously-skip-permissions`; Codex uses `exec --dangerously-bypass-approvals-and-sandbox`. The fixture mocks expected external commands, but this is still a local authenticated model run, not CI-safe.

Pass `--serial` only when debugging host interactions one at a time. Run one host directly:

```bash
python3 tests/agent-smoke/run.py run ready-for-review --host codex --timeout 900
```

## Launch a scenario interactively

Default launch behavior creates a run dir and tries to open a new terminal for the selected host:

```bash
python3 tests/agent-smoke/run.py ready-for-review --host codex
python3 tests/agent-smoke/run.py ready-for-review --host claude
```

The command prints machine-readable lines:

```text
RUN_DIR=/tmp/beislid-agent-smoke-...
LAUNCHER=/tmp/.../launch-codex.sh
VERIFY_CMD=python3 .../run.py verify /tmp/...
STATUS_CMD=python3 .../run.py status /tmp/...
CLEANUP_CMD=python3 .../run.py cleanup /tmp/...
STATUS=launched|prepared
```

If no terminal can be opened, run the printed launcher manually. For agent-orchestrated runs, the parent agent should poll status, verify, then cleanup.

## Lifecycle

```bash
python3 tests/agent-smoke/run.py status <run-dir>
python3 tests/agent-smoke/run.py verify <run-dir>
python3 tests/agent-smoke/run.py cleanup <run-dir>
```

Cleanup is idempotent and should always be called by the parent agent after verify or abort. It restores host skill symlinks from `<run-dir>/host-links-before.json`. The child launcher also restores on normal terminal exit, but parent cleanup is the authoritative finalizer.

Use `--no-launch` to prepare a run without opening a terminal:

```bash
python3 tests/agent-smoke/run.py ready-for-review --host codex --no-launch
```

Use `--foreground` when a new terminal is unavailable and you want to run the child host in the current terminal.

## Safety model

- Only Beislið skills found under this worktree's `skills/*/SKILL.md` are repointed.
- Existing regular files/directories in host skill dirs cause an abort; only missing paths and symlinks are changed.
- Symlink targets are saved and restored.
- The harness is not a network sandbox. Scenarios mock expected external commands, but an agent could still run unrelated network tools.

## Scenario layout

```text
tests/agent-smoke/scenarios/<name>/
  scenario.json
  setup.py
  verify.py
  README.md
  mock-bin/
```

The generic harness owns host linking, terminal launch, status, and cleanup. Scenarios own fixture creation, prompt text, mock tools, and behavior-specific verification.
