---
name: doctor
description: Audit Beislið workflow config and probe each capability. Use when the user says "doctor", "/doctor", "audit my config", "check my workflow", "probe everything", "what's set up", or after editing workflow.md. Reports gaps in conversational prose; does not modify config or skills. Pass `--refresh` to force re-probing even if the cache is fresh.
---

# Doctor

Audit a project's Beislið workflow config end-to-end. Read `<repo>/.beislid/workflow.md`, probe each configured capability against the current host session, write a probe cache that orchestrators consume, and print a conversational audit.

Doctor is read-only on the repo and write-only on the cache. It does not modify workflow.md, install or remove skills, post comments, or invoke other orchestrators.

Pass `--refresh` to force a full re-probe even when the cache is fresh.

---

## 1. Precheck — git repo required

Run via Bash:

```bash
git rev-parse --show-toplevel
```

If exit code ≠ 0, hard-fail with this prose and stop:

> 🛑 Doctor needs a git repository. Beislið workflow config lives at `<repo>/.beislid/workflow.md`. Run `git init` here, make at least one commit, then re-run `/doctor`.

Capture the repo root path for later steps (`$git_root`).

Also verify there is at least one commit:

```bash
git rev-list --max-parents=0 HEAD | head -1
```

If exit ≠ 0 or output is empty, hard-fail with the same prose pattern adjusted to "make at least one commit." No path-hash fallback.

## 2. Read inputs

Read three files in this order:

1. `$git_root/.beislid/workflow.md` — the config under audit. If the Read fails (file does not exist), hard-fail with the **two-clause** prose and stop:

   > 🛑 No `workflow.md` found in `.beislid/`. If this is a fresh project, run `/setup` to create one. If you moved your config, restore it to `<repo>/.beislid/workflow.md`.

2. `probe-semantics.md` (relative to this SKILL.md, resolved through the per-skill symlink). If the Read fails (broken symlink), hard-fail:

   > 🛑 Doctor's probe-semantics aux is unreadable — likely a broken symlink. Re-run the Beislið installer to repair it.

3. `workflow-md-format.md` (relative to this SKILL.md, same pattern). Same broken-symlink message tailored to the format spec.

## 3. Validate the version stamp

The first line of `workflow.md` MUST match exactly:

```
<!-- beislid-workflow: v1 -->
```

If the first line is missing the stamp or shows a different version, hard-fail with prose that names what was found and offers two options:

> ⚠️ This `workflow.md` is `<found>` but doctor only knows `v1`. Update Beislið (current version is X.Y), or downgrade `workflow.md` by hand to v1 syntax. Doctor will not silently mis-parse.

Stop. Do not write a cache file.

## 4. Compute hashes

Two values are needed: the repo identity (used in the cache filename) and the workflow content hash (used to detect drift).

```bash
repo_hash=$(git rev-list --max-parents=0 HEAD | sort | head -c 12)
workflow_hash=$(git hash-object .beislid/workflow.md)
```

Sort makes multi-root histories deterministic. `git hash-object` is portable across Linux/macOS/BSD without depending on `sha256sum`.

State directory: `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/`. Cache filename: `<repo_hash>.json`.

## 5. Load existing cache

Read the cache file if it exists. Three outcomes:

- **No file** — proceed to fresh full probe at step 7.
- **JSON parse fails** — treat as no file. Don't surface in default mode (only in verbose).
- **`schema` field is anything other than `1`** — treat as no file. Reprobe and write fresh at `schema: 1`. Don't surface.

If the file parses as `schema: 1` and `--refresh` was NOT in the user's invocation:

- If `workflow_hash` in the cache matches the freshly computed hash AND `(now - doctor_run_at) < ttl_hours from workflow.md or the cache (whichever is fresher)`, narrate that the cache is fresh and exit:

  > 🩺 Workflow check on `<project_name>`. Cache is fresh from <human time, e.g. "2 hours ago"> — nothing has changed since. Run `/doctor --refresh` to force a full re-probe.

  Stop. No re-write needed.

- Otherwise (hash mismatch or stale): full reprobe at step 7.

If `--refresh` is in the invocation, skip the freshness check entirely and reprobe.

`<project_name>` is the basename of `$git_root`: `git rev-parse --show-toplevel | xargs basename`.

## 6. Prepare the cache target

```bash
mkdir -p "${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/"
```

Don't write the cache file yet — write at step 10 after probing completes.

## 7. Walk workflow.md section by section

Identify section headings (`## <Topic>`) and the typed-key fenced blocks within each. The format spec at `workflow-md-format.md` defines canonical section names and capability keys, including nested fields like `explore.skill` inside `beislid:explore`.

