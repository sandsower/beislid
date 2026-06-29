# Beislið workflow.md format — v1

Per-project Beislið config lives at `<repo>/.beislid/workflow.md`. The file mixes prose for humans with typed-key fenced YAML blocks that orchestrators parse for capability values.

## Version stamp

The first line of the file MUST be:

```
<!-- beislid-workflow: v1 -->
```

Doctor reads this line. A mismatch hard-fails with prose pointing at upgrading Beislið or downgrading workflow.md by hand. Future versions can offer migration when they encounter older stamps.

## Section grammar

Sections are H2 headings (`##`) with topic-based names. Doctor and orchestrators identify sections by these canonical names (case-insensitive on the first H2 occurrence):

- `Issue tracker`
- `PR target`
- `PR reviews`
- `Scopes`
- `Quality gates`
- `Gate sets`
- `Lifecycle actions`
- `Lifecycle hooks`
- `Pi handoff`
- `Action policy`
- `Translation sync`
- `Browser compat`
- `Domain capture`
- `PR description`
- `Guided walkthrough`
- `Visual surfaces`
- `Workflow signals`
- `Model routing`
- `Probe cache`
- `Skill-specific overrides`
- `Ready-for-review`
- `Review-response`
- `Babysit`
- `Kickoff` (put `beislid:explore` here or under `Skill-specific overrides`)

Section order is irrelevant to parsing. Sections that aren't in this list are ignored with a `💭` inline note from doctor; their fenced blocks are skipped.

## Fenced block grammar

Typed-key fenced blocks are the structured input source for orchestrators. The info string format is:

````
```beislid:<key>
```
````

`<key>` is dot-pathed for nested capabilities (`domain_expert.agent`, `pr_description.formatter_skill`, `translation_sync.trigger_paths`). Block content is YAML. Single-value blocks may be a bare scalar.

Example:

````
```beislid:ticket_source
type: mcp
tool: mcp__plugin_linear_linear__get_issue
id_pattern: '^[A-Z]{2,4}-\d+$'
```

```beislid:branch_pattern
^([A-Z]{2,4}-\d+)
```
````

## Canonical fenced keys

Keys recognized by Beislið orchestrators. Optional fields are noted; the rest are required when the parent key is set.

**Issue tracker:**
- `ticket_source` — fields: `type` (`mcp` / `cli` / `file` / `paste`), `tool` (when `type: mcp`), `command` (when `type: cli`, with `{id}` placeholder), `file_glob` (when `type: file`), `id_pattern` (regex), `link_template` (optional, with `{id}` placeholder)
- `branch_pattern` — single regex string; per-project only, never user-level
- `ticket_update` — shared by kickoff and review-response. Fields: `type` (`mcp` / `cli`); comment channel is used for kickoff plan comments and review-response ticket replies (`comment_tool` when `type: mcp`, `comment_command` when `type: cli`); issue channel is optional for review-response child tickets (`issue_tool` / `issue_command`) and `spec_approved` tracker body posts. CLI comment commands use `{id}` + `{body_file}` placeholders; issue commands use `{title_file}` + `{body_file}`. Orchestrators write temp files and substitute file paths — never interpolate raw user-authored body/title text into shell commands.

**PR target:**
- `pr_base.default` — base branch name (e.g. `main`)
- `pr_host.owner`, `pr_host.repo`, `pr_host.remote` — auto-derived from `origin` if absent; explicit override when fork or non-`origin` remote

**PR reviews:**
- `pr_review_source` — fields: `type` (`cli` / `paste`); for `type: cli`, `summary_command` is required and `threads_command` is optional. Placeholders: `{owner}`, `{repo}`, `{number}`, `{url}`. Missing `threads_command` means review-response can read PR-level comments but may miss inline review threads.
- `pr_review_update` — fields: `type` (`cli` / `manual`); for `type: cli`, `reply_command` is required and `rerequest_command` is optional. Commands receive a temp JSON payload via `{json_file}`. Placeholders: `{owner}`, `{repo}`, `{number}`, `{json_file}`. MCP PR review providers are intentionally deferred.

**Scopes and gates:**
- `scopes` — list of scope objects, each with `name`, `paths` (glob list), `cwd`, `gates` (list of gate objects; see **Gate object shape** below)
- `split_policy` — single string; `exclusive` is the only recognized value
- `gates` (top-level) — single gate list when `scopes` is not configured; same gate object shape as a scope's gates
- `gate_sets` — changed-file-aware gate selection. Fields: `sets` (map of set name → object with `gates`, optional `cwd`, optional `stage`) and `selectors` (ordered list with `name`, `paths`, `gate_sets`, optional `exclude`). See **Gate-set selection shape** below.

**Lifecycle actions:**
- `lifecycle_actions` — event-keyed side effects. P0 executable events are `events.kickoff_start.actions[]`, `events.break_spec_approved.actions[]`, `events.spec_approved.actions[]`, `events.blueprint_approved.actions[]`, `events.kickoff_context_ready.actions[]`, and `events.implementation_plan_created.actions[]`. `kickoff_start` supports `type: cli`; planning approval events (`break_spec_approved`, `spec_approved`, `blueprint_approved`) support `type: artifact` and `type: cli`, and `spec_approved` may also include `type: tracker` actions that post approved spec text into the current ticket body through the configured `ticket_update` issue channel. Checkpoint events support `type: artifact` only. Reserved checkpoint events `review_feedback_loaded` and `ready_for_review_pre_submit` may be validated but are not executed by P0 skills yet. Every action has `name` and `type`. CLI actions use `command`, require `approval` (`auto` / `prompt`), and may declare `classes` using action-policy class names. Tracker actions are approval-gated and action-policy-checked with `ticket.update`. Artifact actions may use optional `approval` (defaults to `prompt`) plus optional `path` file templates and documented placeholders. Any action may set `on_failure` to `prompt`, `continue`, or `abort`; omitted means `prompt`. Actions run in order. For before/after phase hooks, use `lifecycle_hooks`.

