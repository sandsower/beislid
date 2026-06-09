# ready-for-review phase 1 detect v1

Loaded just in time at Phase 1 entry. If unreadable, hard-fail instead of running from memory.

## Entry / exit output

Print Phase 1 entry/exit one-liners; emit workflow-signal `working` on entry. In verbose mode, append aux-load/transcript boundaries and ensure transcript is initialized or warning recorded before exit.

## Phase outputs

Populate run context: ticket/branch/base/PR, diff files/stats, gate model (`gate_sets`/scopes/repo-root) with selected/skipped reasons, optional triggers, freshness/merge state, fast-path eligibility, warnings/risks.

Expose `existing_pr_fast_path` early enough for orientation output to append the fast-path clause.

## Procedure

### 1a. Branch, ticket, and default-branch safety

Run `git branch --show-current` and store `branch`.

Ticket association is explicit-only:

- If `branch_pattern` captures an id, store it; normalize against `ticket_source.id_pattern` when configured.
- If the user already said no ticket / maintenance / `none`, store `ticket_id = none` and do not ask again.
- Otherwise emit workflow-signal `waiting`, then ask: `What is the ticket ID? Reply with an ID, or \`none\` for maintenance/no-ticket work.`
- Do not list/search open issues to guess. Only use a ticket id after branch/user confirmation.

Determine `base` from `pr_base.default` when configured, otherwise `main`; if a stacked/non-default base is likely, ask the user and update `base`.

If `branch == base` or the configured default branch and local changes exist, emit workflow-signal `blocked`, then stop before gates/push. Show concise `git status --short`, explain direct PR handoff from base is unsafe, then ask for branch name and include set (`all`, selected paths, or abort). Selected paths require exact confirmation and a commit message; untracked files are excluded unless named. Create the branch and commit only approved paths before continuing. If there are no local changes and no branch diff, stop: nothing to prepare for review.

If on a feature branch with committed diff plus uncommitted files, warn that uncommitted files are excluded from the PR unless the user commits them.

### 1b. Check for existing PR

Run:

```bash
gh pr view --json url,baseRefName,headRefName 2>/dev/null
```

If a PR exists, enter fast-path mode: record `existing_pr_fast_path = true`, `pr_url`, and `base` from `baseRefName`; keep Phase 2 enabled, then push/report after gates and skip Phases 3/4. Split policy still runs but only warns.

### 1c. Categorize changes

Run:

```bash
git diff <base>...HEAD --name-only
git diff <base>...HEAD --shortstat
```

Store files/stats. If `gate_sets` exists, match ordered selectors to changed files, apply `exclude`, union sets deterministically, de-dupe by stable gate identity, and record selected/skipped reasons. Else mark touched scopes; else create implicit repo-root scope for top-level `gates`; else no gate scopes.

### 1d. Apply split policy

Skip when `split_policy` is absent or only one scope is touched. If `split_policy: exclusive` and two or more scopes are touched, set `split_policy_violation=true`, block the normal path before Phase 2, and guide the user to split branches/tickets manually; on existing-PR fast path, warn and continue. Do not auto-split.

### 1e. Detect triggered skills

Set `translation_sync_triggered` / `browser_compat_triggered` by pure path matching against configured trigger paths. Do not probe optional skills in Phase 1.

### 1f. Mandatory-attempt stale check

Attempt:

```bash
git fetch origin <base>
git rev-list --count HEAD..origin/<base>
```

Do not infer freshness from session context. If fetch/check fails, ask retry / proceed with freshness unknown / abort. If proceeding, set `freshness = unknown`, `needs_merge = false`, and carry a warning. If behind count is greater than zero, set `freshness = behind`, `needs_merge = true`, and warn that missing base commits can inflate the PR diff; Phase 2 owns merge/rebase handling. If zero, set `freshness = fresh`, `needs_merge = false`.

### 1g. Fast-path eligibility

Fast-path is for small, low-risk new PRs. Set `fast_path_eligible=true` only when all are true:

- not `existing_pr_fast_path`
- changed lines (additions + deletions from `--shortstat`) are known and ≤100
- one touched scope/repo-root, or `gate_sets` where all selected executable gates are parallel-safe and no-fix
- no split-policy violation
- `freshness=fresh` and `needs_merge=false`

Otherwise set false and record the first reason. Fast-path changes only pacing: preloaded aux, safe parallel gates, combined review. It never skips gates, blocking-finding handling, reduced-coverage acceptance, or PR approval.

## Phase-local tripwires

- No ticket guessing: confirmed id or `none` only.
- Never push/create PR directly from the default/base branch.
- Stale check is mandatory; unknown freshness is not green.
- Unknown diff size, multi-scope work, split violations, or stale base disable fast path.
