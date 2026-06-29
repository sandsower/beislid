# ready-for-review phase 2 gates v1

Loaded just in time after Phase 1. If this file cannot be read, hard-fail; do not reconstruct Phase 2 from memory.

## Inputs / outputs

Inputs: base/branch/ticket/PR, merge/diff state, gate model, configured gates, optional triggers, notes/warnings.

Outputs: gate envelopes, clean-eval proof status + `clean_eval.surface`, logs/artifacts, skips, decisions, warnings, and resume route.

Print Phase 2 entry/exit. Emit workflow-signal `verify` at Phase 2 entry. Verbose mode emits aux/probe/gate summaries.

## 2a. Merge base if stale

If `needs_merge`, policy-check `git.merge` (`workspace-write`, `git-local`) and merge only on `allow`/approved `ask`:

```bash
git merge origin/<base>
```

If conflicts occur, emit workflow-signal `blocked`, then stop and ask the user for help. After resolution, continue Phase 2 and run gates that apply to touched files; merged code may violate current rules.

## 2b. Run scoped or top-level gates

Run applicable checks in order and fail fast; fast-path may parallelize safe gates after probing.

Selection:

- `gate_sets`: run Phase 1 selected gates with set defaults.
- `scopes`: run scope `setup` before pre-pr gates (`pushd <cwd>`, `popd`). `setup` blocks gates.
- top-level `gates`: run pre-pr gates from repo root.
- none: `no gates configured — skipping`.

Flat `name`+`command` = pre-pr sensor. Execute legacy + rich gates where stage is absent/`pre-pr`, kind is absent/`sensor`, command exists, execution is absent/`computational`. Other stages → `skipped-by-stage`; non-computational/non-sensor pre-pr → `skipped-by-execution`. Rich `output`/`failure` as prompt context.

Probe each selected gate once (`probe(gate_sets.sets.<set>.gates[<gate>].command)`, scope, or top-level equivalent), plus `required_tools[]` via `command -v`. On failure, use the Phase 2b prompt.

Execution:

1. If `fast_path_eligible=true`, batch only gates with `parallel_safe: true`, no `autofix`, and `mutates` not true. Run concurrently when supported; otherwise run sequentially and record `parallel_unavailable`.
2. Run non-batched gates once in configured order. Normal mode treats every selected gate as non-batched.
3. For each run, capture duration and parse stdout/stderr into the shared Gate result envelope from `output-templates.md`. Store raw logs by path when possible, else a safe summary.
4. Autofix when `fail` and not environment: if `approval_gates.autofix_commit` is `auto`, policy-check `gate.autofix`, record diff to transcript/ledger, commit without prompt (unless action policy denies). Else policy-check `gate.autofix`, show diff as context, and ask the approval question once in the final blocking response.
5. For `error`, environment failure, or no autofix: emit `waiting`. If `approval_gates.gate_failure` is `auto` and not environment: record failure envelope to transcript/ledger with `auto-accept-risk`, continue. Else prompt from envelope + context in the final blocking response. Surface all failure envelopes together.
6. Re-run applicable gate after fixes. User proceed-without-passing (or auto accept-risk) → record.

Probe/cache rule: first use of a configured gate, ticket source, formatter, domain/memory hook, or PR-provider capability updates run-memory probe state. Plain git checks are not probe-cache entries.

Track envelopes, skips/reasons, proof status, gate model, duration, autofix, probes, metadata, exceptions. Phase exits only after required proof is satisfied or handled by `failure_policy`.

## 2c. Translation sync

If Phase 1 did not trigger `translation_sync`, print the not-triggered skip line from `ready-for-review-templates.md` and skip.

If `translation_sync.skill` is not configured, print the disabled inline note from `ready-for-review-templates.md` and skip.

Otherwise probe `translation_sync.skill`, invoke the configured skill, and policy-check any translation edits before committing. Carry AI-generated user-facing-content warnings to Phase 4.

## 2d. Browser compatibility check

If Phase 1 did not trigger `browser_compat`, print the not-triggered skip line from `ready-for-review-templates.md` and skip.

If `browser_compat.skill` is not configured, print the disabled inline note from `ready-for-review-templates.md` and skip.

Otherwise probe `browser_compat.skill` and invoke the configured skill with the diff. Browser compatibility is advisory and does not block PR handoff by itself.

## Clean evaluator

If `clean_eval` is absent or `mode: off`, print the clean-evaluator skip line from `ready-for-review-templates.md` and continue.

If `clean_eval.mode: require`, honor `surface` (auto/worktree/container): reuse matching surface, or create from branch+base, apply patch, run selected pre-pr gates, store artifacts under `artifact_root` or run-ledger tree, classify failures as `patch-regression` or `environment_failure`. On failure: `blocked` for patch regressions, `waiting`/`blocked` for environment. If `approval_gates.clean_eval_failure` is `auto`, record to transcript/ledger with `auto-skip`, continue (patch regressions still block). Else stop unless user accepts retry/skip.

## Phase 2b: Guided walkthrough

Run this conditional subsection after quality gates and before Phase 3 review, including on the existing-PR fast path.

Count the diff size:

```bash
git diff <base>...HEAD --shortstat
```

Use `guided_walkthrough.threshold_files` / `threshold_lines` when configured; defaults are 5 files and 200 lines. If files or lines changed meets/exceeds threshold, print the Phase 2b entry one-liner and offer:

> This touches N files across [areas]. Want to do a guided walkthrough before code review?

Options: `Skip — go straight to review` (recommended for most cases) or `Yes, walk me through it`. Below threshold, skip silently.

If the user skips, print the skipped line. If accepted, invoke `walk-the-diff`; when it wraps, fix surfaced issues, re-run applicable gates, then print done with issue count.

Resume behavior:

- Normal new-PR path: continue to Phase 3.
- Existing-PR fast path: do not enter Phase 3; push and report the existing PR URL.

If the user explicitly asks for a durable visual proof/review artifact, suggest `show-me` and wait for direct request. Do not auto-run `show-me`.

## Phase-local tripwires

- Run only applicable gates: `gate_sets` selection when configured, otherwise touched scopes when scoped, otherwise top-level gates only when scopes are absent.
- Fast-path parallelism requires `parallel_safe: true`; absence of `autofix` alone is not enough, and `mutates: true` gates are never parallel candidates.
- Only configured `autofix` commands may run after policy; other failures need user direction.
- Clean evaluator is policy-driven: `mode: off` skips it; `mode: require` must run a clean surface and classify failures instead of silently falling back to the working tree.
- Walkthrough is optional and `show-me` requires an explicit user request; neither is an automatic blocker.
