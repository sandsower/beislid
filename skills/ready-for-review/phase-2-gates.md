# ready-for-review phase 2 gates v1

Loaded just in time after Phase 1. If this file cannot be read, hard-fail; do not reconstruct Phase 2 from memory.

## Inputs / outputs

Inputs: base/branch/ticket/PR, merge/diff state, gate model (`gate_sets`/scopes/repo-root), configured gates, optional triggered skills/walkthrough, notes/warnings.

Outputs: gate envelopes, status/duration/count, autofix count, user decisions, fast-path parallel status, new commits/changes, reviewer warnings, browser advisory result, walkthrough result, and resume route.

Print Phase 2 entry/exit one-liners. Verbose mode emits aux/probe/gate summaries.

## 2a. Merge base if stale

If `needs_merge`, policy-check `git.merge` (`workspace-write`, `git-local`) and merge only on `allow`/approved `ask`:

```bash
git merge origin/<base>
```

If conflicts occur, stop and ask the user for help. After resolution, continue Phase 2 and run gates that apply to touched files; merged code may violate current rules.

## 2b. Run scoped or top-level gates

Run applicable checks in order and fail fast; fast-path may parallelize safe gates after probing. Selection is config-driven:

- `gate_sets`: run Phase 1 selected gates. Apply set `cwd`/`stage` defaults before normalization; gate fields win. Preserve order, de-dupe, and record reasons.
- `scopes`: run touched scopes only (`pushd <scope.cwd>`, executable pre-pr gates, `popd`).
- top-level `gates`: run executable pre-pr gates from repo root.
- none: print `no gates configured — skipping`.

Normalize per `workflow-md-format.md`: flat `name`+`command` means pre-pr computational sensor. P0 ready-for-review executes legacy gates plus rich gates where `stage` is absent/`pre-pr`, `kind` is absent/`sensor`, `command` exists, and `execution` is absent/`computational`. Record other stages as `skipped-by-stage`; record pre-pr non-computational/non-sensor as `skipped-by-execution`. Treat rich `output`/`failure` as prompt context.

Probe each selected gate once (`probe(gate_sets.sets.<set>.gates[<gate>].command)`, scope, or top-level equivalent), plus `required_tools[]` via `command -v`. On failure, use the Phase 2b prompt.

Execution:

1. If `fast_path_eligible=true`, batch only gates with `parallel_safe: true`, no `autofix`, and `mutates` not true. Run concurrently when supported; otherwise run sequentially and record `parallel_unavailable`.
2. Run non-batched gates once in configured order. Normal mode treats every selected gate as non-batched.
3. For each run, capture duration and parse stdout/stderr into the shared Gate result envelope from `output-templates.md` (pytest parser when pytest-like, otherwise generic). Store raw logs by path when possible, else a safe summary.
4. Autofix only when `fail` and not environment failure: policy-check `gate.autofix` (`workspace-write` plus non-read classes), show summary, run on `allow`/approved `ask`, show diff, ask before commit. Ask the commit approval question exactly once in user-visible output; do not duplicate it across progress prose and the final/blocking response.
5. For `status: error`, `environment_failure: true`, or no `autofix`, prompt from the envelope (`summary`, failures, flags, action, raw-log reference) plus configured `failure.*` / `output.parser` context. Do not guess. In parallel, wait for siblings and surface all failure envelopes together.
6. After a fix, re-run the applicable gate before advancing. If the user explicitly proceeds without a passing gate, record that decision/risk.

Probe/cache rule: first use of a configured gate, ticket source, formatter, domain/memory hook, or PR-provider capability updates run-memory probe state for cache write-back. Plain git checks are not probe-cache entries.

Track envelopes, skipped counts/reasons, gate model/areas, duration, autofix count, parallel mode, probe/cache updates, rich metadata, and approved exceptions.

## 2c. Translation sync

If Phase 1 did not trigger `translation_sync`, print the not-triggered skip line from `ready-for-review-templates.md` and skip.

If `translation_sync.skill` is not configured, print the disabled inline note from `ready-for-review-templates.md` and skip.

Otherwise:

1. `probe(translation_sync.skill)`. On failure, use the Phase 2c prompt from `ready-for-review-templates.md`.
2. If probe resolves, invoke the configured skill via the host agent's skill mechanism. The skill owns pull/push cycles and may commit translation files.
3. If translation edits result, policy-check `git.commit` (`workspace-write`, `git-local`), then ask before committing.

If the invoked skill reports machine- or AI-generated user-facing content, carry that warning to Phase 4. Do not silently pass AI-authored translations/localized copy to reviewers.

## 2d. Browser compatibility check

If Phase 1 did not trigger `browser_compat`, print the not-triggered skip line from `ready-for-review-templates.md` and skip.

If `browser_compat.skill` is not configured, print the disabled inline note from `ready-for-review-templates.md` and skip.

Otherwise:

1. `probe(browser_compat.skill)`. On failure, use the Phase 2d prompt from `ready-for-review-templates.md`.
2. If probe resolves, invoke the configured skill with the diff.

Browser compatibility is advisory and does not block PR handoff by itself.

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
- Walkthrough is optional and `show-me` requires an explicit user request; neither is an automatic blocker.
