# ready-for-review phase 1 detect v1

Loaded just in time at Phase 1 entry. If unreadable, hard-fail instead of running from memory.

## Entry / exit output

Print entry/exit one-liners; emit workflow-signal `working`; verbose appends aux/transcript stamps.

## Phase outputs

Populate run context: ticket/branch/base/PR, diff files/stats, gate model, optional triggers, freshness/merge state, AgenticReviewer risk/opt-in decision, clean-eval, fast-path, warnings/risks. Expose `existing_pr_fast_path` early enough for orientation output.

## Procedure

### 1a. Branch, ticket, and default-branch safety

Run `git branch --show-current` and store `branch`.

Ticket association is explicit-only:

- If `branch_pattern` captures an id, store it; normalize against `ticket_source.id_pattern` when configured.
- If the user already said no ticket / maintenance / `none`, store `ticket_id = none` and do not ask again.
- Otherwise emit workflow-signal `waiting`, then ask: `What is the ticket ID? Reply with an ID, or \`none\` for maintenance/no-ticket work.`
- Do not list/search open issues to guess. Only use a ticket id after branch/user confirmation.

Determine `base` from `pr_base.default` when configured, otherwise `main`; if a stacked/non-default base is likely, ask.

If `branch == base` or default branch with local changes, emit `blocked`, stop before gates/push, show `git status --short`, explain direct PR handoff from base is unsafe, then ask for branch name and include set (`all`, selected paths, or abort). Selected paths require exact confirmation and commit message; untracked files are excluded unless named. If no local changes/diff, stop: nothing to review.

On feature branches, warn uncommitted files are excluded unless committed; if there are changes but no commits, warn tree uncommitted.

### 1b. Check for existing PR

Run:

```bash
gh pr view --json url,baseRefName,headRefName 2>/dev/null
```

If a PR exists, enter fast-path: record `existing_pr_fast_path = true`, `pr_url`, and `base` from `baseRefName`; keep Phase 2, then push/report after gates and skip Phases 3/4. Split policy warns.

### 1c. Categorize changes

Run:

```bash
git diff <base>...HEAD --name-only
git diff <base>...HEAD --shortstat
```

Store files/stats. If the diff touches `skills/**` or `.beislid/**`, emit the skill-change warning.

If `review_policy.agentic_reviewer.mode: opt_in_final_review`, classify risk: `high` for high path/threshold match; `low` only when every file is low-risk and low thresholds hold; else `medium` (unknown stats cannot be low). Store `agentic_reviewer_required = risk > max_auto_closeout_risk` using `low < medium < high`. Missing policy preserves old behavior.

`probe(crust_seam)`; if ok, select gates via `crust gates select --stage pre_pr --changed-files <files> --json` (`crust-seam-protocol.md`) and use its `selected`/`skipped`. Else if `gate_sets` exists, match selectors to changed files, apply `exclude`, union deterministically, de-dupe by gate identity, and record selected/skipped reasons. Else mark touched scopes; else create repo-root scope for top-level `gates`; else no gate scopes.

### 1d. Apply split policy

Skip when `split_policy` is absent or only one scope is touched. If `split_policy: exclusive` and 2+ scopes are touched, set `split_policy_violation=true`, block before Phase 2, and ask the user to split; on existing-PR fast path, warn and continue. Do not auto-split.

### 1e. Detect triggered skills

Set `translation_sync_triggered` / `browser_compat_triggered` by pure path matching against configured trigger paths. Do not probe optional skills in Phase 1.

### 1f. Mandatory-attempt stale check

Attempt:

```bash
git fetch origin <base>
git rev-list --count HEAD..origin/<base>
```

Do not infer freshness from session context. If fetch/check fails, ask retry / proceed unknown / abort. Unknown sets `freshness=unknown`, `needs_merge=false`, and carries a warning. Behind count >0 sets `freshness=behind`, `needs_merge=true`, and warns Phase 2 owns merge/rebase. Zero means `fresh`.

### 1g. Fast-path eligibility

Fast-path is for small, low-risk new PRs. Set `fast_path_eligible=true` only when all are true:

- not `existing_pr_fast_path`
- changed lines (additions + deletions from `--shortstat`) are known and ≤100
- one touched scope/repo-root, or `gate_sets` where all selected executable gates are parallel-safe and no-fix (crust-selected gates carry no `parallel_safe`/`mutates` metadata — read that from workflow.md's own gate objects, not the crust selection response, per the carve-out in `crust-seam-protocol.md`)
- no split-policy violation
- `freshness=fresh` and `needs_merge=false`

Otherwise set false and record the first reason. Fast-path changes only pacing: preloaded aux, safe parallel gates, combined review. It never skips gates, blocking-finding handling, reduced-coverage acceptance, or PR approval.

## Phase-local tripwires

- No ticket guessing: confirmed id or `none` only.
- Never push/create PR directly from the default/base branch.
- Stale check is mandatory; unknown freshness is not green.
- Unknown diff size, multi-scope work, split violations, or stale base disable fast path.