**Lifecycle hooks:**
- `lifecycle_hooks` — phase-boundary side effects. Fields: `phases.<phase>.before.actions[]` and `phases.<phase>.after.actions[]`. Supported phases are `spec`, `blueprint`, `implement`, `verify`, `review`, `fresh_eyes`, `ready_for_review`, and `review_response`. Each hook action reuses the lifecycle action shape (`name`, `type`, provider-specific `command` / `tool`, `approval`) and may add optional `when` trigger rules: `paths`, `exclude`, `scopes`, and `branch_pattern`. Hooks run before/after the phase body, obey action policy and approval gates, and do not replace quality gates.

**Pi handoff:**
- `pi_handoff` — Pi-extension-only context handoff policy. Fields: `enabled` (bool, default true when the Beislið Pi extension is active), `events` (`all` or list of lifecycle/checkpoint event names, default `all`), and `exclude` (list of event names to suppress). Repo workflow declares team intent; local Pi extension settings are the final override. Portable skills do not execute this key directly.

**Action policy:**
- `action_policy` — optional evaluator overrides for deterministic action-risk decisions. Fields: `modes.<mode>.rules.<class>` (`allow` / `ask` / `deny`), `modes.<mode>.actions.<action-id>`, `modes.<mode>.unknown_action`, `modes.<mode>.unclassified_action`, and `modes.<mode>.sandbox.minimum` / `on_uncommitted_changes`. Supported modes are `supervised-auto` and `unattended-auto`. Supported classes are `read`, `workspace-write`, `dependency-install`, `network-read`, `git-local`, `git-remote`, `destructive`, and `secret-bearing`. Sandbox baselines are `none`, `non-default-branch`, `separate-worktree`, and `host-sandbox`.

**Visual surfaces:**
- `visual_surfaces` — optional visual-surface routing config. Fields: `provider` (`lavish-axi` in v1), `mode` (`off | suggest | prompt | auto`, default `suggest`), optional `command` (string override for the provider command), optional `artifact_root` (repo-relative path, default `.lavish`), optional `artifact_retention` (`local | discard | preserve-repo`, default `local`), and optional `workflows` map for per-workflow mode overrides. Workflow override keys are Beislið workflow/skill names such as `spec`, `blueprint`, `poke-holes`, `show-me`, `review`, `ready-for-review`, `walk-the-diff`, and `handoff`; override values use the same mode enum. Proactive routing requires repo `visual_surfaces` config; user-level plugin enablement alone is not enough.

**Workflow signals:**
- `workflow_signals` — optional local workflow-state signal fan-out. Fields: `mode` (`off | auto`, default `auto`), `sinks[]` (v1 supports `type: tmux-glance`; future sink types are reserved), and optional `skills` map for per-skill mode overrides using the same enum. Beislið emits normalized states `working | blocked | waiting | verify | review | done | explore`; sinks consume them best-effort and must not block workflow progress. Workflow signals are local presence/status events, not tracker writes or quality gates.

**Model routing:**
- `model_routing` — optional per-skill host model preferences. Fields: `defaults` (optional route object) and ordered `overrides[]` route objects. Route objects use `model` (single candidate shorthand) or `models` (ordered candidate list), optional `mode` (`prefer` / `require`, default `prefer`), and `skills` (required on overrides). `when` is reserved for future conditional routing and is not executable in v1.

**Kickoff overrides:**
- `explore` — fields: `skill` (Beislið skill name), `mode` (`replace` or `enhance`; default `enhance`). Put this block under a `## Kickoff` or `## Skill-specific overrides` section. Used by kickoff Step 2 before implementation design.

**Triggered skills:**
- `translation_sync.skill`, `translation_sync.trigger_paths`
- `browser_compat.skill`, `browser_compat.trigger_paths`
- `pr_description.formatter_skill`, `pr_description.formatter_args` (optional map)

**Ready-for-review approval gates:**
- `ready_for_review` — optional approval gate friction policy. Fields: `approval_gates.pr_title_body` (`prompt` / `auto`, default `prompt`), `approval_gates.gate_failure` (`prompt` / `auto`, default `prompt`), `approval_gates.autofix_commit` (`prompt` / `auto`, default `prompt`), `approval_gates.clean_eval_failure` (`prompt` / `auto`, default `prompt`), `approval_gates.reduced_review_coverage` (`prompt` / `auto`, default `prompt`). `auto` records the decision in transcripts/ledgers and continues without an interactive prompt while still blocking on real-risk stops: critical review findings, merge conflicts, missing credentials, destructive actions, and policy denials.

**Ready-for-review clean evaluation:**
- `clean_eval` — optional clean worktree/container policy for pre-PR evaluation. Fields: `mode` (`off` / `require`, default `off`); optional `surface` (`auto` / `worktree` / `container`, default `auto`); optional `artifact_root` (repo-relative path, default `.beislid/clean-eval`). `mode: require` means ready-for-review must stage the candidate patch in a clean surface and run configured pre-PR gates there before handing off; `mode: off` keeps the normal working-tree gate path. Failures are classified as patch-regression versus environment/harness failure, and logs/artifacts live under the configured root or run-ledger artifacts.
- `ship_time_artifacts` — optional ship-time planning-artifact narration policy for `ready-for-review`. Fields: `mode` (`remind` / `include` / `skip` / `clean`, default `remind`). It only changes how ready-for-review summarizes generated planning artifacts during handoff; it does not auto-commit or auto-delete files in P0.

