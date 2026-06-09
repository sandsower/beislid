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
- action policy overrides
- per-skill model routing hints/requirements
- visual surfaces such as optional Lavish routing
- workflow signals such as optional tmux-glance tab markers
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
- validation-only config such as action policy, model routing, and visual surfaces
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

Scopes let Beislið run the gates that match the files touched by a branch. For newer workflows that need reusable named gate groups and explicit selected/skipped explanations, prefer `gate_sets`.

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

Changed-file-aware gate sets are selected before legacy scopes/top-level gates when configured:

````markdown
```beislid:gate_sets
sets:
  docs:
    gates:
      - name: docs-lint
        command: 'python3 scripts/check_docs.py'
  skills:
    gates:
      - name: validate-skills
        command: 'python3 scripts/validate_skills.py'
selectors:
  - name: docs-files
    paths: ['docs/**', 'README.md']
    gate_sets: ['docs']
  - name: skill-files
    paths: ['skills/**', '.beislid/**']
    gate_sets: ['skills']
```
````

When multiple selectors match, Beislið unions their gate sets deterministically: first by selector order, then by `gate_sets` order within each selector, then by gate declaration order within each set. De-duplication preserves the first occurrence in that order. Runs should explain why each selector, gate set, and gate declaration was selected or skipped.

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
  "raw_logs": {"path": "artifacts/gates/repo/full-tests/1/summary.txt", "transcript_safe_summary": "2 failed, 41 passed"}
}
```

Generic text output and pytest-style output have built-in parser guidance in the shared output templates; `output.parser: generic-text` or `output.parser: pytest` metadata can guide parser selection where supported.

## Action policy

Action policy is the deterministic risk model repo-aware orchestrators use before risky side effects. It is evaluated by:

```bash
beislid action-policy evaluate --mode unattended-auto --action git.push --sandbox-baseline non-default-branch
```

The evaluator accepts explicit JSON/config input and returns an envelope with `decision` (`allow`, `ask`, or `deny`), `mode`, `action`, `classes`, `matched_rules`, `sandbox_status`, `requires_human`, `log_level`, `reason`, and `remediation`. It intentionally does not attempt full shell parsing; orchestrators pass action identity and declared classes. A small known-action registry and conservative secret-bearing heuristics cover common cases.

Built-in classes are `read`, `workspace-write`, `dependency-install`, `network-read`, `git-local`, `git-remote`, `destructive`, and `secret-bearing`. Actions may have multiple classes; the strictest matching rule wins (`deny` > `ask` > `allow`). Built-in modes are `supervised-auto` and `unattended-auto`.

Default behavior:

- `supervised-auto`: read/network-read actions allow; workspace writes, dependency installs, local/remote git, and secret-bearing actions ask; destructive actions deny.
- `unattended-auto`: read/network-read actions allow; workspace writes, dependency installs, and local git ask; remote git, destructive, and secret-bearing actions deny.
- Unknown or unclassified actions ask by default in both modes.
- `unattended-auto` requires at least a `non-default-branch` sandbox baseline by default. Stricter baselines are `separate-worktree` and `host-sandbox`. Uncommitted changes ask unless project policy overrides that to deny or allow.

Override defaults in workflow config only where the project needs stricter or looser behavior:

````markdown
## Action policy

```beislid:action_policy
modes:
  unattended-auto:
    sandbox:
      minimum: separate-worktree
      on_uncommitted_changes: deny
    rules:
      git-remote: deny
      dependency-install: ask
    actions:
      pr.review.reply: allow
    unknown_action: ask
    unclassified_action: ask
  supervised-auto:
    rules:
      destructive: deny
