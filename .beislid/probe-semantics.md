# Beislið probe semantics

Beislið uses these probe techniques to test whether a configured capability resolves in the current session. Doctor and orchestrators consume this file at runtime via a per-skill auxiliary symlink.

Capability fenced blocks declare a `type` field that selects the probe kind. This file documents the probe technique for each kind, what each status means, and how `probe_supported` is computed.

## Probe kinds

### mcp

Capability declares one MCP tool name (e.g. `tool: mcp__plugin_linear_linear__get_issue`) or a logical set of related MCP tools (e.g. `ticket_update.comment_tool` + optional `issue_tool`).

**Probe:** ask the host agent for its tool registry and check whether every configured tool for the logical capability is registered in this session. A host-adapter alias for an equivalent tool may satisfy the configured route when the registry can prove the mapping; record whether the hit was exact or alias-satisfied in the captured value/prose.

| Status | Condition |
|---|---|
| `ok` | Every configured tool is available, either by exact registration or by a host-adapter alias for an equivalent tool. `probe_supported: true`. |
| `missing` | One or more configured tools are not registered in the session and no host alias resolves them. `probe_supported: true`. Reason names the missing tools, e.g. `"tools 'mcp__x__comment', 'mcp__x__issue' not registered in this session"`. |
| `failed` | Tool registry lookup raised. `probe_supported: true`. Reason captures the error. |

If the host has no MCP tool registry mechanism at all, status is `failed` with `probe_supported: false` and reason `"host has no MCP tool registry"`.

Known multi-tool logical MCP capabilities:

- `ticket_update` (`comment_tool`, optional `issue_tool`)
- future PR review MCP providers, when added to the grammar

### cli

Capability declares one shell command (e.g. `command: 'gh issue view {id}'`) or a logical set of related commands (e.g. `pr_review_source.summary_command` + `threads_command`).

**Probe:** run `command -v <first-word>` via Bash. The first whitespace-separated word of each command is the binary name. For multi-command capabilities, probe every unique binary and record one logical capability result.

| Status | Condition |
|---|---|
| `ok` | Every required binary exits 0 from `command -v`. `probe_supported: true`. |
| `missing` | One or more binaries exit ≠ 0. `probe_supported: true`. Reason names the missing binaries, e.g. `"gh, glab not on PATH"`. |
| `failed` | Bash unavailable. `probe_supported: false`. Reason: `"host has no Bash mechanism"`. |

Known multi-command logical capabilities:

- `pr_review_source` (`summary_command`, optional `threads_command`)
- `pr_review_update` (`reply_command`, optional `rerequest_command`)
- `fresh_eyes.command` when `beislid:fresh_eyes` uses `type: command`; probe the command's first binary. `enabled: false` has no probe and records an explicit policy value.
- `ticket_update` when `comment_command` is configured, with optional `issue_command`. Probe only the binaries; placeholder validation (`{body_file}` / `{title_file}` rather than raw `{body}` / `{title}`) is performed by setup/orchestrators before execution.
- `lifecycle_actions.<event>` for P0 CLI actions under one event's `actions[]` list. Probe every unique first binary from that event's `type: cli` action commands and record one logical capability. Validate each action's optional `on_failure` as exactly `prompt`, `continue`, or `abort`; omitted means `prompt`. Orchestrators probe only events they execute, e.g. kickoff probes `lifecycle_actions.kickoff_start`, while spec/blueprint/break-spec probe their own planning approval event when it contains CLI actions. Future events must not block current-event execution. Non-CLI providers such as `mcp` are reserved for CLI lifecycle actions; orchestrators must not execute unsupported providers.

### path

Capability declares a filesystem path (e.g. `path: knowledge-base/`).

**Probe:** resolve the path against the git repo root, run `test -d <resolved>` for directories or `test -f <resolved>` for files. Defaults to `-d` unless the capability specifies `kind: file`.

| Status | Condition |
|---|---|
| `ok` | `test` exits 0. `probe_supported: true`. |
| `missing` | `test` exits 1. `probe_supported: true`. Reason: `"path '<resolved>' does not exist"`. |
| `failed` | Bash unavailable. `probe_supported: false`. |

### skill

Capability declares a Beislið skill name (e.g. `formatter_skill: tone`).