**Ready-for-review final review:**
- `fresh_eyes` — optional replacement/disable for the final `fresh-eyes` pass only. Fields: `enabled` (optional bool, defaults true); when enabled and replacing built-in behavior, `type: command` plus `command` are required. `enabled: false` is explicit project policy to skip the final whole-diff pass; the primary `review` pass still runs.

**Babysit:**
- `babysit` — optional PR babysitting policy used by the `babysit` skill and Pi `/babysit` command. Fields: `goal.token_budget` (optional string such as `50k`), `loop.use_review_response` (bool, default true), `loop.run_configured_gates_before_push` (bool, default true), `loop.wait_interval_seconds` (positive integer, default 60), `loop.timeout_minutes` (positive integer, optional), `closeout.merge.mode` (`off` / `ask` / `auto`, default off), `closeout.merge.method` (`squash` / `merge` / `rebase` / `repo-default`, default repo-default), `closeout.merge.delete_branch` (bool, default false), `closeout.memento.mode` (`off` / `ask` / `auto`, default off), `closeout.retro.mode` (`off` / `ask` / `auto`, default off), and `closeout.retro.apply_findings` (`off` / `ask` / `auto`, default ask). `auto` removes routine prompts only when action policy allows; policy `ask` still asks and policy `deny` still stops.

**Envelope:**
- `envelope` — optional config for the `/envelope` skill. Fields: `rubric_path` (optional repo-relative `.md` path, no `..` segments) replacing the skill's built-in AFK-eligibility rubric. See **Envelope shape** below.

**Paired (Phase 4d of ready-for-review):**
- `domain_expert.agent` — domain expert name (paired with `knowledge_store.path`); kickoff resolves it as a subagent first and, on hosts without a subagent mechanism, may fall back to an installed Beislið skill with the same name
- `knowledge_store.path` — repo-relative path (paired with `domain_expert.agent`)

**Walkthrough thresholds:**
- `guided_walkthrough.threshold_files`, `guided_walkthrough.threshold_lines`

**Cache:**
- `probe_cache` — fields: `ttl_hours` (integer; defaults to 24 when absent)

Capabilities not in this list are unknown — doctor reports them with a `💭` inline note and continues.

## Pi handoff shape

`pi_handoff` lets a repo declare team intent for the Beislið Pi extension's automatic fresh-session handoff behavior. It is host-specific policy for Pi-managed command wrappers; portable skills still write/read checkpoint artifacts and print manual fresh-context guidance for Claude and other hosts.

````markdown
## Pi handoff

```beislid:pi_handoff
enabled: true
events: all
exclude: []
```
````

`enabled` defaults to true when the Beislið Pi extension is active. `events` may be `all` or a list of lifecycle/checkpoint event names; `exclude` suppresses specific events from that set. The Pi extension only auto-switches sessions when it owns the managed workflow run and can validate a readable `.beislid/checkpoints/latest.json` pointer or equivalent checkpoint input. Local Pi extension settings are the final override over repo workflow intent. Missing or unreadable checkpoint artifacts fall back to the existing manual guidance; the extension must not synthesize continuation context from live session history.

## Visual surfaces shape

`visual_surfaces` lets a repo opt into optional visual review/planning surfaces without making user-level plugin state surprising. Beislið owns config, routing decisions, prompt semantics, and fallback guidance; the provider owns local editor/runtime behavior. In v1 the only provider is `lavish-axi`.

````markdown
## Visual surfaces

```beislid:visual_surfaces
provider: lavish-axi
mode: prompt
command: 'npx -y lavish-axi'
artifact_root: .lavish
artifact_retention: local
workflows:
  spec: prompt
  blueprint: suggest
  poke-holes: suggest
  show-me: auto
```
````

`mode` controls proactive use: `off` disables visual routing, `suggest` mentions that a visual surface may help, `prompt` asks before opening/invoking one, and `auto` allows configured workflows to open/invoke without another prompt when their own action policy permits it. Per-workflow overrides inherit the global mode when absent. `command` defaults to the enabled Lavish plugin command, then `npx -y lavish-axi`; doctor validates shape but should not deep-invoke the command. `artifact_root` defaults to `.lavish` and must be a relative repo-local path with no `..` segments. `artifact_retention` controls supplemental Lavish HTML only: `local` keeps ignored local wrappers, `discard` removes wrappers after use, and `preserve-repo` requires explicit workflow intent plus a gitignore exception before anything is committed. Repo config is required for proactive routing; user-level plugin enablement alone is not enough.

Planning workflow routing is conservative: `blueprint` surfaces are for visual plans, implementation-option comparisons, architecture/data-flow diagrams, and risk/test matrices that materially improve design approval; `poke-holes` surfaces are for decision trees, branching tradeoffs, risk maps, and diagram-backed stress tests. Simple linear planning turns stay in Markdown/chat.

When a workflow's effective visual-surface mode is active, load the portable Lavish contract from canonical `.beislid/visual-surface-protocol.md` or that workflow skill's readable auxiliary copy. That protocol defines the supplemental HTML review surface rules, provider boundary, fallback behavior, planning workflow surface loops (`Blueprint design surface loop` and `Poke-holes decision-tree surface loop`), the `BEISLID_VISUAL_PROMPT_V1` prompt envelope, Show Me deck routing and artifact_retention semantics, and the `BEISLID_VISUAL_FEEDBACK_V1` typed gate validation contract. Workflows must not claim Lavish routing is active without repo-level `beislid:visual_surfaces` config.