```
````

Use `actions` for explicit stable action-id overrides when one action should differ from its class default; for example, `pr.review.reply: allow` can auto-allow PR review replies while `git-remote` still asks for push/PR creation.

Doctor validates `beislid:action_policy` as config, not as an external probe. It should report invalid modes, classes, decisions, sandbox baselines, and malformed overrides instead of silently falling back to defaults.

Policy decisions recorded in run summaries or the durable ledger should preserve the evaluator envelope shape: `decision`, `mode`, `action`, `classes`, `matched_rules`, `sandbox_status`, `requires_human`, `log_level`, `reason`, and `remediation`. When an `ask` decision is accepted or declined, summaries should record the human outcome separately from the original evaluator decision. Denied actions should include the remediation hint and stop point.

In v1, repo-aware orchestrators enforce action policy at their owned side-effect boundaries: `kickoff`, `implement`, `ready-for-review`, and `review-response`. `retro` also uses the shared protocol for its optional approved handoff-artifact write. They use the same envelope rather than duplicating policy tables in skill prose.

## Work Contract v1

`work-contract-v1` is the shared planning contract that lets Beislið carry requirements across `spec`, `kickoff`, and `blueprint` without turning planning artifacts into execution state. Current spec artifacts remain human-readable specs; a Work Contract is the hardened section or artifact shape used when downstream automation needs stable fields.

A Work Contract is Markdown with stable fields and headings:

- `Kind`: `work-contract-v1`.
- `Status`: `draft`, `needs-human-decision`, `approved`, or `superseded`.
- `Source`: user prompt, GitHub issue, Linear issue, PR feedback, CI failure, roadmap item, or new-project ask, plus source URL/identifier when known.
- `Problem`: what is broken or missing, and who or what is affected.
- `Desired Outcome`: the observable end state, not the implementation design.
- `Constraints`: explicit technical, product, policy, compatibility, or timeline constraints.
- `Acceptance Outcomes`: user-reviewable outcomes that prove the contract is satisfied.
- `Unknowns / Human Decisions`: unresolved product choices; agents must not invent these to unblock implementation.
- `Risk Classification`: low, medium, high, or critical, with a short reason.
- `scope_classification`: the canonical scope and routing classifier. Keep every field present. Use `kind: unknown` only in `draft` or `needs-human-decision` contracts; approved automation handoffs must classify as `atomic`, `single_pr`, `multi_slice`, or `project`.
- `proof_requirements`: list of `proof-requirement-v1` items that define what evidence makes the contract done.
- `slice_plan`: reserved for break-spec child contract output from #58.
- `children`: reserved for child Work Contracts or child slice references from #58.
- `Ownership Boundary`: what Beislið owns versus Rondo execution/proof/run state and Memento curated memory.

Stable extension slots:

```yaml
scope_classification:
  kind: unknown # atomic | single_pr | multi_slice | project | unknown
  confidence: low # low | medium | high
  rationale: ""
  recommended_route: spec_refinement # spec_refinement | minimal_blueprint | blueprint | break_spec | project_planning
  requires_human_approval: true
  requires_split: false
  split_reason: null

proof_requirements: [] # list of proof-requirement-v1 items; [] means none identified yet

slice_plan: null       # populated for multi_slice/project work in #58
children: []           # child Work Contracts / child slice references in #58
```

Classifier vocabulary:

- `atomic`: tightly bounded, clear, low-branching work. It is not merely a tiny diff; a small risky or ambiguous change may still be `single_pr` or require refinement. Route to `minimal_blueprint` or `blueprint`, and do not over-decompose.
- `single_pr`: one coherent reviewable PR. Route to `blueprint`.
- `multi_slice`: known direction with multiple independently shippable vertical slices. Route to `break_spec` and require a split reason.
- `project`: broad work needing milestones, contracts, or ownership boundaries before child execution. In P0, use `recommended_route: spec_refinement` while boundaries are unresolved; then use `project_planning` as an intermediate route before proceeding to `break_spec` (slice planning). Do not scaffold by default.
- `unknown`: temporary draft state only. Use `confidence: low`, `recommended_route: spec_refinement`, and `requires_human_approval: true`; do not use it in approved automation handoffs.

Always show the classifier before using it to route downstream work. `requires_human_approval: true` means an extra approval boundary beyond normal spec/blueprint approval, and is required when classification triggers decomposition, automation fanout, project planning, contradicts the user's expected route, or has low confidence with high consequence. When approval is required because the scope is broad or low-confidence, recommend the smallest refinement that would reduce ambiguity rather than under-classifying the work to avoid approval.

Example:

````markdown
# Work Contract: Define Work Contract v1

Kind: work-contract-v1
Status: approved

## Source
- Type: GitHub issue
- Identifier: #55
- URL: https://github.com/sandsower/beislid/issues/55

## Problem
Beislið planning flows do not share one durable, human-reviewable artifact describing the work to be done.

## Desired Outcome
`spec`, `kickoff`, and `blueprint` can pass a stable planning contract forward before implementation fanout.

## Constraints
- Keep this in Beislið planning semantics.
- Do not introduce Rondo execution state.
- Follow existing lifecycle artifact safety rules for writes.

## Acceptance Outcomes
- Fields and one example are documented.
- `spec` can finalize the contract for vague/product work.
- `kickoff` can derive the contract from tracker issues.
- `blueprint` can consume an approved contract.

## Unknowns / Human Decisions
- None blocking.

## Risk Classification
Medium — prompt changes span multiple skills and must stay concise.

## Extension Slots

```yaml
scope_classification:
  kind: single_pr
  confidence: high
  rationale: "One coherent Work Contract foundation change across docs and skill guidance."
  recommended_route: blueprint
  requires_human_approval: false
  requires_split: false
  split_reason: null