For each fenced block with info string `beislid:<key>`:

1. **Duplicate check.** If this `<key>` was already encountered earlier in the file, the **first occurrence wins**. Add an inline `⚠️` warning to the output narrating "found a second `beislid:<key>` block on line N — using the first one." Skip this block. Use `grep -n '^\`\`\`beislid:' .beislid/workflow.md` to map blocks to lines.

2. **Unknown key check.** If `<key>` is not in the canonical keys list (per the format spec), add an inline `💭` note: "I don't know what `beislid:<key>` is — skipping. If this is a new capability, check the format spec." Continue.

3. **Disabled-state check.** If the section's prose says "Disabled for this project" (or similar) AND no fenced block follows, record `status: disabled`, `probe_supported` not set, no probe run.

4. **Probe/validate.** Otherwise, dispatch on `type` or the key's canonical probe kind per `probe-semantics.md`:

   - For `gates`, `scopes[*].gates`, and `gate_sets.sets[*].gates`, validate both legacy flat gates and rich staged gates. `name` and `command` are required for executable P0 gates; missing or non-string values are warnings/failures tied to the gate path. Legacy flat gates default to `stage: pre-pr`, `kind: sensor`, `execution: computational`, and `mutates: false`. Rich gate metadata may include `stage`, `kind`, `execution`, `timeout_seconds`, `cost`, `mutates`, `accepts_files`, `required_tools`, `changed_file_selector` or `selector`, `output`, `failure`, `autofix`, and `parallel_safe`. Unknown stage values or unsupported execution values are warnings. Doctor should summarize staged gate counts and note that P0 ready-for-review/review-response only execute legacy/`pre-pr` command gates.
   - For `gate_sets`, also validate the selector model: `sets` must be a map of named gate sets, each referenced selector `gate_sets[]` entry must exist, selectors need `name`, `paths`, and at least one referenced gate set, and optional `exclude` must be a glob list. Missing referenced sets are failures; unmatched selectors are runtime skip reasons, not doctor failures.
   - For `clean_eval`, `mode: off` records ok policy, `mode: require` means clean worktree/container evaluation is required, optional `surface` may be `auto` / `worktree` / `container`, optional `artifact_root` must be a relative repo-local path with no `..` segments, and invalid mode/surface/path values fail validation. `mode: off` with no other fields is valid and means the working-tree path stays in place.
   - For `fresh_eyes`, `enabled: false` records ok policy, absent/true with no type uses built-in behavior, and `type: command` requires/probes `command` as `fresh_eyes.command`; other types are reserved warnings.
   - For `action_policy`, validate rather than probe an external capability. Use the deterministic evaluator contract (`beislid action-policy validate`) or the same vocabulary/defaults from `workflow-md-format.md`: modes are `supervised-auto` / `unattended-auto`; classes are `read`, `workspace-write`, `dependency-install`, `network-read`, `git-local`, `git-remote`, `destructive`, and `secret-bearing`; decisions are `allow`, `ask`, or `deny`; sandbox baselines are `none`, `non-default-branch`, `separate-worktree`, and `host-sandbox`. Unknown modes/classes/decisions/baselines, malformed `rules`, malformed `actions`, malformed `sandbox`, or invalid `unknown_action` / `unclassified_action` values mark `action_policy` as `failed` with `probe_supported: true`. Valid policy records `status: ok`, `probe_kind: validation`, and a concise value naming effective modes, sandbox minimums, action overrides, and known-action registry size.
   - For `model_routing`, validate rather than probe model availability. `defaults` is optional; `overrides` must be a list when present. Route objects use exactly one of `model` (string shorthand) or `models` (non-empty string list), optional `mode` (`prefer` or `require`, default `prefer`), and `skills` (non-empty string list, required on overrides and invalid on defaults). Record valid config as `status: ok`, `probe_kind: validation`, and a concise value naming default candidates, override count, required-route count, and any unresolved host-specific strings as warnings. A `when` field is reserved and must be warned as inactive v1 config, not treated as an unconditional route. If the repo also dogfoods a `WORKFLOW.md` Rondo profile, the separate step-routing consistency gate validates its `step_hints` adapter (`initial`, `steps`, `phases`) and should surface malformed or unknown tier values there.
   - For `visual_surfaces`, validate rather than invoke a visual provider. `provider` must be `lavish-axi`; `mode` and every `workflows.*` value must be `off`, `suggest`, `prompt`, or `auto`; optional `command` must be a non-empty string; optional `artifact_root` must be a relative repo-local path with no `..` segments; optional `artifact_retention` must be `local`, `discard`, or `preserve-repo`; optional `workflows` must be a map. Record valid config as `status: ok`, `probe_kind: validation`, and a concise value naming provider/command/mode/artifact_root/artifact_retention/workflow override count plus Lavish plugin state guidance. Missing or disabled Lavish plugin state is graceful fallback guidance, not a config failure when shape is valid.
   - For `workflow_signals`, validate rather than emit a signal or invoke a sink. `mode` must be `off` or `auto`; `sinks` must be a list; v1 executable sink type is `tmux-glance`; unknown sink types are reserved warnings unless the shape is invalid; optional `skills` must be a map whose values are `off` or `auto`. Record valid config as `status: ok`, `probe_kind: validation`, and a concise value naming mode, sink count/types, skill override count, plus tmux-glance availability guidance. Missing `tmux-glance` is graceful fallback guidance, not a config failure when shape is valid.
   - For `babysit`, validate rather than invoke `/goal`, PR tooling, memento, or retro. Optional `goal.token_budget` must be a positive integer-like string with optional `k`/`m` suffix. Optional `loop.use_review_response` and `loop.run_configured_gates_before_push` must be booleans; `loop.wait_interval_seconds` and `loop.timeout_minutes` must be positive integers when present. Closeout modes must be `off`, `ask`, or `auto`; merge method must be `squash`, `merge`, `rebase`, or `repo-default`; `closeout.merge.delete_branch` must be boolean. Record valid config as `status: ok`, `probe_kind: validation`, and a concise value naming goal budget, loop behavior, and closeout modes. Note that `/goal` availability is checked by the runtime command, not doctor.
   - For `lifecycle_actions.events.<event>`, expand into event-scoped logical capabilities such as `lifecycle_actions.kickoff_start`, `lifecycle_actions.spec_approved`, `lifecycle_actions.blueprint_approved`, `lifecycle_actions.kickoff_context_ready`, and `lifecycle_actions.implementation_plan_created`.
     - P0 probes supported CLI actions for `kickoff_start`.
     - P0 validates artifact actions for `spec_approved`, `blueprint_approved`, `kickoff_context_ready`, and `implementation_plan_created` without touching the filesystem: `name` required; `approval` may be `prompt`, `auto`, or omitted; `path` may be omitted but, when present, must be a relative `.md` file template with no `..` segments and only placeholders documented for that event (`{feature}`, `{kind}`, `{ticket_id}` for planning artifacts; plus `{event}` for checkpoint artifacts). Artifact actions record `status: ok`, `probe_supported: true`, and a value such as `(auto/prompt artifact at runtime)`.
     - `review_feedback_loaded` and `ready_for_review_pre_submit` artifact actions are valid reserved checkpoint intent and should be narrated as reserved/not executed rather than invalid. Unsupported events/providers are noted as reserved and not executed.

   Record the result in the cache schema below.