Typed gate feedback and freeform annotations are distinct. Only a typed payload that validates for the current workflow/action may count as a visual gate decision; unknown actions, unknown decisions, malformed payloads, freeform-only feedback, or parser-unavailable hosts fall back to manual Markdown/chat review. The optional `beislid visual-feedback normalize` helper normalizes accepted events and reports `manual_review` with `canonical_update_required` so the canonical Markdown/chat record remains auditable. V1 planning gates include `blueprint` action `approve_revise_or_choose_blueprint` for approve/revise/choose and `poke-holes` action `resolve_revise_or_choose_poke_holes` for resolved/revise/choose; visual choices require `selected_option` and do not approve implementation by themselves.

## Workflow signals shape

`workflow_signals` lets Beislið skills emit local, transcript-safe workflow-state signals. Beislið owns the semantic state (`waiting`, `verify`, `blocked`, etc.); sinks own local side effects. In v1 the only executable sink is `tmux-glance`, which annotates the current tmux window/tab through the external `tmux-glance` CLI when available. Pi's managed Beislið wrapper additionally surfaces emitted signals in Pi's status/title UI and emits a best-effort start signal for managed skill commands.

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

Valid states are `working | blocked | waiting | verify | review | done | explore`. `mode: off` disables signal emission. Skill overrides inherit the global mode when absent. Sink execution is best-effort: outside tmux, without `tmux-glance`, or on a sink failure, the workflow continues silently. The `tmux-glance` sink maps `explore` to its working marker when the installed `tmux-glance` command has no dedicated explore state. Future sink types may fan the same normalized signal to other local processes, but they must use constrained transcript-safe metadata and must not become external tracker/PR side effects.

Skills should emit signals only when they have real semantic knowledge. For example, `ready-for-review` can mark gate execution as `verify`, review phases as `review`, hard approval boundaries as `waiting`, and blocking failures as `blocked`; `poke-holes` can mark each interview question as `waiting` and interrogation/exploration as `working`.

Use the CLI for manual or skill-driven emission:

```bash
beislid workflow-signal emit waiting --skill ready-for-review --phase approval
beislid workflow-signal status --skill ready-for-review
```

## Model routing shape

`model_routing` lets a repo declare which host model candidates should run specific Beislið skills. It is a host-adapter control contract: hosts honor it when they expose model selection, disclose fallback when they cannot, and block only for required routes that cannot be honored.

````markdown
## Model routing

```beislid:model_routing
defaults:
  models: [openai:gpt-5.1-codex]
  mode: prefer
overrides:
  - skills: [spec, blueprint, poke-holes]
    models: [anthropic:claude-opus-4.8, google:gemini-2.5-pro]
    mode: require
  - skills: [implement, ready-for-review, review-response]
    model: openai:gpt-5.1-codex
tiers:
  light: [google:gemini-2.5-flash, anthropic:claude-haiku-4.5, openrouter:deepseek/deepseek-chat-v3.1]
  standard: [openai:gpt-5.1-codex, anthropic:claude-sonnet-4.6, google:gemini-2.5-pro]
  heavy: [anthropic:claude-opus-4.8, openai:gpt-5.1-codex, google:gemini-2.5-pro]
  frontier: [anthropic:claude-opus-4.8, google:gemini-2.5-pro, openai:gpt-5.1-codex]
tier_mode: prefer
```
````

`model` is shorthand for `models: [<value>]`; use one or the other, not both. `models` is an ordered acceptable candidate list. Portable aliases are `opus`, `sonnet`, `haiku`, `default`, and `host-default`; namespaced provider strings such as `openai:gpt-5.1-codex` are allowed as escape hatches. Ordered overrides are first-match by skill name; defaults apply when no override matches. `mode: prefer` continues with a disclosed fallback when unsupported; `mode: require` stops before invoking the routed skill unless at least one candidate can be honored. Subagents inherit the parent skill's resolved model by default when the host supports subagent model selection. `when:` is reserved for future conditional routing and must not be treated as unconditional.

Some repos also carry a separate Rondo execution profile whose `model_routing` block nests `step_hints` (`initial`, `steps`, `phases`) for kickoff/ready-for-review phase routing. That adapter is not part of the `.beislid/workflow.md` v1 skill-routing syntax; it is documented and validated separately.

`tiers` is an optional map from provider-neutral capability tier names — exactly `light`, `standard`, `heavy`, `frontier`; other names are reserved — to ordered provider candidate lists (e.g. `heavy: [anthropic:claude-opus-4.8, openai:gpt-5.1-codex]`). Tiers are how envelope-authored slices declare capability needs without naming providers: export resolves a slice's tier through this table into `runner_extensions.model_routing.candidates`. When the repo omits `tiers`, Beislið resolves through the versioned shipped defaults documented in `docs/configuration.md` (current table: `research-v1`). Optional `tier_mode` (`prefer` / `require`, default `prefer`) sets the default resolution mode stamped into exported tier hints; per-envelope overrides happen at approval.

## Babysit shape

`babysit` config controls the persistent PR babysitting loop and optional closeout automation. The skill still requires host goal support, live PR evidence, and action-policy handling at every side-effect boundary.

````markdown
## Babysit