proof_requirements: []

slice_plan: null
children: []
```

## Ownership Boundary
Beislið owns work-contract semantics; Rondo owns execution/proof/run state; Memento owns curated memory.
````

Work Contract artifacts use existing lifecycle artifact actions. `spec_approved` may write a spec that contains a Work Contract, and `blueprint_approved` may write a design derived from an approved Work Contract. There is no separate `beislid:work_contract` config key in v1. Doctor validates configured Work Contract artifact writes through the existing `beislid:lifecycle_actions` rules: relative `.md` paths, supported placeholders, prompted or safe auto writes, and no overwrite without approval. Beislið owns contract semantics; Rondo owns execution/proof/run state; Memento owns curated memory.

## Proof Requirement v1

`proof-requirement-v1` is the portable done-evidence contract inside a Work Contract. It names the proof a human or agent must produce before the contract, slice, or child task can be treated as ready. Beislið defines the semantics; it does not store proof artifacts, ingest Rondo run state, or replace Memento curated memory.

Proof requirements are YAML objects under `proof_requirements`. Required fields are `kind`, `id`, `type`, `stage`, `status`, `success_criteria`, `failure_policy`, and `expected_artifact`; optional fields include `description` and `applies_to`. Defaults: required `command_gate` proof uses `on_missing: block` and `on_failure: block`; advisory proof may use `warn`. Unknown `type`, `stage`, `status`, or result values are invalid for export.

```yaml
- kind: proof-requirement-v1
  id: pre-pr-gates
  type: command_gate
  stage: pre-pr
  status: required # required | advisory
  description: Run configured pre-PR quality gates.
  success_criteria:
    - All selected gates return pass envelopes.
  failure_policy:
    on_missing: block # required: block | human_interrupt; advisory may warn
    on_failure: block # required: block | human_interrupt; advisory may warn
    retryable: true
  applies_to:
    paths: ['skills/**', '.beislid/**']
    risk: medium
  expected_artifact:
    kind: gate_envelope
    reference: run-ledger gate path or transcript-safe summary
