# review-response phase 3 push v1

Authoritative JIT protocol for Phase 3. Load after Phase 2 has completed fixes/drafts. If unreadable, hard-fail instead of reconstructing from memory.

## Entry / exit output

Print the Phase 3 entry one-liner from `review-response-templates.md`. In verbose mode, emit `✓ review-response/phase-3-push v1 loaded` after reading this file. Print the Phase 3 exit one-liner after push and reply handling.

**Hard boundary:** Push is not PR feedback update authority. Only configured `pr_review_update` may post PR comments/replies, submit/dismiss reviews, or re-request review; absent/manual/skipped means print only.

## 3a. Decide whether gates are needed

Changes that only affect comments, variable names within function bodies, or whitespace are cosmetic. Everything else is functional.

If only cosmetic changes were made, pushing without gates is allowed after telling the user. Otherwise run gates.

## 3b. Run gates

Categorize the fix diff by gate model:

- `gate_sets`: select by files, apply excludes/defaults, union/de-dupe, run executable `pre-pr` gates, and record reasons.
- `scopes`: for each touched scope, `pushd <scope.cwd>` and run executable `pre-pr` gates.
- top-level `gates`: when no scopes exist, run executable `pre-pr` gates from repo root.
- none: print `no gates configured — skipping`.

Normalize gates before running. Flat `name` + `command` defaults to `stage: pre-pr`, `kind: sensor`, `execution: computational`, `mutates: false`. P0 runs absent/`pre-pr` sensor computational gates with commands. Other stages are skipped-by-stage; pre-pr non-computational/non-sensor gates are skipped-by-execution.

Before each selected gate, probe the gate command plus any `required_tools[]`. On failure use the gate prompt; `(b)` skips only this gate and is not cached.

For every gate, capture duration and parse stdout/stderr into the shared Gate envelope; store raw logs by path when possible, otherwise a safe summary.

Gate failure handling:

- Gate `autofix` with `fail` / not env failure: show summary, policy-check, run on `allow`/approved `ask`, show diff, ask before commit.
- Envelope error/environment failure: do not autofix; prompt to repair/retry or abort.
- No `autofix`: prompt from the envelope plus configured failure/parser context. Do not guess.

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
- Pushback and clarification replies require per-item approval before posting; keep draft/context prose question-free.
- If update is absent, `type: manual`, or skipped, print reply instructions only. Do not use ad-hoc `gh api`, `gh pr review`, `gh pr comment`, GraphQL, or host API fallbacks.

Reply payload:

```json
{ "body": "Fixed in abc1234", "in_reply_to": 123 }
```

For QA/ticket items:

- Use `ticket_update.comment_tool` / `comment_command` after approval and `ticket.comment` policy.
- CLI commands write reply text to temp file and substitute `{body_file}`; never raw body shell interpolation. If configured `{body}`, stop and ask for `/setup` update or print manually.
- If absent/skipped, print manual reply text.

## 3f. Re-request review

Re-request only for substantive changes (new logic, pushback, investigation-driven rewrites). Do NOT re-request for simply implementing requested fixes; push/reply is enough.

If warranted and `pr_review_update.rerequest_command` exists, write JSON payload:

```json
{ "reviewers": ["<reviewer>"] }
```

Policy-check `pr.review.rerequest`, then run configured command with `{json_file}` on `allow`/approved `ask`. If absent/manual/skipped, print only; no ad-hoc fallbacks.

## Outputs to run end

- pushed branch status
- replies posted or printed
- gate envelopes/status, selection model, selected/skipped reasons, skipped-by-stage/skipped-by-execution rich gates, and any accepted skips
- feedback response log using the `artifact-templates.md` shape
- review re-request status if warranted
- policy envelopes and `ask` outcomes
- probe/cache entries to write back