```beislid:babysit
goal:
  token_budget: 50k
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 60
  timeout_minutes: 60
closeout:
  merge:
    mode: ask
    method: squash
    delete_branch: true
  memento:
    mode: ask
  retro:
    mode: ask
    apply_findings: ask
```
````

Closeout mode values are `off`, `ask`, and `auto`. `off` disables that closeout step. `ask` stops for explicit approval. `auto` proceeds without an extra babysit prompt only when action policy allows the specific side effect; policy `ask` still asks and policy `deny` still stops. Invocation args can override config for a single run, for example `stop when green`, `don't merge`, `merge then stop`, `skip memento`, or `skip retro`.

`loop.use_review_response: true` means `babysit` delegates actionable PR feedback handling to `review-response` rather than reimplementing categorization, fixing, safe replies, commits, and pushes. `false` means `babysit` stops with the loaded feedback summary and asks the user how to proceed instead of fixing, replying, committing, or pushing automatically. `loop.run_configured_gates_before_push: true` means babysit-owned pushes and merge preparation must use the same configured gates/scopes/gate sets as other Beislið PR workflows.

## Envelope shape

`envelope` config customizes the `/envelope` skill. All keys are optional; omitting the block means skill defaults.

````markdown
## Envelope

```beislid:envelope
rubric_path: docs/afk-rubric.md
```
````

`rubric_path` points at a repo-relative `.md` file that replaces the skill's built-in AFK-eligibility rubric (`skills/envelope/afk-rubric.md`, currently `afk-rubric-v1`). The path must be relative, end in `.md`, and contain no `..` segments; anything else is invalid and the skill falls back to the built-in rubric with a warning. Resolution is repo-override-first: when `rubric_path` resolves to a readable file, that rubric's version string is judged against and recorded in exports; otherwise the skill default applies.

## Fresh-eyes replacement shape

`ready-for-review` always runs the primary `review` pass on the normal new-PR path. Configure `fresh_eyes` only to change the final whole-diff `fresh-eyes` pass.

Use a custom command replacement:

````markdown
## Ready-for-review

```beislid:fresh_eyes
type: command
command: 'node tools/codex-companion.mjs adversarial-review --wait --scope branch'
```
````

Or explicitly disable the final pass as project policy:

````markdown
## Ready-for-review

```beislid:fresh_eyes
enabled: false
reason: 'Final review is enforced by an external required check.'
```
````

The command is probed like a CLI capability by checking its first binary. It should exit nonzero for blocking findings; ambiguous output is treated as blocking until the user provides evidence or accepts risk.

## Ready-for-review approval gates shape

`ready_for_review` lets a repo configure which ready-for-review approval gates prompt interactively versus auto-approve after recording the decision. When a gate is `auto`, the skill logs the decision and metadata to the transcript and run ledger, then continues without an interactive prompt. Real-risk stops — critical review findings, merge conflicts, missing credentials, destructive actions, and policy denials — are never downgraded by this config.

All gates default to `prompt` (safe, backward-compatible). Set individual gates to `auto` only when the repo trusts the agent's generated metadata enough to skip the prompt:

````markdown
## Ready-for-review

```beislid:ready_for_review
approval_gates:
  pr_title_body: prompt
  gate_failure: prompt
  autofix_commit: prompt
  clean_eval_failure: prompt
  reduced_review_coverage: prompt
```
````

`pr_title_body` controls the Phase 4 hard gate where the user must approve the PR title and body before push/creation. When a prompt is needed, the blocking approval question belongs only in the final user-facing response. `auto` logs the title/body to the transcript and continues without prompting.

`gate_failure` controls Phase 2 prompts when a configured gate fails. `auto` records the failure envelope, auto-accepts risk for non-critical failures, and continues; environment failures and missing tools still block.

`autofix_commit` controls whether autofix diffs are committed without interactive approval. `auto` policy-checks the commit, records the diff, and commits without prompting unless action policy denies.

`clean_eval_failure` controls the clean evaluator failure prompt. `auto` records the failure and skips clean eval for this session; patch regressions still block.

`reduced_review_coverage` controls the explicit reduced-coverage acceptance prompt when review is cancelled or incomplete. `auto` records the reduced-coverage status and continues without prompting.

## Action policy shape

Action policy controls how repo-aware orchestrators decide whether side effects may proceed. The deterministic evaluator lives behind `beislid action-policy evaluate`; workflow config supplies optional overrides on top of built-in defaults. Actions may carry multiple classes, and the strictest applicable decision wins (`deny` > `ask` > `allow`). Unknown or unclassified actions default to `ask` in both built-in modes.

Example override:

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

Built-in defaults:

- `supervised-auto`: `read` and `network-read` allow; `workspace-write`, `dependency-install`, `git-local`, `git-remote`, and `secret-bearing` ask; `destructive` denies; no sandbox baseline is required, but uncommitted changes ask.
- `unattended-auto`: `read` and `network-read` allow; `workspace-write`, `dependency-install`, and `git-local` ask; `git-remote`, `destructive`, and `secret-bearing` deny; sandbox minimum is `non-default-branch`, and uncommitted changes ask.

Evaluator input is explicit JSON/config from the calling orchestrator. The evaluator intentionally does not attempt full shell parsing. It uses a small known-action registry plus conservative secret-bearing heuristics for obvious tokens, environment variable names, and authorization headers. Optional `actions` entries are explicit project allow/ask/deny decisions for stable action ids such as `pr.review.reply`; they may relax `ask` and ordinary policy denies but are floored by the protected classes — a `destructive` or `secret-bearing` decision can never be downgraded per action, only by an explicit mode-wide class rule. Doctor validates policy overrides through the same evaluator contract (`beislid action-policy validate`) and records a concise effective-policy summary rather than probing an external dependency.

