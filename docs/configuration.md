# Beislið configuration

Beislið has two layers:

1. **Installed skills** in the agent host.
2. **Repo-local workflow config** in `<repo>/.beislid/workflow.md`.

Basic skills such as `spec`, `blueprint`, `debug`, `verify`, and `review` can work after install. Repo-aware orchestrators such as `kickoff`, `ready-for-review`, and `review-response` use `workflow.md` when they need ticket, PR, quality-gate, scope, or team-specific behavior.

## Setup

Use `setup` to create or update project config interactively.

Typical first run:

```text
setup
```

`setup` can configure:

- issue tracker source
- branch pattern
- default PR base
- PR host
- PR review source and update path
- ticket update path
- lifecycle actions such as assigning/moving a ticket when kickoff starts
- planning artifacts written after approved specs/designs
- quality gates
- scopes
- custom kickoff explore skills and triggered checks such as translation sync or browser compatibility
- guided walkthrough thresholds
- probe cache settings

Setup shows diffs before destructive writes. It should not silently overwrite project config.

### Updating Beislið

Use `setup update` or `/setup update` to update the installed Beislið distribution from an agent host. This is separate from project config setup: it reads the install manifest, confirms the Beislið checkout path, then runs `<beislid-repo>/install.sh --update`.

The updater fast-forwards the Beislið checkout with `git pull --ff-only`, aborts on uncommitted local changes, preserves previous manifest install targets and opt-ins such as security hooks and Pi show-me, then relinks installed skills/hooks. It does not read or write project-owned `.beislid/workflow.md` files.

## Doctor

Use `doctor` to audit workflow config and probe configured capabilities.

```text
doctor
```

Use `doctor --refresh` to force re-probing even when the cache is fresh.

Doctor checks:

- `workflow.md` version stamp
- known sections and fenced keys
- duplicate or unknown config keys
- disabled vs missing capabilities
- whether configured commands/tools are reachable in the current host session
- probe cache freshness

Doctor reports gaps in prose. It is an audit tool, not a fixer.

## workflow.md

Project config lives at:

```text
<repo>/.beislid/workflow.md
```

The first line must be:

```text
<!-- beislid-workflow: v1 -->
```

The file mixes human-readable prose with typed fenced blocks:

````markdown
```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body,comments'
id_pattern: '^[A-Z]{2,4}-\d+$'
```
````

Full format reference: [`.beislid/workflow-md-format.md`](../.beislid/workflow-md-format.md).

## Scopes and quality gates

Scopes let Beislið run the gates that match the files touched by a branch.

Example shape:

````markdown
```beislid:scopes
- name: frontend
  paths:
    - "web/**"
  cwd: web
  gates:
    - name: test
      command: npm test
    - name: lint
      command: npm run lint
- name: backend
  paths:
    - "api/**"
  cwd: api
  gates:
    - name: test
      command: pytest
```
````

Use top-level gates when the project does not need scoped gates. Existing flat gates are still valid and default to `stage: pre-pr`, `kind: sensor`, `execution: computational`, and `mutates: false`. For `ready-for-review` fast-path, mark independent read-only gates with `parallel_safe: true`; unmarked gates stay sequential.

Rich gate metadata can describe where a check belongs in the harness and how agents should interpret failures:

````markdown
```beislid:gates
- name: ruff-check
  stage: per-edit
  kind: sensor
  execution: computational
  command: '.venv/bin/python -m ruff check .'
  timeout_seconds: 30
  cost: cheap
  mutates: false
  changed_file_selector:
    include: ['memento/**/*.py', 'hooks/**/*.py', 'scripts/**/*.py', 'tests/**/*.py']
  output:
    parser: generic-text
    agent_summary: true
  failure:
    retryable: true
    max_fix_iterations: 2
    hint: 'Fix lint errors exactly; avoid broad refactors.'
- name: full-tests
  stage: pre-pr
  kind: sensor
  execution: computational
  command: '.venv/bin/python -m pytest'
  timeout_seconds: 600
  cost: expensive
  mutates: false
  output:
    parser: pytest
  failure:
    retryable: true
    max_fix_iterations: 1
```
````

`ready-for-review` and `review-response` currently execute legacy gates and computational `stage: pre-pr` sensor gates. Other stages (`preflight`, `per-edit`, `pre-commit`, `post-pr`, `continuous`, and `human-interrupt`) plus non-computational/non-sensor pre-pr declarations are valid metadata for Rondo/future orchestrators; current skills report them rather than running them at the wrong lifecycle point. `required_tools` entries are probed as CLI binaries before a gate is treated as runnable.

When orchestrators run gates, they summarize each result as an agent-readable envelope with canonical top-level keys: `gate` (object with `name`, `scope`, `cwd`, and `command` strings), `status` (`pass`, `fail`, `skipped`, or `error`), `duration_ms` (integer), `summary` (string), `failures` (array), `retryable` (boolean), `environment_failure` (boolean), `suggested_next_action` (string), and `raw_logs` (object with optional `path` and `transcript_safe_summary` strings).