```

Canonical proof `type` values:

- `command_gate`: configured command gate or gate-set result.
- `clean_eval`: independent clean worktree/container evaluation.
- `review`: primary review contract result.
- `fresh_eyes`: final whole-diff review result.
- `screenshot_show_me`: screenshot, video, or Show Me deck evidence.
- `docs_drift_check`: check that docs/config examples still match behavior.
- `migration_dry_run`: migration or data-change dry run evidence.
- `human_approval`: explicit human decision or risk acceptance.
- `artifact_exists`: required local artifact path exists and is readable.
- `ci_check`: provider CI check or required status result.

`stage` names when the proof is expected, using the gate stages where possible (`preflight`, `per-edit`, `pre-commit`, `pre-pr`, `post-pr`, `continuous`, or `human-interrupt`). `status: required` proofs block readiness when missing or failing according to `failure_policy`; `status: advisory` proofs are reported but do not block unless a caller upgrades them by policy.

Proof result status vocabulary is `satisfied`, `missing`, `failed`, `blocked`, `human_interrupt_required`, `advisory_warn`, and `not_applicable`. Orchestrators use `failure_policy.on_missing` and `failure_policy.on_failure` to turn `missing` or `failed` proof into a result: required proof may resolve only to `blocked` or `human_interrupt_required`; `advisory_warn` is only for advisory proof.

`success_criteria` should be observable and reviewable. `expected_artifact` records a reference shape, not embedded proof content: command log path, gate envelope, CI URL/check name, Show Me deck path, screenshot path, migration dry-run log, review report, or human approval note.

Existing gate metadata maps naturally to `command_gate` proof requirements: `name` becomes `id`, `stage` carries over, `changed_file_selector` / gate-set selector data becomes `applies_to.paths` plus `applies_to.exclude` when present, `output` guides the expected artifact parser, and `failure` maps into `failure_policy`. Exported command gates default to `on_missing: block` and `on_failure: block`; `failure.retryable`, `max_fix_iterations`, `stop_if_patterns`, and `hint` are copied when present. Setup/pre commands such as codegen, dependency install, or build prerequisites are not quality proof; they are prerequisites for running proofs, and their failure blocks dependent proof collection rather than satisfying done criteria.

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

Default `plans/` paths are intentionally discoverable by downstream skills. Custom paths are passed through same-session handoff context; broader later-session rediscovery is future work. Planning artifacts are also checkpoint-compatible state seeds: a fresh context may use an approved spec/design artifact as its primary input when it captures enough context for the next skill.

P0 also supports boundary checkpoint artifact events as a thin workflow-configured slice of the future durable run ledger. These events are useful when a workflow wants operational resume metadata around a boundary, not just the approved planning deliverable. Current executable events are `kickoff_context_ready` and `implementation_plan_created`; reserved events `review_feedback_loaded` and `ready_for_review_pre_submit` may be documented in config but are not executed by P0 skills yet.

````markdown
## Lifecycle actions

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
        approval: auto
        path: 'checkpoints/{event}-{ticket_id}.md'
```
````

Checkpoint event artifact paths follow the same safety rules as planning artifacts and additionally support `{event}`. Omitted paths use `checkpoints/{event}-{ticket_id}.md` when ticket context is known, otherwise `checkpoints/{event}-{feature}.md`. Generated checkpoint artifacts are written to `checkpoints/` by default, while `.beislid/checkpoints/latest.json` stores the lightweight pointer index; both `checkpoints/` and `.beislid/checkpoints/` are local by default and ignored by Beislið's own repo. After a checkpoint event artifact is written, the executing skill updates `.beislid/checkpoints/latest.json` so a fresh context can say “continue this ticket” or “continue from checkpoint” without pasting a path. Planning artifacts do not need to update this pointer to be valid checkpoint inputs; downstream skills already discover default `plans/` paths and same-session handoffs carry custom paths.

Example pointer shape:

```json
{
  "version": 1,
  "latest": {
    "kickoff_context_ready": {
      "event": "kickoff_context_ready",
      "path": "checkpoints/kickoff_context_ready-41.md",
      "ticket": {"id": "41", "title": "Add explicit checkpoint artifact actions for orchestrator skills"},
      "branch": "victor/41-checkpoint-artifacts",
      "source_skill": "kickoff",
      "written_at": "2026-05-21T22:30:00Z"
    },
    "implementation_plan_created": {
      "event": "implementation_plan_created",
      "path": "checkpoints/implementation_plan_created-41.md",
      "ticket": {"id": "41", "title": "Add explicit checkpoint artifact actions for orchestrator skills"},
      "branch": "victor/41-checkpoint-artifacts",
      "source_skill": "implement",
      "written_at": "2026-05-21T22:45:00Z"
    }
  }
}
```

The pointer is replaceable convenience state only: no run ID, no event history, no gate logs, and no resume state machine. The `latest` pointer schema keeps one entry per event key; skills should verify the entry's branch and ticket metadata before rediscovering context. If metadata is missing or does not match the current context, ask the user to confirm or provide a checkpoint path.