The policy decision envelope contains `decision`, `mode`, `action`, `classes`, `matched_rules`, `sandbox_status`, `requires_human`, `log_level`, `reason`, and `remediation`. Run summaries and ledger events should preserve that shape, plus a separate human outcome when an `ask` decision is accepted or declined.

## Gate object shape

Gate lists are backward-compatible. Existing flat gates remain valid:

```yaml
- name: test
  command: npm test
  autofix: npm run lint -- --fix # optional
  parallel_safe: true          # optional fast-path hint for independent read-only gates
```

A flat gate is shorthand for a staged sensor with these defaults: `stage: pre-pr`, `kind: sensor`, `execution: computational`, `mutates: false`, no selector, no output parser, and no retry policy beyond the orchestrator's normal user-directed failure handling.

Rich gates may add harness metadata. `name` is always required. `command` is required for executable command gates, including every P0-runnable gate; non-command declarations must be explicitly represented through `kind` or `execution` metadata and are reported rather than executed by P0 orchestrators:

```yaml
- name: full-tests
  stage: pre-pr
  kind: sensor
  execution: computational
  command: '.venv/bin/python -m pytest'
  timeout_seconds: 600
  cost: expensive
  mutates: false
  accepts_files: false
  required_tools: ['python']
  changed_file_selector:
    include: ['memento/**/*.py', 'hooks/**/*.py', 'tests/**/*.py']
  output:
    parser: pytest
    agent_summary: true
  failure:
    retryable: true
    max_fix_iterations: 2
    stop_if_patterns:
      - 'No module named'
    hint: 'Fix failing tests. If this is an environment issue, stop and report it.'
```

Supported stage values are `preflight`, `per-edit`, `pre-commit`, `pre-pr`, `post-pr`, `continuous`, and `human-interrupt`. P0 `ready-for-review` and `review-response` execute legacy gates and computational `stage: pre-pr` sensor gates only; other stages are valid metadata for Rondo/future orchestrators and must be reported, not silently executed at the wrong lifecycle point.

`kind` currently recognizes `sensor` for gates that observe readiness. Future guide/feedforward artifacts are tracked separately from gate lists. P0 command execution runs only gates where `kind` is absent or `sensor`; other `kind` values are metadata declarations that are reported as non-sensor and not executed. `execution` may be `computational`, `inferential`, or `human`; P0 command execution supports `computational` gates directly and reports `inferential`/`human` entries as non-command metadata declarations unless a future orchestrator owns them.

`cost` is free-form but recommended values are `cheap`, `medium`, and `expensive`. `required_tools` is a list of additional CLI binaries the gate depends on beyond the command's first word; doctor and gate-running orchestrators probe each with `command -v` before treating the gate as runnable. `mutates: true` means the gate may edit files or external state and must not be auto-batched as read-only. `parallel_safe: true` remains the fast-path batching flag and is only honored when the gate has no `autofix` and `mutates` is not true.

Selectors may use `changed_file_selector.include` / `exclude` glob lists (or legacy draft `selector.paths`) to describe when the gate is relevant. Gate-level selectors are advisory metadata unless a selected gate set includes the gate; the changed-file-aware selector model is `gate_sets`.

Output/parser metadata is declarative. `output.parser` may name parsers such as `generic-text` or `pytest`, but the full agent-readable result envelope is handled by the gate-result-envelope work. `failure` may declare `retryable`, `max_fix_iterations`, `stop_if_patterns`, and `hint`; P0 orchestrators surface this context in failure prompts but still require user direction before risky fixes or skips.

## Gate metadata to Proof Requirement mapping

A runnable gate can be exported as a `proof-requirement-v1` `command_gate` without depending on skill prose. Map `name` to `id`, `stage` to proof `stage`, selected path metadata to `applies_to.paths` / `applies_to.exclude`, and `output` to `expected_artifact`. Default `failure_policy` to `on_missing: block` and `on_failure: block`; copy `failure.retryable`, `max_fix_iterations`, `stop_if_patterns`, and `hint` when present. A passing gate envelope satisfies proof; failing, skipped, or missing required gates block readiness or create the configured human interrupt.

Setup/pre commands are prerequisites, not proof. Code generation, dependency download, and other setup steps may block dependent gates when they fail, but they do not by themselves prove quality or done status.

## Gate-set selection shape

`gate_sets` is the preferred model when a project needs deterministic changed-file-aware checks. It is optional and takes precedence over legacy `scopes` / top-level `gates` when configured; if absent, orchestrators keep the old fallback behavior.

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

Selection is driven by the changed file list. Orchestrators evaluate selectors in file/config order, match `paths` with git-style globs, apply optional `exclude` globs, then union the referenced sets deterministically: first selector order, then `gate_sets` order inside the selector, then gate declaration order inside each set. Duplicate gates are de-duped by stable identity (`set`, `cwd`, `name`, `command`) so the first selection reason wins.

Every run should explain selection. For each selected gate, record the changed file(s), selector, and gate set that selected it. For skipped selectors, record that no changed file matched. For skipped gates, record whether the reason was stage, execution/kind, missing command/tools, or another normalized-gate rule. P0 `ready-for-review` and `review-response` execute only selected gates that also normalize to executable computational `pre-pr` sensors; other stages remain metadata and are reported as skipped, not run at the wrong lifecycle point.