```json
{
  "gate": {"name": "full-tests", "scope": "repo", "cwd": ".", "command": ".venv/bin/python -m pytest"},
  "status": "fail",
  "duration_ms": 18432,
  "summary": "2 pytest failures in billing tests",
  "failures": [
    {"type": "assertion", "location": "tests/test_billing.py::test_total", "message": "expected 10, got 12"}
  ],
  "retryable": false,
  "environment_failure": false,
  "suggested_next_action": "fix code and rerun full-tests",
  "raw_logs": {"path": ".beislid/runs/gates/full-tests.log", "transcript_safe_summary": "2 failed, 41 passed"}
}
```

Generic text output and pytest-style output have built-in parser guidance in the shared output templates; `output.parser: generic-text` or `output.parser: pytest` metadata can guide parser selection where supported.

## Lifecycle actions

Lifecycle actions are configured side effects at named Beislið workflow events. They are distinct from quality gates: gates verify branch readiness; lifecycle actions update external systems or create user-approved records.

P0 supports ordered CLI actions for `kickoff_start`, which runs after kickoff successfully fetches ticket context:

````markdown
## Lifecycle actions

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: assign-ticket
        type: cli
        command: 'gh issue edit {id} --add-assignee @me'
        approval: auto
      - name: move-in-progress
        type: cli
        command: 'example-tracker transition {ticket_id} in-progress --branch {branch}'
        approval: auto
