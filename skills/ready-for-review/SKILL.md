---
name: ready-for-review
description: >
  Use when the user says "ready-for-review", "ready for review", "prepare for review", or "finalize for review", or when completed work is explicitly ready for PR review handoff. Bookend to kickoff: gates, review, fresh-eyes, and PR creation/update. Do NOT use for mid-implementation commits or unfinished work. Reads workflow.md and probes capabilities lazily.
---

# Ready for Review

Take a completed branch through gates, review, fresh-eyes, and PR creation. Existing PR updates: gates, push, report URL. Small safe new PRs use fast-path: preload aux, parallel safe gates, combined review/fresh-eyes.

**Don't use this for:** mid-implementation commits, experimental branches without tickets, or work that isn't ready for review.

Project config lives at `<repo>/.beislid/workflow.md` (typed-key fenced YAML blocks; format reference at `workflow-md-format.md`). Capabilities are probed lazily on first need. Output prose follows `output-templates.md` and `ready-for-review-templates.md`.

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

Read `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/<repo_hash>.json` if present. Missing means `cold`; workflow hash mismatch means `stale` and starts with empty in-memory state; matching hash means `fresh` and loads capability entries. Per-cap freshness uses `cache_ttl_hours` from workflow.md, default 24.

Initialize the verbose transcript immediately after config/cache setup if `BEISLID_VERBOSE=1`, then load Phase 1 and record its aux-load/entry events. Print the orientation prose from `ready-for-review-templates.md` once after Phase 1 has established branch, base, and fast-path status, so the existing-PR suffix is accurate.

## Internal: probe(<cap>)

Probe capabilities lazily on first use. The in-memory probe state is authoritative for the run; do not re-probe a capability mid-run unless the user chose retry from a probe-failure prompt.

Algorithm:
1. If `<cap>` exists in memory with `status: ok` and is within TTL, return ok.
2. Otherwise probe using `probe-semantics.md` for the cap kind.
3. On success, record the result in memory and continue.
4. On failure, use the call-site-specific 3-way prompt from `ready-for-review-templates.md` or the active phase aux file: retry re-probes now; proceed-this-session records `session_skip: true` and continues without that capability; abort stops immediately and suppresses cache write-back.
5. On successful run end, write back probed/re-probed entries except `session_skip`.

Rules: never silently downgrade a configured capability to unconfigured behavior; never re-probe outside explicit retry; preserve `doctor_run_at` because doctor owns it; last-writer-wins is acceptable for v0.2.

## Global tripwires

- No legacy YAML fallback; `.beislid/workflow.md` is the only project config source.
- Do not execute a phase from memory if its aux file cannot be read.
- Do not write probe cache on abort or after workflow hash changed mid-run.
- Status prose is not a prompt. After green preflights/gates, continue unless a listed hard gate, failure, ambiguity, or approval is reached.
- At hard approval boundaries, ask the blocking approval question once; commentary may give context/drafts, not repeat it.
- No-ticket PR handoff must be explicit (`ticket_id = none`); never infer issues from open issue lists.
- Never push/create a PR from the default/base branch; Phase 1 branches/commits approved paths first.
- Do not commit, push, create a PR, or mark a draft ready without the existing user-approval gates.
- Fast-path mode never bypasses gates, blocking review handling, reduced-coverage acceptance, or PR approval.
- PR creation must run from explicit repo cwd and pass `--head <branch>`.

## Phase protocol loading

Complete phases in order. At each phase entry, read the phase aux file and follow it as authoritative. Phase exit lines are progress reports, not checkpoints. If `fast_path_eligible=true`, preload Phase 2/3/4 aux before Phase 2. Do not execute a phase from memory if aux read fails; hard-fail and stop:

> 🛑 Could not read `skills/ready-for-review/<phase-file>.md`. Ready-for-review cannot safely execute this phase from memory; reinstall Beislið or restore the file.

When `BEISLID_VERBOSE=1`, emit the aux load stamp from `ready-for-review-templates.md`, append the transcript boundary, and include loaded/not-reached aux files at run end.

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
- stale base merged or explicitly blocked on conflicts
- applicable gates run by touched scope or top-level config
- autofix diffs shown and committed only with user approval
- non-autofix failures surfaced for user direction
- translation/browser checks run or skipped per trigger/config
- guided walkthrough offered when thresholds are met and handled per user choice
- any reviewer warnings such as AI-generated translations carried forward

Exit: print the Phase 2 exit one-liner from `ready-for-review-templates.md`. If this is the existing-PR fast path, push to the PR branch, print the fast-path success line, then proceed to run-end cache/memory handling.

## Phase 3: Review

Skip on existing-PR fast path. Otherwise read and follow `phase-3-review.md`.

Inputs: Phase 2 results, full diff against `base`, ticket/spec/design context, verification already run, and reviewer warnings.

Required outputs:
- normal `review` pass, or fast-path combined review, completed; or cancelled/incomplete coverage explicitly accepted as reduced-coverage risk
- Critical findings fixed; Important findings fixed unless user explicitly accepts risk
- incorrect findings pushed back with code/test evidence
- applicable gates rerun after functional fixes
- `fresh-eyes` final pass completed, or fast-path combined review completed, with no blocking findings/accepted risk

Exit: print the Phase 3 exit one-liner from `ready-for-review-templates.md`.

## Phase 4: Submit

Skip on existing-PR fast path. Otherwise read and follow `phase-4-submit.md`.

Inputs: Phase 3 result and review mode, ticket ID, base, branch, diff summary, reviewer warnings, and configured PR handoff/memory capabilities.

Required outputs:
- domain capture paired-set front-loaded before side effects
- ticket title fetched/pasted, or `ticket_id=none` recorded as no issue
- PR title/body drafted, optionally formatted, shown to the user, and explicitly approved
- optional draft-bot-review path handled when supported and accepted
- branch pushed and PR created only after approval
- domain knowledge capture considered
- structured memento/session-memory brief attempted when enabled/detected

Exit: print the Phase 4 PR success and exit one-liners from `ready-for-review-templates.md`.

## Run end: write back probe cache

After Phase 4 or fast-path push/report, write in-memory probe state to `<repo_hash>.json`: update probed/re-probed entries, exclude `session_skip: true`, preserve `doctor_run_at`, update `workflow_hash`, and keep the workflow TTL. If `workflow.md` changed mid-run, do not overwrite stale state. If write fails, surface the template warning; the run still completed. On abort after Phase 2 starts or any side effect, skip cache write-back unless safe, but still attempt/print the structured brief with `phase_path: aborted`.

## Verbose transcript and memory brief

Default mode prints only prose. With `BEISLID_VERBOSE=1`, append structured stamps under prose, persist a best-effort local transcript at major boundaries, and print the transcript path if written. Read `ready-for-review-templates.md` for exact stamp layout, transcript boundary/redaction rules, write-failure behavior, and loaded/not-reached summary.

`BEISLID_MEMENTO_CAPTURE` is independent from verbose mode. Generic auto-capture does not satisfy ready-for-review memory. Before final run-end output, write exactly one memory marker to transcript/output: `kind: ready-for-review-session-memory-v1` with the brief, or `memory brief unavailable:<reason>`. The brief includes PR/ticket links or `none`, loaded aux, transcript path/unavailable reason, gates, review status, risks, side effects, host/duration, and summary.

Cross-host protocol changes should use `tests/agent-smoke/` when practical.