## Durable run ledger

Beislið also provides a portable run-ledger utility for durable Rondo-style execution evidence. Unlike checkpoint artifacts, the ledger is not workflow-configured and does not write repo-local Markdown by default. It stores operational run state under external Beislið state:

```text
${BEISLID_STATE_DIR:-~/.local/state/beislid}/runs/<flow>/<repo_hash>/<run_id>/
```

Run IDs are stable, timestamped identifiers such as `20260521T224501Z-a7f3c9`; `flow` is an orchestrator name such as `kickoff`, `implement`, or `ready-for-review`. Each run directory contains `run.json` (`kind: run-ledger-v1`), append-only `events.jsonl`, a human-readable `transcript.md`, plus `artifacts/`, `logs/`, `checkpoints/`, and optional `final-report.md` paths. Gate attempts use predictable paths under `artifacts/gates/<scope>/<gate-name>/<attempt>/envelope.json`. Checkpoints are `run-ledger-checkpoint-v1` JSON files and should include `resume_hint` values when they mark a safe continuation boundary. The utility redacts secret-looking fields before writing ledger events or transcript summaries; skills must still avoid sending hidden reasoning, raw secrets, auth headers, or unnecessary raw logs into the ledger.

Use the CLI directly when an orchestrator or harness needs explicit state:

```bash
beislid run-ledger init --skill kickoff --flow kickoff --ticket-id 15 --ticket-title 'Add durable run ledger'
beislid run-ledger event --run-id <run_id> --flow kickoff --type ticket_snapshot --json-file /tmp/ticket.json
beislid run-ledger checkpoint --run-id <run_id> --flow kickoff --name kickoff_context_ready --json-file /tmp/context.json --resume-hint 'continue with implementation planning'
beislid run-ledger gate --run-id <run_id> --flow kickoff --scope repo --name validate-skills --envelope-file /tmp/gate.json
beislid run-ledger interrupt --run-id <run_id> --flow kickoff --reason human_interrupt --resume-hint 'resume at next approval boundary'
beislid run-ledger finalize --run-id <run_id> --flow kickoff --status completed --report-file /tmp/final-report.md
beislid run-ledger resume --flow kickoff --ticket-id 15 --branch victor/15-run-ledger
```

The ledger may link to workflow-configured checkpoint artifacts, but it does not replace them. `.beislid/checkpoints/latest.json` remains a lightweight repo-local rediscovery pointer; the ledger is the durable run history with run IDs, event history, gate log indexes, interruptions, approved risks, and final reports.

## Model routing

`model_routing` lets a repo describe which host model candidates should run each Beislið skill. It is a host hint plus enforcement contract, not a guarantee that every host can switch the currently running model. Hosts should report whether routing was honored, unsupported, fallen back, or blocked.

````markdown
## Model routing

```beislid:model_routing
defaults:
  models: [sonnet]
  mode: prefer
overrides:
  - skills: [spec, blueprint, poke-holes]
    models: [opus, openai:gpt-5.5]
    mode: require
  - skills: [implement, ready-for-review, review-response]
    model: sonnet
```
````

`model` is shorthand for a one-item `models` list. `models` is ordered: the host picks the first supported candidate unless its adapter has a more specific local mapping policy. Portable aliases are `opus`, `sonnet`, `haiku`, `default`, and `host-default`; namespaced provider strings are allowed as escape hatches. `mode: prefer` continues with a disclosed fallback if none can be honored. `mode: require` stops before invoking that skill unless at least one candidate can be honored. Ordered overrides are first-match by skill name, then defaults. Subagents inherit the parent skill's resolved model by default when supported.

Conditional `when:` routing is reserved for future work and is not active in v1; do not rely on a `when:` field to narrow a route.

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

## Visual surfaces

`visual_surfaces` lets a repo opt into optional local visual surfaces while keeping Markdown/chat artifacts canonical. Beislið owns workflow routing, config validation, prompt semantics, and fallback guidance; the provider owns the local runtime. In v1 the supported provider is Lavish via `lavish-axi`.