```
````

CLI placeholders are `{ticket_id}`, `{id}` (alias), `{branch}`, and `{event}`. Orchestrators must pass placeholder values through argv construction when available or shell-quote them before execution. `approval: auto` runs once configured and prompts only on failure; `approval: prompt` asks before running.

P0 also supports local planning artifacts for approved specs and designs through `type: artifact` actions:

````markdown
## Lifecycle actions

```beislid:lifecycle_actions
events:
  spec_approved:
    actions:
      - name: write-spec-artifact
        type: artifact
        approval: prompt
        path: 'plans/{feature}-spec.md'
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        path: 'plans/{feature}-design.md'
```
````

`spec` runs `spec_approved` after the spec is approved. `blueprint` runs `blueprint_approved` after the implementation design is approved. `approval: prompt` asks before writing; `approval: auto` creates a missing file via auto-write, but never overwrites an existing file. Omitted approval defaults to `prompt`. Omitted paths use `plans/{feature}-spec.md` and `plans/{feature}-design.md`. Supported path placeholders are `{feature}`, `{kind}`, and `{ticket_id}`. Paths must be relative `.md` file templates inside the repo, with no `..` segments. Parent directories are created as part of an approved or auto-write.

Artifact results use the same status vocabulary in skill output and same-session handoff context: `written` for a prompted write, `auto-written` for an automatic missing-file write, `skipped` for user-declined prompts or existing-file conflicts the user declines, `not configured` when no event action exists, and `failed` for unexpected write/path errors.

Default `plans/` paths are intentionally discoverable by downstream skills. Custom paths are passed through same-session handoff context; broader later-session rediscovery is future work.

## Ready-for-review final review

`ready-for-review` runs a primary `review` pass and then a final whole-diff `fresh-eyes` pass. Configure `fresh_eyes` only when you want to replace or explicitly disable that final pass; the primary review still runs.

Use a command replacement:

````markdown
## Ready-for-review

```beislid:fresh_eyes
type: command
command: 'node tools/codex-companion.mjs adversarial-review --wait --scope branch'
```
````

Or disable the final pass by project policy:

````markdown
## Ready-for-review

```beislid:fresh_eyes
enabled: false
reason: 'Final review is enforced by a required external check.'
```
````

Absent config keeps the built-in `fresh-eyes` behavior.

## Kickoff explore skills

Kickoff can use a project skill during Step 2 exploration. Skill probes search repo-local `.beislid/skills/<name>` first, then `$BEISLID_SKILLS_DIRS`, then global host skill directories (`~/.agents/skills`, `~/.claude/skills`, `~/.codex/skills`). Put the block under a recognized Kickoff/Skill-specific overrides section:

````markdown
## Kickoff

```beislid:explore
skill: guide
mode: enhance
```
````

`enhance` runs default codebase exploration and merges skill findings. `replace` runs the skill instead of default exploration; if the skill is unavailable, kickoff asks whether to retry, fall back to default exploration for this session, or abort.

## Repo-aware orchestrators

These skills read `workflow.md`:

- `kickoff`: ticket source, branch pattern, kickoff-start lifecycle actions, custom explore skill, ticket update path, scopes, triggered checks.
- `ready-for-review`: PR target, quality gates, scopes, review flow, final `fresh-eyes` policy, PR description formatting, triggered checks.
- `review-response`: PR review source/update path, ticket update path, feedback handling.
- `spec` / `blueprint`: planning artifact lifecycle actions for their own approval events.
- `doctor`: all configured capabilities.
- `setup`: writes and updates config.

If `workflow.md` is missing, these flows should stop and tell you to run `setup`.

## Probe cache

Probe state lives under:

```text
${BEISLID_STATE_DIR:-~/.local/state/beislid}/probes/<repo-hash>.json
```

The cache records whether configured capabilities worked in the current environment. Doctor owns the audit view. Orchestrators probe lazily when they need a capability.

If behavior looks stale, run:

```text
doctor --refresh
```

## Installation state

The default user installer links skills into supported host directories:

- `~/.agents/skills`
- `~/.claude/skills`
- `~/.codex/skills`

It also links the CLI by default:

```text
${BEISLID_BIN_DIR:-~/.local/bin}/beislid
```

If that bin dir is not on `PATH`, the installer warns. Add it to your shell profile to run `beislid` directly.

It writes machine-local install state to:

```text
${BEISLID_STATE_DIR:-~/.local/state/beislid}/install.json
```

Re-running the installer is safe. Dangling symlinks are repaired. Live symlinks pointing outside this repo are left alone unless you pass `--force`. Regular files and directories are never clobbered. The manifest records `bin_dir` and `cli_path` when the CLI link is installed or already correct.

For the v0.1.x → v0.2 clean-history transition, run `./install.sh --migrate-v0.2` from a fresh v0.2 checkout. The migration reads the previous manifest, removes only old Beislið symlinks pointing into the previous checkout, preserves install targets and opt-ins, then runs a user install from the new checkout. It does not delete the old checkout or clobber regular files.

Project-level install defaults to symlink mode and also supports copy mode:

```bash
beislid install project [path]
beislid install project [path] --copy
beislid install project [path] --copy --write-gitignore
beislid status project [path]
./install.sh --project [path]
./install.sh --project [path] --copy
```

With no path, `beislid install project` targets the git root when run inside a git repo. Outside git, it targets the current directory and warns. An explicit path is used exactly and is allowed even when it sits inside a larger repo. Non-git targets warn but continue.

Project install creates:

- `<project>/.agents/skills`
- `<project>/.claude/skills`
- `<project>/.codex/skills`

It writes `<project>/.beislid/project-install.json` with source path, version/commit, mode, targets, and install counts. In copy mode, each copied skill dir also gets a `.beislid-owner.json` marker with `owner: beislid`, `mode: copy`, the skill name, host, source path, version, and commit. Reruns refresh existing Beislið-owned copied dirs using either the marker or manifest as ownership evidence. Unmarked project files or directories are skipped and are not clobbered, even with `--force`.

Project installs do not edit `.gitignore` by default. They print this suggested block:

```gitignore
# BEGIN Beislið project install
.agents/skills/
.claude/skills/
.codex/skills/
.beislid/project-install.json
# END Beislið project install
```

Pass `--write-gitignore` to create `.gitignore` if needed, insert the block if absent, or replace the existing marked block idempotently. Project install does not create `.beislid/workflow.md`; if that file is missing, it prints a soft note to run the agent `setup` workflow when repo-aware behavior is needed.

## Package-manager compatibility

`packaging/homebrew/beislid.rb` is a draft Homebrew formula for packaging validation. It installs the Beislið runtime subset under Homebrew `libexec` and exposes `bin/beislid` on PATH. This is not published Homebrew support yet; full Homebrew install/upgrade policy is tracked in #67.

The CLI validates its runtime layout before loading installer code. It expects `scripts/install_lib.sh`, `skills/`, and `install.sh` under the resolved Beislið runtime root. The root is normally derived from the real `bin/beislid` path; package wrappers can set `BEISLID_HOME` when the executable and runtime root are separated.

## CLI commands and optional install flags

```bash
beislid install user
beislid install project [path]
beislid install project [path] --copy
beislid status
beislid status project [path]
beislid update
beislid migrate v0.2
beislid help
```

Legacy installer flags remain supported:

```bash
./install.sh --with-security-hooks
./install.sh --with-pi-show-me
./install.sh --update
./install.sh --migrate-v0.2
./install.sh --status
./install.sh --project [path]
./install.sh --project [path] --copy
./install.sh --force
```

- `--with-security-hooks`: enable the Claude Code `credential_guard` hook.
- `--with-pi-show-me`: install the Pi extension for `show-me`.
- `--update`: fast-forward the Beislið checkout and re-run install, preserving previous manifest install targets and opt-ins.
- `--migrate-v0.2`: one-time migration from a pre-v0.2 install after cloning the clean v0.2 repository history.
- `--status`: print installed commit and symlink status.
- `--project [path]`: run a project install through the legacy installer entrypoint.
- `--copy`: copy project-local skills instead of symlinking them.
- `--write-gitignore`: create or replace the managed project `.gitignore` block.
- `--force`: repoint/replace existing symlinks. It also allows replacing symlinks during copy installs, but never clobbers unmarked regular files or directories.
