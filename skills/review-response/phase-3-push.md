# review-response phase 3 push v1

Authoritative JIT protocol for Phase 3. Load after Phase 2 has completed fixes/drafts. If unreadable, hard-fail instead of reconstructing from memory.

## Entry / exit output

Print the Phase 3 entry one-liner from `review-response-templates.md`. In verbose mode, emit `✓ review-response/phase-3-push v1 loaded` after reading this file. Print the Phase 3 exit one-liner after push and reply handling.

## 3a. Decide whether gates are needed

Changes that only affect comments, variable names within function bodies, or whitespace are cosmetic. Everything else is functional.

If only cosmetic changes were made, pushing without gates is allowed after telling the user. Otherwise run gates.

## 3b. Run gates

Categorize the fix diff by gate model:

- `gate_sets`: match ordered selectors to fix-diff files, apply excludes, union/de-dupe sets deterministically, run selected executable `pre-pr` gates, and record selected/skipped reasons.
- `scopes`: for each touched scope, `pushd <scope.cwd>` and run executable `pre-pr` gates.
- top-level `gates`: when no scopes exist, run executable `pre-pr` gates from repo root.
- none: print `no gates configured — skipping`.

Normalize each gate before selection. A legacy flat gate with `name` + `command` defaults to `stage: pre-pr`, `kind: sensor`, `execution: computational`, and `mutates: false`. P0 review-response executes legacy gates and rich gates where `stage` is absent or `pre-pr`, `kind` is absent or `sensor`, `command` is present, and `execution` is absent or `computational`. Other stages are skipped-by-stage; pre-pr non-computational/non-sensor declarations are skipped-by-execution, not failures.

Before each selected gate, probe the gate command plus any `required_tools[]`. On failure use the gate prompt; `(b)` skips only this gate and is not cached.

For every gate, capture duration and parse stdout/stderr into the shared Gate envelope; use pytest parser for pytest-like output, otherwise generic. Store raw logs by path when possible, or a safe summary.

Gate failure handling:

- Gate `autofix` with `fail` / not env failure: show summary, policy-check, run on `allow`/approved `ask`, show diff, ask before commit.
- Envelope `status: error` or `environment_failure: true`: do not run autofix; prompt to repair/retry the environment or abort.
- Gate without `autofix`: prompt from the envelope (`summary`, key failures, retryable/environment flags, suggested next action, raw-log reference) plus configured `failure.*` / `output.parser` context. Do not guess.

If `split_policy: exclusive` and post-fix diff touches >1 scope, warn but don't block. `gate_sets` unioning areas is not itself a violation.

## 3c. Translation sync

Skip if `translation_sync` is not configured or no fix-diff file matches `trigger_paths`.

Otherwise `probe(translation_sync.skill)` before invoking. If ok, invoke it. It may commit translation files; policy-check `git.commit`, then ask before commit.

## 3d. Push

Policy-check `git.push` (`git-remote`), then push on `allow`/approved `ask`:

```bash
git push
```

## 3e. Post or print replies

For PR review items:

- If `pr_review_update.type: cli`, `probe(pr_review_update)` and policy-check `pr.review.reply`.
- Write temp JSON payloads and substitute `{json_file}` into configured commands. Never shell-interpolate comment bodies.
- Clear-fix replies may be `Fixed in <short-sha>` after commit/push when fast path or item-level approval authorized them.
- Pushback and clarification replies always require per-item approval before posting.
- If update is absent, `type: manual`, or skipped, print reply instructions.

Reply payload:

```json
{ "body": "Fixed in abc1234", "in_reply_to": 123 }
```

For QA/ticket items:

- Use `ticket_update.comment_tool` / `comment_command` after approval and `ticket.comment` policy.
- CLI commands write reply text to temp file and substitute `{body_file}`; never raw body shell interpolation. If configured `{body}`, stop and ask for `/setup` update or print manually.
- If absent/skipped, print manual reply text.

## 3f. Re-request review

Only re-request review when the fix involves substantive changes (new logic, pushback, investigation-driven rewrites). Do NOT re-request when simply implementing what the reviewer asked for; the push and reply are enough.

If warranted and `pr_review_update.rerequest_command` exists, write JSON payload:

```json
{ "reviewers": ["<reviewer>"] }
```

Policy-check `pr.review.rerequest`, then run configured command with `{json_file}` on `allow`/approved `ask`. If absent/manual/skipped, print instructions.

## Outputs to run end

- pushed branch status
- replies posted or printed
- gate envelopes/status, selection model, selected/skipped reasons, skipped-by-stage/skipped-by-execution rich gates, and any accepted skips
- review re-request status if warranted
- policy envelopes and `ask` outcomes
- probe/cache entries to write back