5. **Parse failure.** If the YAML inside the fenced block doesn't parse, run `grep -n '^\`\`\`beislid:<key>' .beislid/workflow.md` to find the block start line, add the YAML parse-error offset within the block to compute the file line, and surface in prose:

   > ⚠️ The `beislid:<key>` block on line N doesn't parse as YAML — <one-line description of the parse error, e.g. "looks like a tab where there should be spaces.">

   Mark this capability as `status: failed`, `probe_supported: true`, `reason: "YAML parse error at line N: <details>"`. Continue probing other capabilities.

## 8. Detect paired-half-missing and soft pairs

For each hard paired set (today: `domain_expert.agent` ↔ `knowledge_store.path`), check whether exactly one half is configured. If so, surface in prose (non-blocking):

> ⚠️ `domain_expert.agent` is set but `knowledge_store.path` isn't — domain capture/recording steps will skip where they require the pair.

Both halves probed independently and recorded in the cache; no special status — the warning is purely narrative.

Also check gate soft constraints:

- When `gate_sets` is configured, narrate that it takes precedence over legacy `scopes` / top-level `gates`; if more than one model is present, warn that `scopes`/`gates` are fallback-only for older orchestrators.
- Legacy flat gates are valid even when they omit stage/cost/timeout metadata.
- `stage` values outside `preflight`, `per-edit`, `pre-commit`, `pre-pr`, `post-pr`, `continuous`, and `human-interrupt` are warnings.
- `kind` values other than absent/`sensor` are warnings for P0 gate execution; guide/feedforward artifacts are separate from gate lists.
- `execution` values outside `computational`, `inferential`, and `human` are warnings.
- `parallel_safe: true` on `mutates: true` gates is a warning because fast-path batching is only safe for read-only independent gates.
- Each `required_tools[]` entry is an additional CLI binary dependency; probe it with `command -v` alongside the gate command and report missing tools before the gate is treated as runnable.
- Rich `output.parser` and `failure` metadata is reported as declarative unless the current orchestrator has explicit support.