Gate sets work with the same **Gate object shape** as `gates` and scope gates. A set-level `cwd` applies to gates in that set unless a gate declares its own `cwd`; absent `cwd` runs from the repo root. A set-level `stage` may be used as metadata for all gates in the set, but gate-level `stage` wins.

## Lifecycle actions shape

Lifecycle actions are optional side effects at named workflow events. They are not quality gates: gates prove branch readiness, while lifecycle actions mutate external systems or create user-approved records.

P0 executes ordered CLI actions for `kickoff_start`, immediately after kickoff fetches ticket context:

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
        on_failure: prompt
      - name: move-in-progress
        type: cli
        command: 'example-tracker transition {ticket_id} in-progress --branch {branch}'
        approval: auto
        on_failure: abort
```
````

For CLI actions, `approval` is required. `approval: auto` runs once configured; `approval: prompt` asks before running. Orchestrators must pass placeholder values through argv construction when available or shell-quote them before execution; raw branch/ticket text must not be spliced into a shell. `on_failure` is optional and defaults to `prompt`, which preserves the current retry / skip-remaining-this-session / abort flow when a configured side effect fails. `on_failure: continue` warns and proceeds without blocking the workflow, while `on_failure: abort` stops the owning skill immediately. Use `continue` only for explicitly best-effort side effects; use `abort` when later workflow steps are unsafe without the side effect.

P0 also executes ordered actions for approved planning outputs. Artifact actions write the approved Markdown output; CLI actions run configured side effects after approval:

````markdown
## Lifecycle actions

```beislid:lifecycle_actions
events:
  break_spec_approved:
    actions:
      - name: write-structure-artifact
        type: artifact
        approval: prompt
        # optional; default is plans/{feature}-structure.md
        path: 'plans/{feature}-structure.md'
  spec_approved:
    actions:
      - name: write-spec-artifact
        type: artifact
        approval: prompt
        # optional; default is plans/{feature}-spec.md
        path: 'plans/{feature}-spec.md'
      - name: post-spec-body-to-tracker
        type: tracker
        approval: prompt
      - name: announce-approved-spec
        type: cli
        command: 'notify-planning-approved {event} {ticket_id} {artifact_path}'
        approval: prompt
        classes: [git-remote]
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        # optional; default is plans/{feature}-design.md
        path: 'plans/{feature}-design.md'
      - name: run-design-hook
        type: cli
        command: 'planning-hook {event} {feature} {kind}'
        approval: auto
        classes: [workspace-write]
```
````

`break-spec` owns the `break_spec_approved` event; `spec` owns the `spec_approved` event; `blueprint` owns the `blueprint_approved` event. Kickoff only passes context in and records returned lifecycle status/path. Under these events, P0 supports `type: artifact` and `type: cli` for all planning approvals, and `spec_approved` additionally supports `type: tracker` posts that reuse the configured `ticket_update` issue channel to update the ticket body with approved spec text. MCP and other providers are reserved and skipped unless the event explicitly documents them. Artifact actions write the approved structure/spec/design Markdown to a repo file; a `work-contract-v1` section or artifact uses these same events rather than a separate config key. `approval: prompt` asks before writing, running, or posting; `approval: auto` creates a missing artifact without another prompt or runs/posts once configured; omitted artifact approval defaults to `prompt`, while CLI and tracker approval are required. Existing artifact targets always prompt for overwrite / choose another path / skip. Skips and reserved providers do not block routing to downstream skills. Failed actions use `on_failure`: omitted/`prompt` asks for retry / skip or override / abort, `continue` warns and routes onward without that side effect, and `abort` stops downstream routing.

Artifact `path` is a file path template. If omitted, defaults are `plans/{feature}-structure.md` for break-spec outputs, `plans/{feature}-spec.md` for specs, and `plans/{feature}-design.md` for designs. Supported placeholders are `{feature}` (slug from approved title, then ticket title, then branch, else ask), `{kind}` (`structure`, `spec`, or `design`), and `{ticket_id}` when ticket context is known. If `{ticket_id}` is used and no ticket id is available, runtime asks for another path or skip; it must not write `unknown` or silently drop the placeholder. Paths must be relative, stay inside the repo root, contain no `..` segments, and end in `.md`. Parent directories may be created as part of an approved or auto write.

Planning-event CLI actions use the same placeholder safety posture as kickoff lifecycle CLI actions: orchestrators pass values through argv construction when available or shell-quote before execution, never splicing raw branch/ticket text into a shell. Supported planning placeholders are `{ticket_id}`, `{id}` (alias), `{branch}`, `{event}`, `{feature}`, `{kind}`, and `{artifact_path}` (the latest written/auto-written artifact path for this event, or empty when no artifact has been written). Do not expose approved structure/spec/design body text as a command-line placeholder; use an artifact path or a future file-based provider instead. Before each action, skills evaluate action policy with action id `lifecycle.<event>.<name>`; artifact actions use class `workspace-write`, and CLI actions use configured `classes` or the conservative default `[workspace-write, git-remote]`.

Planning artifacts are checkpoint-compatible state seeds: a fresh context may use an approved structure/spec/design artifact as primary input when it captures enough context for the next skill. Checkpoint event artifacts are a narrow bridge toward clear-context and Rondo-style execution when workflows need operational resume metadata around a boundary, not just the approved planning deliverable. P0 executes `kickoff_context_ready` after kickoff has enough context to choose the next route, and `implementation_plan_created` after `implement` has written the implementation plan but before code changes. Reserved checkpoint events `review_feedback_loaded` and `ready_for_review_pre_submit` are valid to document future workflow intent, but current skills report and skip them.

Checkpoint event artifacts use the same safety posture as planning artifacts: `approval` omitted means `prompt`; `approval: auto` creates only missing files; existing targets always prompt; `on_failure` omitted means `prompt`; paths must be relative `.md` files inside the repo with no `..` segments. If omitted, default paths are `checkpoints/{event}-{ticket_id}.md` when ticket context is known, otherwise `checkpoints/{event}-{feature}.md`. Supported path placeholders are `{event}`, `{feature}`, `{kind}` (`checkpoint`), and `{ticket_id}` when ticket context is known. After a checkpoint event artifact is written, the executing skill updates `.beislid/checkpoints/latest.json` as a lightweight latest-pointer index for fresh-context rediscovery. Planning artifacts do not need to update this pointer to be valid checkpoint inputs; default `plans/` paths are discoverable and custom paths travel through handoff context. The pointer shape is versioned JSON with a `latest` object keyed by event; each entry records `event`, `path`, optional `ticket` object, `branch`, `source_skill`, and `written_at` when available. That pointer is replaceable convenience state only: no run ID, no event history, no gate logs, and no resume state machine.

The durable run ledger is separate from workflow-configured checkpoint artifacts. It lives in external Beislið state by default at `${BEISLID_STATE_DIR:-~/.local/state/beislid}/runs/<flow>/<repo_hash>/<run_id>/` and is managed by `beislid run-ledger ...`. The ledger may index checkpoint artifact paths, but it owns run IDs, append-only event history, gate log indexes, interruption/resume metadata, approved risks, and final reports. Current run status values are `running`, `interrupted`, `failed`, and `completed`; repo-local `.beislid/runs` is reserved for a future explicit opt-in.

Future events such as `pr_opened`, MCP/file-payload providers for planning events, ship-time artifact handling, and repo-local run-ledger storage are reserved for later Beislið versions.

## Explore skill shape

Use a custom skill to replace or enhance kickoff's default codebase exploration. Put it under a recognized Kickoff/Skill-specific overrides section:

````markdown
## Kickoff

```beislid:explore
skill: guide
mode: enhance
```
````

`replace` means the skill must provide the Step 2 context packet instead of default exploration. If it fails, kickoff prompts to retry, fall back to default exploration for this session, or abort. `enhance` runs default exploration first, then merges skill findings when available.

## PR reviews worked shape

```markdown
## PR reviews