**Probe:** resolve Beislið-controlled skill paths before host/global fallbacks. Look for `<skills-dir>/<name>/SKILL.md` or `<skills-dir>/<name>.md` in this order: repo-local `.beislid/skills/` (resolved from the git repo root), `$BEISLID_SKILLS_DIRS` if set, then `~/.agents/skills`, `~/.claude/skills`, `~/.codex/skills`. Host skill discovery may be used only when it can preserve this precedence.

| Status | Condition |
|---|---|
| `ok` | Skill found at any candidate location. `probe_supported: true`. |
| `missing` | Skill not found at any candidate. `probe_supported: true`. Reason: `"skill '<name>' not found in repo-local .beislid/skills or any configured/global skills directory"`. |
| `failed` | Filesystem read raised. `probe_supported: true`. Reason captures the error. |

Kickoff's `explore.skill` uses this probe kind.

### subagent

Capability declares a subagent name (e.g. `agent: researcher`).

**Probe:** if the host has a subagent/delegation mechanism, query it for the named subagent.

| Status | Condition |
|---|---|
| `ok` | Subagent is registered. `probe_supported: true`. |
| `missing` | Host has subagents but the named one isn't registered. `probe_supported: true`. Reason: `"subagent '<name>' not registered"`. |
| `failed` | Host has no subagent mechanism. `probe_supported: false`. Reason: `"host has no subagent mechanism"`. |

`probe_supported: false` here is the canonical case. Orchestrators that depend on ordinary subagent-only capabilities treat this as a host limitation and skip the dependent step without prompting the user.

Kickoff has one hybrid special case: `domain_expert.agent` probes as a subagent first for backwards compatibility, but when the subagent probe returns `failed` with `probe_supported: false`, kickoff falls back to probing the same configured name as a `skill` capability. If that skill probe succeeds, kickoff invokes the skill inline in the current conversation and carries `domain_expert_resolution: skill` through Step 2 and Step 7 as run-local context. Kickoff must not write that skill-fallback success as the generic cached `domain_expert.agent` result, because future runs still need to start with the subagent-first resolution path. If the host supports subagents and the configured subagent is merely missing, kickoff does not fall back to skill discovery; that remains a missing configured subagent.

## Special cases

### type=paste

The capability has no probe to run; the user supplies the value at orchestrator runtime. Doctor records `status: ok`, `probe_supported: true`, with `value: "(paste at runtime)"`. This applies to `ticket_source.type: paste` and `pr_review_source.type: paste`.

### type=manual

The capability intentionally has no automated write path. Doctor records `status: ok`, `probe_supported: true`, with `value: "(manual at runtime)"`. This applies to `pr_review_update.type: manual`; review-response prints reply/re-request instructions instead of posting.

### fresh_eyes.enabled=false

This is explicit ready-for-review project policy, not a probe. Doctor records `fresh_eyes` as `status: ok`, `probe_supported: true`, with `value: "(built-in fresh-eyes disabled by workflow)"`.

### ship_time_artifacts validation

`beislid:ship_time_artifacts` is validated as a ready-for-review ship-time narration policy for generated planning artifacts. Doctor checks shape only: optional `mode` must be `remind`, `include`, `skip`, or `clean`; absent mode defaults to `remind` when the block is present. It should record `probe_kind: validation` and summarize the mode and whether planning-artifact lifecycle actions are configured. Missing `ship_time_artifacts` is valid and means no extra ship-time narration is configured.

### review_policy validation

`beislid:review_policy` is validated, not probed. Doctor checks shape only: `agentic_reviewer.mode` must be `opt_in_final_review`; optional `provider`, `label`, and `description_keyword` must be non-empty strings when present; `risk.max_auto_closeout_risk` must be `low`, `medium`, or `high`; path lists must be lists of strings; file/change thresholds must be positive integers. Missing `review_policy` preserves old behavior. A legacy `coderabbit` object may be reported as provider-specific legacy config, but new configs should use `agentic_reviewer`.

### action_policy validation

`beislid:action_policy` is validated, not probed as an external dependency. Doctor should use `beislid action-policy validate` or the same deterministic evaluator contract to validate overrides and derive the effective policy summary.

| Status | Condition |
|---|---|
| `ok` | Policy overrides parse and validate. `probe_supported: true`, `probe_kind: validation`, value summarizes modes, sandbox minimums, fallback decisions, and known-action registry availability. |
| `failed` | Unknown mode/class, invalid decision, invalid sandbox baseline, malformed `rules`/`actions`/`sandbox`, or invalid fallback value. `probe_supported: true`; reason names the invalid path/value. |