Also check lifecycle action soft constraints:

- `spec_approved`, `blueprint_approved`, `kickoff_context_ready`, and `implementation_plan_created` support only `type: artifact` in P0. Non-artifact actions under those events are reserved; warn that skills will skip them.
- Work Contract artifacts do not have a separate v1 config key; validate them as ordinary `spec_approved` or `blueprint_approved` artifact actions when workflows configure them.
- `review_feedback_loaded` and `ready_for_review_pre_submit` are reserved checkpoint artifact events; warn that no P0 skill executes them yet, but do not mark valid artifact action shape as failed.
- `artifact` actions under other unsupported events are reserved; warn that no skill executes them yet.
- `approval` omitted for artifact actions is valid and means `prompt`. `approval: auto` is valid and means create a missing target without prompting; existing targets still prompt at runtime.
- Doctor never creates artifact directories, files, or `.beislid/checkpoints/latest.json`; runtime skills own writes.

Also check action policy:

- `action_policy` is validation-only, not an external probe. Narrate the effective policy at a high level: configured modes, any stricter sandbox baseline than the built-in default, unknown/unclassified fallback decisions, and whether the known-action registry is available. Do not copy the full default table into doctor prose.
- Invalid action policy config is a failure, not a silent fallback. Name the invalid path/value and tell the user to fix `beislid:action_policy` or remove the override to use defaults.

Also check model routing:

- `model_routing` is validation-only; doctor does not spend model budget probing candidate availability. Narrate `prefer` routes as advisory and `require` routes as blocking only when a host adapter cannot honor any candidate at runtime.
- `model` and `models` are mutually exclusive; normalize `model` to a one-item list for summaries. Empty `models`, non-string candidates, unknown `mode`, missing override `skills`, or duplicate/empty skill names are failures.
- Portable aliases are `opus`, `sonnet`, `haiku`, `default`, and `host-default`. Namespaced provider strings are valid escape hatches; unknown bare strings should warn that host mapping may be unavailable.
- `when` is reserved for conditional routing and inactive in v1. Warn and tell the user to remove it or track the conditional-routing issue; do not let it narrow or activate a route.

Also check visual surfaces:

- `visual_surfaces` is validation-only; doctor does not deep-invoke Lavish or spend npm/network/cache by running the provider command. Invalid provider/command/mode/artifact_root/artifact_retention/workflow override shape is a config failure.
- Valid provider is `lavish-axi`. Valid modes are `off`, `suggest`, `prompt`, and `auto`; per-workflow overrides use the same enum. `artifact_root` must be repo-relative and cannot contain `..` segments. `artifact_retention` must be `local`, `discard`, or `preserve-repo`.
- Proactive visual routing requires repo config. User-level plugin enablement alone is not enough.
- Lavish plugin state is local guidance: missing or disabled state should mention graceful fallback and suggest `beislid plugin enable lavish` or `beislid plugin status lavish`; it should not make otherwise valid `visual_surfaces` config fail.

Also check workflow signals:

- `workflow_signals` is validation-only; doctor does not emit test signals, rename tmux windows, or invoke sinks. Invalid mode/sinks/skills shape is a config failure.
- Valid modes are `off` and `auto`. Valid v1 executable sink type is `tmux-glance`; future sink types are reserved and should be narrated as not executed by v1 skills. Skill override values use the same mode enum.
- Signal emission is best-effort and local. Missing `tmux-glance` or non-tmux sessions should be guidance, not a config failure. Recommend `beislid workflow-signal status` for a local status check.

Also check babysit policy:

- `babysit` is validation-only in doctor. Do not start `/goal`, check PR state, run gates, merge, capture memento, or run retro. Narrate `auto` closeout modes as still subject to action policy and runtime safety stops.
- A missing `babysit` block is valid; the skill defaults to conservative stop-when-green behavior with closeout disabled.

Also check ready-for-review final-review policy:

- `clean_eval.mode: off` is valid only as explicit project policy; narrate that the working-tree gate path remains in force. `clean_eval.mode: require` is a required clean-surface path that should classify failures as patch-regression versus environment/harness failure; `surface` and `artifact_root` are advisory policy values that must still validate.
- `fresh_eyes.enabled: false` is valid only as explicit project policy; narrate that the primary review still runs and final built-in fresh-eyes is disabled.
- `fresh_eyes.type: command` is a replacement for final fresh-eyes only; its first binary must probe ok before ready-for-review treats it as runnable.