````markdown
## Visual surfaces

```beislid:visual_surfaces
provider: lavish-axi
mode: prompt
command: 'npx -y lavish-axi'
artifact_root: .lavish
workflows:
  spec: prompt
  blueprint: suggest
  show-me: auto
```
````

Modes are `off`, `suggest`, `prompt`, and `auto`. `suggest` mentions that a visual surface may help; `prompt` asks before invoking one; `auto` permits configured workflows to use the visual surface without another prompt when their own action policy permits it. Per-workflow overrides inherit the global mode when absent.

`command` and `artifact_root` are optional. The default command follows Lavish plugin state and otherwise falls back to `npx -y lavish-axi`; the default artifact root is `.lavish`. Doctor validates the config shape and reports missing or disabled Lavish plugin state as graceful fallback guidance. Proactive routing requires repo config: user-level plugin enablement alone is not enough.

Use `beislid plugin enable lavish` to enable local plugin state and `beislid plugin status lavish` for the light status check. `beislid plugin status lavish --check` may invoke the configured command and can touch npm/network/cache, so doctor does not run that deep check automatically.

## Workflow signals

`workflow_signals` lets Beislið skills emit local, transcript-safe workflow-state signals. Beislið owns the semantic signal; configured sinks decide how to present it locally. In v1 the supported sink is `tmux-glance`, which annotates the current tmux window/tab when the external `tmux-glance` CLI is available.

````markdown
## Workflow signals

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
skills:
  ready-for-review: auto
  poke-holes: auto
```
````

Valid signal states are `working`, `waiting`, `verify`, `review`, `blocked`, `done`, `idle`, and `clear`. Emission is best-effort: if workflow signals are absent/off, the process is outside tmux, `tmux-glance` is missing, or a sink fails, the Beislið workflow continues silently.

Skills should emit signals only where they have semantic knowledge. For example, `ready-for-review` can emit `verify` while gates run, `review` during review/fresh-eyes, `waiting` at approval boundaries, and `blocked` on hard failures. `poke-holes` can emit `waiting` before each interview question and `working` while interrogating or exploring code.

Manual check/emission:

```bash
beislid workflow-signal status --skill ready-for-review
beislid workflow-signal emit waiting --skill ready-for-review --phase approval
```

Future sink types are reserved. They should consume the same normalized signal with constrained, transcript-safe metadata and must not become tracker/PR side effects.

## Repo-aware orchestrators

These skills read `workflow.md`:

- `kickoff`: ticket source, branch pattern, kickoff-start lifecycle actions, custom explore skill, ticket update path, scopes, triggered checks, and model-routing disclosure for downstream skills.
- `ready-for-review`: PR target, quality gates, scopes, review flow, final `fresh-eyes` policy, PR description formatting, triggered checks, and model-routing disclosure.
- `review-response`: PR review source/update path, ticket update path, feedback handling, and model-routing disclosure.
- `spec` / `blueprint`: planning artifact lifecycle actions for their own approval events plus model-routing status from the host.
- `doctor`: all configured capabilities.
- `retro`: current workflow config plus available run/session evidence, producing recommendations only; accepted config changes route through `setup`.
- `setup`: writes and updates config.

If `workflow.md` is missing, repo-aware execution flows should stop and tell you to run `setup`; `setup` creates it, and `retro` can still recommend setup-oriented next steps.

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

`packaging/homebrew/beislid.rb` is a draft Homebrew formula for packaging validation. It installs the Beislið runtime subset under Homebrew `libexec` and exposes `bin/beislid` on PATH. This is not published Homebrew support yet; full Homebrew install/upgrade policy is tracked separately in the Homebrew packaging work.

The CLI validates its runtime layout before loading installer code. It expects `scripts/install_lib.sh`, `scripts/run_ledger.py`, `scripts/action_policy.py`, `skills/`, and `install.sh` under the resolved Beislið runtime root. The root is normally derived from the real `bin/beislid` path; package wrappers can set `BEISLID_HOME` when the executable and runtime root are separated.

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