​```beislid:pr_review_source
type: cli
summary_command: 'gh pr view --json url,number,reviewDecision,reviews,comments'
threads_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments'
​```

​```beislid:pr_review_update
type: cli
reply_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments --method POST --input {json_file}'
rerequest_command: 'gh api repos/{owner}/{repo}/pulls/{number}/requested_reviewers --method POST --input {json_file}'
​```
```

For `pr_review_update`, review-response writes JSON payload files instead of interpolating comment bodies into shell strings. Reply payloads use `{ "body": "...", "in_reply_to": 123 }`; re-request payloads use `{ "reviewers": ["octocat"] }`.

Manual PR review source is explicit:

````markdown
```beislid:pr_review_source
type: paste
```
````

Manual PR review updates are explicit:

````markdown
```beislid:pr_review_update
type: manual
```
````

## Disabled-state convention

To disable a capability for a project, write a section whose prose explicitly says "Disabled for this project" (or similar) and omit the fenced block. Doctor records the capability as `disabled` — semantically distinct from `missing` (probe failed) and from absent-from-the-file (treated as `not configured`).

Disabled is a deliberate user choice. Missing is a probe result. Not-configured is silence.

## Skill-specific subsections

H3 subsections under a skill name hold capabilities only one orchestrator uses. Naming pattern: H3 named after the skill in title case. Capabilities still use the same `beislid:<key>` info-string convention.

```
### Ready-for-review overrides

​```beislid:guided_walkthrough.threshold_files
8
​```
```

## Duplicate keys

When the same `beislid:<key>` appears in multiple fenced blocks, the **first occurrence wins**. Doctor warns about subsequent duplicates in prose, naming the line of each. This is lenient by design — duplicates usually come from copy-paste or merge conflicts; the audit surfaces them so the user can clean up.

## Worked example

```markdown
<!-- beislid-workflow: v1 -->

# Beislið workflow config — example-project

## Issue tracker

GitHub Issues on `acme/example-project`, accessed via the `gh` CLI.

​```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body,labels'
id_pattern: '^#?\d+$'
​```

​```beislid:branch_pattern
^(\d+)-
​```

## Scopes

Frontend (Next.js) and backend (Hono) get different gates.

​```beislid:scopes
- name: frontend
  paths: ['apps/web/**']
  cwd: apps/web
  gates:
    - { name: lint, command: 'pnpm lint' }
    - name: typecheck
      stage: pre-pr
      kind: sensor
      execution: computational
      command: 'pnpm typecheck'
      timeout_seconds: 120
      cost: medium
      mutates: false
      output:
        parser: generic-text
      failure:
        retryable: true
        max_fix_iterations: 1
- name: backend
  paths: ['apps/api/**']
  cwd: apps/api
  gates:
    - { name: lint, command: 'bun run lint' }
​```

​```beislid:split_policy
exclusive
​```

## Translation sync

Disabled for this project.

## Browser compat

Disabled — no shared frontend components.

## Domain capture

​```beislid:domain_expert.agent
researcher
​```

​```beislid:knowledge_store.path
knowledge-base/
​```

## Probe cache

​```beislid:probe_cache
ttl_hours: 24
​```
```