Also check the PR review soft pair:

- `pr_review_source` alone is valid. Narrate it as read-only PR feedback handling; replies/re-request review will be manual if `pr_review_update` is absent or `type: manual`.
- `pr_review_update` without `pr_review_source` is a warning: update is configured without a source, so review-response can only use it after pasted PR feedback.
- `pr_review_source.type: paste` with `pr_review_update` configured is valid with a note: update is usable after pasted PR feedback.
- `pr_review_update.type: manual` is ok/no-probe; narrate it as manual-by-design, not missing.

## 9. Cache schema

Read `doctor-templates.md` for the canonical cache JSON example and field-level rules (status enum semantics, when `probe_supported: false` applies, when `value` and `reason` are omitted, etc.).

Always write the cache, including failures. Orchestrators need full state for lazy-probing decisions.

## 10. Write the cache

Marshal the schema to JSON and write to `<state_dir>/probes/<repo_hash>.json`. Overwrite atomically if possible.

If the write fails (permissions, disk full, etc.), surface in prose with the path:

> ⚠️ Couldn't write the probe cache to `<path>`: <error>. The audit ran fine, but orchestrators won't see the cached results until you fix the underlying issue.

Continue to step 11 — the audit narration is still useful even without a cache write.

## 11. Print the conversational audit

Default mode (no `BEISLID_VERBOSE`) emits prose narration. Char budgets:

- **Success path:** ≤500 chars total.
- **Failure path:** ≤700 chars total. Use the **three-clause shape**: name what's wrong → name what's still working → name what to do.

Open with `🩺 **Workflow check on `<project_name>`.**` then narrate what's configured, what was probed, and the cache status. Keep it conversational — no tables, no fixed-width columns, no checkmark grids.

Read `doctor-templates.md` for doctor's success and failure templates (worked examples). The three-clause failure shape (the rule), the 12-emoji palette, and the rules for placing inline `⚠️` and `💭` notes inside the narration come from `output-templates.md`.

## 12. Verbose mode

When `BEISLID_VERBOSE=1` is set in the environment, append structured stamps under the prose, separated by `---`. Stamps are diagnostic, not narrative.

Read `output-templates.md` for the universal verbose-stamps layout rule (`---` divider; "augment, don't replace"). Read `doctor-templates.md` for doctor's per-capability stamp layout and the stamp-symbol legend (`✓` / `✗` / `—`). Verbose mode is gated entirely on the env var; default mode shows only the prose, never the stamps.

---

## Common mistakes

- **Treating staged rich gates as invalid because old gates were flat.** `command` gates are shorthand and remain valid; staged metadata is additive.
- **Treating `gate_sets` as a replacement for gate normalization.** Gate sets select candidate gates by changed files; normal stage/kind/execution/command/tool checks still decide what P0 can execute.
- **Treating `pr_review_source`/`pr_review_update` as unknown keys.** They are Phase 3 workflow.md keys. Source-only is valid; update-only is a warning; manual/paste variants are configured no-op probes.
- **Writing a cache file before validation completes.** All hard-fail conditions (missing workflow.md, missing git repo, version mismatch, broken aux symlinks) exit before any cache write.
- **Using line numbers from Read tool output.** That formatting differs across hosts. Always compute line numbers via `grep -n '^\`\`\`beislid:' .beislid/workflow.md` plus the YAML parse offset.
- **Re-probing inside the same run.** Each capability is probed once per `/doctor` invocation. Stale cache invalidates the whole file; doctor doesn't reprobe per-capability mid-flight.
- **Silently using a different repo-hash on multi-root histories.** `git rev-list --max-parents=0 HEAD` without `sort` gives non-deterministic order across runs. Always pipe through `sort` before truncating.
- **Skipping the version-stamp check.** Doctor never silently mis-parses an unknown workflow.md version.

## Key principles

- **Read-only on workflow.md, write-only on cache.** Doctor never edits the user's config.
- **Conversational over CI-style.** Prose narration with the 12-emoji palette. No tables or fixed-width columns in default mode.
- **Hard-fail loudly when assumptions break.** No git repo, no commits, no workflow.md, broken aux symlinks, unknown version stamp — all stop with a clear pointer to the fix.
- **Verbose mode adds, never replaces.** Stamps go under the prose, separated by `---`. Default-mode users never see them.