No command, tool, path, skill, or network probe is run for this capability. Missing `action_policy` means built-in defaults apply; doctor may mention defaults in prose but should not write a disabled cache entry for an absent block.

### workflow_signals validation

`beislid:workflow_signals` is validated as local signal routing config. Doctor checks shape only: `mode` must be `off` or `auto`; `sinks` must be a list; v1 executable sink type is `tmux-glance`; unknown sink types are reserved warnings unless the shape is invalid; optional `skills` must be a map whose values are `off` or `auto`. Valid states are `working | blocked | waiting | verify | review | done | explore`. Doctor may recommend `beislid workflow-signal status`, but it must not invoke `tmux-glance` or emit test signals. Missing `tmux-glance` is graceful fallback guidance, not a config failure when the workflow shape is valid.

### model_routing validation

`beislid:model_routing` is validated, not probed as an external dependency. Doctor checks shape only: optional `defaults`, ordered `overrides[]`, route `model`/`models` candidates, `mode: prefer|require`, and override `skills[]`. It should record `probe_kind: validation` and summarize default candidates, override count, and required-route count. Runtime hosts decide whether candidates are supported; doctor may warn on unknown bare strings but must not spend model budget probing availability. `when` is reserved for future conditional routing and should warn as inactive v1 config rather than narrowing a route.

Optional `tiers` must be a map whose keys are known tier names (`light`, `standard`, `heavy`, `frontier`) and whose values are non-empty candidate lists of non-empty strings; unknown tier names warn as reserved rather than fail. Optional `tier_mode` must be `prefer` or `require`. Tier checks are validation-only: doctor never probes whether tier candidates are available, and absent `tiers` is valid (the shipped defaults in `docs/configuration.md` apply).

The repo's checked-in `WORKFLOW.md` Rondo profile may also carry `step_hints` under the same `model_routing` block. `initial` is the kickoff/context-discovery spawn hint; `steps` and `phases` are ordered rule lists that match on `stage`, `skill`, `phase`, and `step`. The dedicated step-routing consistency gate validates that file and should report malformed or unknown tier values, while the broad defaults continue to apply when `step_hints` is absent.

### visual_surfaces validation

`beislid:visual_surfaces` is validated, not deep-probed as an external provider. Doctor checks shape only: `provider` must be `lavish-axi`; `mode` and every `workflows.*` override must be one of `off`, `suggest`, `prompt`, or `auto`; optional `command` must be a non-empty string; optional `artifact_root` must be a relative repo-local path with no `..` segments; optional `artifact_retention` must be one of `local`, `discard`, or `preserve-repo`; optional `workflows` must be a map. It should record `probe_kind: validation` and summarize provider, mode, override count, artifact root, artifact retention, and Lavish plugin state guidance. Doctor may read user-level Lavish plugin state and may recommend `beislid plugin status lavish`, but it must not run a deep provider check or invoke the configured command. Missing or disabled plugin state is graceful fallback guidance, not a config failure when the workflow shape is valid.

### babysit validation

`beislid:babysit` is validated, not executed. Doctor checks shape only: optional `goal.token_budget` must be a positive integer-like string with optional `k`/`m` suffix; optional `loop.use_review_response` and `loop.run_configured_gates_before_push` must be booleans; optional `loop.wait_interval_seconds` and `loop.timeout_minutes` must be positive integers; closeout modes must be `off`, `ask`, or `auto`; merge method must be `squash`, `merge`, `rebase`, or `repo-default`; optional `closeout.merge.delete_branch` must be boolean. It should record `probe_kind: validation` and summarize goal budget, loop behavior, and closeout modes. Doctor must not start `/goal`, inspect PRs, run gates, merge, capture memento, or run retro. Missing `babysit` config is valid and means conservative defaults.

### planning/checkpoint lifecycle actions

Artifact actions under `lifecycle_actions.break_spec_approved`, `lifecycle_actions.spec_approved`, `lifecycle_actions.blueprint_approved`, `lifecycle_actions.kickoff_context_ready`, and `lifecycle_actions.implementation_plan_created` have no external dependency to probe. Doctor records one logical capability per planning event when at least one supported artifact or CLI action is configured. It evaluates artifact and CLI actions independently so artifact-only, CLI-only, and mixed planning events are all probeable/cacheable; checkpoint events still record artifact-only capabilities:

```json
"lifecycle_actions.break_spec_approved": {
  "status": "ok",
  "probe_supported": true,
  "value": "(prompted artifact at runtime)"
}
```

Use `"(auto/prompt artifact at runtime; failure: prompt)"` or similarly concise value text when the event mixes `approval: auto` and prompted actions. Doctor validates shape instead of probing: action `name` is required; `approval` may be `prompt`, `auto`, or omitted; `on_failure` may be `prompt`, `continue`, `abort`, or omitted; `path` may be omitted; configured paths must be relative `.md` file templates, must not contain `..` segments or be absolute, and may only use placeholders documented for that event. Planning artifact events allow `{feature}`, `{kind}`, and `{ticket_id}` where `{kind}` can be `structure`, `spec`, or `design` depending on the event. Checkpoint artifact events allow `{event}`, `{feature}`, `{kind}`, and `{ticket_id}`. Omitted `approval` means `prompt`. Omitted `on_failure` means `prompt`. Omitted `path` means the event default path. Invalid artifact action shape records the event capability as `failed` with `probe_supported: true` and a concise reason.

Planning approval events (`break_spec_approved`, `spec_approved`, and `blueprint_approved`) also support `type: cli` actions. Doctor validates `name`, `command`, required `approval: auto|prompt`, optional `classes[]` against action-policy class names, and placeholders limited to `{ticket_id}`, `{id}`, `{branch}`, `{event}`, `{feature}`, `{kind}`, and `{artifact_path}`; it probes the command binary using the `cli` probe kind. A CLI-only planning event records `probe_kind: cli`; an artifact-only planning event records validation/runtime artifact behavior; and a mixed event records `probe_kind: mixed` with a value summarizing both the artifact runtime behavior and CLI binary. The event capability is `failed` if any supported action shape is invalid, `missing` if a CLI binary is missing, and `ok` when all supported actions validate/probe. Skills execute supported planning actions in configured order after approval, skip reserved providers such as `mcp`, and evaluate action policy before every supported action.

Artifact actions under reserved checkpoint events `review_feedback_loaded` and `ready_for_review_pre_submit` are valid workflow intent but are not executed by P0 skills; doctor should report them as reserved rather than failed. Artifact actions on other unsupported events, non-artifact actions under checkpoint artifact events, and MCP/file-payload providers under planning events are reserved. Skills skip reserved actions.

### type=tracker lifecycle actions

Tracker actions under `lifecycle_actions.spec_approved` post the approved spec body into the current ticket body through the configured `ticket_update` issue channel. Probe `ticket_update` as a logical capability first; if the issue channel is missing, the tracker action is reserved and skipped. Doctor validates shape instead of sending the update: `name` is required; `approval` may be `prompt`, `auto`, or omitted; no filesystem path is involved. Record a concise value such as `(tracker body post via ticket_update issue channel)` when the tracker action is configured.

### type=file (file glob)

The capability declares a glob (e.g. `file_glob: '.scratch/<feature>/*.md'`). Probe via `ls <glob>` succeeds with at least one match.

| Status | Condition |
|---|---|
| `ok` | Glob expands to ≥1 file. `probe_supported: true`. |
| `missing` | Glob expands to nothing. `probe_supported: true`. Reason captures the glob string. |
| `failed` | Bash unavailable. `probe_supported: false`. |

## The `disabled` status

`disabled` is never the result of a probe. It's determined by workflow.md content: when a section's prose explicitly says "Disabled for this project" or similar, and the section has no fenced block, doctor records the capability as `disabled` without probing. Cache stores `status: disabled` with no `reason`. `probe_supported` is not set on disabled entries.

## Paired capabilities

Some capabilities are useful only together (e.g. `domain_expert.agent` + `knowledge_store.path`). Doctor probes each independently and records each status separately, then surfaces a `paired-half-missing` warning in prose when exactly one half is configured. The warning is non-blocking; orchestrators that depend on the pair skip the dependent step.

Today's known paired sets:

- `domain_expert.agent` ↔ `knowledge_store.path` (kickoff Step 7 and ready-for-review Phase 4d: agent records findings into the store; kickoff may resolve `domain_expert.agent` as either a subagent or a skill per the hybrid special case above)

PR review source/update is a soft pair, not a hard paired capability. `pr_review_source` alone is useful for reading feedback and printing manual replies. `pr_review_update` without `pr_review_source` gets a doctor warning because review-response can only use it after pasted PR feedback.
