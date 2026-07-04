---
name: ready-for-review
description: >
  Use when the user says "ready-for-review", "ready for review", "prepare for review", or "finalize for review", or when work is ready for PR review handoff. Bookend to kickoff: gates, review, final check, and PR handoff. Do NOT use for mid-implementation commits or unfinished work. Reads workflow.md and probes capabilities lazily.
---

# Ready for Review

Take a branch through gates, review, and PR creation. See [worktree isolation](../../docs/worktree-isolation.md). Existing PR updates: gates, push, report URL. Small new PRs use fast-path: preload aux, parallel-safe gates, combined review/final-check.

**Don't use this for:** mid-implementation commits, experimental branches without tickets, or work that isn't ready for review.

Project config: `<repo>/.beislid/workflow.md`. Use `action-policy-protocol.md` before side effects. Output follows `output-templates.md` and `ready-for-review-templates.md`.

Honor `../lifecycle-hooks.md` before and after this phase.

---

## Load project config

Read `<repo>/.beislid/workflow.md`. If it doesn't exist, hard-fail and stop:

> 🛑 No `workflow.md` found in `.beislid/`. If this is a fresh project, run `/setup` to create one. If you moved your config, restore it to `<repo>/.beislid/workflow.md`.

Validate line 1 is `<!-- beislid-workflow: v1 -->`. If missing or different, hard-fail and stop:

> ⚠️ This `workflow.md` is `<found>` but ready-for-review only knows `v1`. Update Beislið (current version is X.Y) or downgrade `workflow.md` by hand to v1 syntax. Ready-for-review will not silently mis-parse.

Compute cache identifiers with the same recipes doctor uses:

```bash
repo_hash=$(git rev-list --max-parents=0 HEAD | sort | head -c 12)
workflow_hash=$(git hash-object .beislid/workflow.md)
```

Read `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/<repo_hash>.json` if present. Missing means `cold`; workflow hash mismatch means `stale` (start with empty in-memory state); matching hash means `fresh` (load capability entries). Per-cap freshness uses `probe_cache.ttl_hours`, default 24.

After config/cache setup, init transcript and `beislid run-ledger init --skill ready-for-review`. Record events, and if active checkpoint with `beislid run-ledger checkpoint --run-id <run_id> --name <phase_name>`. Ledger and `workflow-signal` calls are best-effort: warn and continue on missing `beislid` CLI or failure; never replace approvals, transcript, or memory marker. Then load Phase 1 and print orientation after branch/base/fast-path are known.

## Internal: probe(<cap>)

Probe capabilities lazily on first use. The in-memory probe state is authoritative for the run; do not re-probe mid-run unless the user chose retry from a probe-failure prompt.

Algorithm:
1. If `<cap>` exists in memory with `status: ok` and is within TTL, return ok.
2. Otherwise probe using `probe-semantics.md` for the cap kind.
3. On success, record the result in memory and continue.
4. On failure, use the call-site-specific 3-way prompt from `ready-for-review-templates.md` or the active phase aux file: retry re-probes now; proceed-this-session records `session_skip: true` and continues without it; abort stops immediately and suppresses cache write-back.
5. On successful run end, write back probed/re-probed entries except `session_skip`.

Rules: never silently downgrade a configured capability to unconfigured behavior; never re-probe outside explicit retry; preserve `doctor_run_at` because doctor owns it; last-writer-wins is acceptable for v0.2.

`workflow-signal` shorthand means `beislid workflow-signal emit <state> --skill ready-for-review --phase <phase>`.

## Global tripwires

- No legacy YAML fallback; `.beislid/workflow.md` is the only project config source.
- Do not execute a phase from memory if its aux file cannot be read.
- Do not write probe cache on abort or after workflow hash changed mid-run.
- Status prose is not a prompt. After green preflights/gates, continue unless a listed hard gate, failure, ambiguity, or approval is reached.
- At hard approval boundaries, keep commentary context-only; ask the blocking approval question once in the final response.
- No-ticket PR handoff must be explicit (`ticket_id = none`); never infer issues from open issue lists.
- Never push/create a PR from the default/base branch; Phase 1 branches/commits approved paths first.
- Do not commit, push, create a PR, or mark a draft ready without the existing user-approval gates.
- Covered side effects require action-policy evaluation; `ask` needs approval, `deny` stops.
- Fast-path mode never bypasses gates, blocking review handling, reduced-coverage acceptance, policy, or PR approval.
- PR creation must run from explicit repo cwd and pass `--head <branch>`.
- Run-ledger resume hints return only to safe protocol boundaries; ask normal approvals again.

## Phase protocol loading

Complete phases in order. At each entry, read the phase aux and follow it. Phase exits are progress reports; if a ledger is active, also checkpoint safe summary, artifacts, side effects, and `resume_hint`. If `fast_path_eligible=true`, preload Phase 2/3/4 aux before Phase 2. Do not execute from memory if aux read fails; stop:

> 🛑 Could not read `skills/ready-for-review/<phase-file>.md`. Ready-for-review cannot safely execute this phase from memory; reinstall Beislið or restore the file.

Read `action-policy-protocol.md` before Phase 2 side effects. Verbose mode emits aux stamps/transcript boundaries and loaded/not-reached aux files.

## Phase 1: Detect

Read and follow `phase-1-detect.md`.

Inputs: workflow config, branch name, probe cache state, current git state.

Required outputs:
- `ticket_id` (from `branch_pattern`, explicit user prompt, or `none`)
- `branch`, `base`, `existing_pr_fast_path`, and `pr_url` when present
- changed file count/line summary and touched scopes or implicit top-level gate scope
- split-policy decision or warning
- trigger booleans for `translation_sync` and `browser_compat`
- `freshness` (`fresh`, `behind`, or `unknown`), `needs_merge`, stale-check warnings/accepted risk
- `fast_path_eligible` plus reason when false

Exit: print the Phase 1 exit one-liner from `ready-for-review-templates.md`. If `existing_pr_fast_path=true`, finish Phase 2 then push/report via the fast-path line and skip Phases 3 and 4.

## Phase 2: Quality gates

Read and follow `phase-2-gates.md`.

Inputs: Phase 1 outputs, configured scopes/gates, trigger booleans, `needs_merge`, existing-PR fast-path state, and small-diff fast-path eligibility.

Required outputs:
- stale base merge handled
- applicable gates run; proof status reported and required proof blocked/interrupted per policy
- autofix diffs handled with approval
- non-autofix failures surfaced
- translation/browser checks handled
- guided walkthrough handled when threshold met
- reviewer warnings carried forward
- ledger gate artifact paths, if active

Exit: print the Phase 2 exit one-liner. Existing-PR fast path: push, apply required AgenticReviewer opt-in label after policy, report URL, then run-end cache/memory.

## Phase 3: Review

Skip on existing-PR fast path. Otherwise read and follow `phase-3-review.md`.

Inputs: Phase 2 results, full diff against `base`, ticket/spec/design context, verification already run, and reviewer warnings.

Required outputs:
- normal `review` pass, or fast-path combined review, completed; or cancelled/incomplete coverage explicitly accepted as reduced-coverage risk
- Critical findings fixed; Important findings fixed unless user explicitly accepts risk
- incorrect findings pushed back with code/test evidence
- applicable gates rerun after functional fixes
- configured final check completed, disabled by policy, or fast-path combined review completed with no blockers/accepted risk
- ledger review/final-check artifact paths, if active

Exit: print the Phase 3 exit one-liner from `ready-for-review-templates.md`.

## Phase 4: Submit

Skip on existing-PR fast path. Otherwise read and follow `phase-4-submit.md`.

Inputs: Phase 3 result, review mode, proof status, ticket ID, base, branch, diff summary, reviewer warnings, and PR handoff/memory capabilities.

Required outputs:
- domain capture paired-set front-loaded before side effects
- ticket title fetched/pasted, or `ticket_id=none` recorded as no issue
- PR title/body drafted, optionally formatted, shown to the user, and explicitly approved
- optional draft-bot-review path handled when supported and accepted
- branch pushed/PR created only after policy and approval
- domain knowledge capture considered
- structured memento/session-memory brief attempted when enabled/detected
- ledger finalized with PR URL, risks, side effects, artifacts, and memory status if active

Exit: print the Phase 4 PR success and exit one-liners from `ready-for-review-templates.md`.

## Run end: write back probe cache

After Phase 4 or fast-path push/report, write in-memory probe state to `<repo_hash>.json`: update probed entries, exclude `session_skip`, preserve `doctor_run_at`, update `workflow_hash`, and keep TTL. If `workflow.md` changed mid-run, do not overwrite. If write fails, warn; the run still completed. On abort after Phase 2 or any side effect, skip cache write-back unless safe, but still print the structured brief with `phase_path: aborted`.

## Verbose transcript and memory brief

Default mode prints prose only. With `BEISLID_VERBOSE=1`, append structured stamps, persist a best-effort transcript, and print its path. See `ready-for-review-templates.md` for stamp/redaction/write-failure details.

`BEISLID_MEMENTO_CAPTURE` is independent from verbose mode. Before final output, write exactly one marker: `kind: ready-for-review-session-memory-v1` with the brief, or `memory brief unavailable:<reason>`. Include PR/ticket, aux, transcript, gates, review, risks, side effects, host/duration, and summary.

Cross-host protocol changes should use `tests/agent-smoke/` when practical.
