# review-response phase 3 push v1

Authoritative JIT protocol for Phase 3. Load after Phase 2 has completed fixes/drafts. If unreadable, hard-fail instead of reconstructing from memory.

## Entry / exit output

Print the Phase 3 entry one-liner from `review-response-templates.md`. In verbose mode, emit `✓ review-response/phase-3-push v1 loaded` after reading this file. Print the Phase 3 exit one-liner after push and reply handling.

## 3a. Decide whether gates are needed

Changes that only affect comments, variable names within function bodies, or whitespace are cosmetic. Everything else is functional.

If only cosmetic changes were made, pushing without gates is allowed after telling the user. Otherwise run gates.

## 3b. Run gates

Categorize the fix diff by scope:

- If `scopes` is configured: for each scope touched by the fix commits, `pushd <scope.cwd>` and run executable `pre-pr` gates in order.
- If top-level `gates` is configured and no scopes are configured: run executable `pre-pr` gates from repo root.
- If neither is configured: print `no gates configured — skipping`.

Normalize each gate before selection. A legacy flat gate with `name` + `command` defaults to `stage: pre-pr`, `kind: sensor`, `execution: computational`, and `mutates: false`. P0 review-response executes legacy gates and rich gates where `stage` is absent or `pre-pr`, `kind` is absent or `sensor`, `command` is present, and `execution` is absent or `computational`. Other stages are skipped-by-stage; pre-pr non-computational/non-sensor declarations are skipped-by-execution, not failures.

Before each selected gate command, `probe(scopes.<scope>.gates[<gate>].command)` or `probe(gates[<gate>].command)` as a CLI command, plus CLI `command -v` probes for any `required_tools[]` binaries. On failure use the gate prompt from `review-response-templates.md`; `(b)` skips only this gate for the session and is not written to cache.

For every gate run, capture duration and parse stdout/stderr into the shared Gate result envelope from `output-templates.md`; use the pytest parser for pytest-like output, otherwise generic text. Store raw logs by path when possible, or a transcript-safe summary.

Gate failure handling:

- Gate with `autofix` and envelope `status: fail` / `environment_failure: false`: show the envelope summary, run autofix, show diff, ask before committing.
- Envelope `status: error` or `environment_failure: true`: do not run autofix; prompt to repair/retry the environment or abort.
- Gate without `autofix`: prompt from the envelope (`summary`, key failures, retryable/environment flags, suggested next action, raw-log reference) plus configured `failure.*` / `output.parser` context. Do not guess.

If `split_policy: exclusive` and post-fix diff touches more than one scope, warn but do not block — the PR already exists.

## 3c. Translation sync

Skip if `translation_sync` is not configured or no fix-diff file matches `trigger_paths`.

Otherwise `probe(translation_sync.skill)` before invoking. If ok, invoke the skill. It may commit translation files; ask approval before committing generated changes.

## 3d. Push

```bash
git push
```

## 3e. Post or print replies

For PR review items:

- If `pr_review_update.type: cli`, `probe(pr_review_update)` before the first write.
- Write temp JSON payloads and substitute `{json_file}` into configured commands. Never shell-interpolate comment bodies.
- Clear-fix replies may be `Fixed in <short-sha>` after commit/push when fast path or item-level approval authorized them.
- Pushback and clarification replies always require per-item approval before posting.
- If update is absent, `type: manual`, or skipped, print reply instructions.

Reply payload:

```json
{ "body": "Fixed in abc1234", "in_reply_to": 123 }
```

For QA/ticket items:

- Use `ticket_update.comment_tool` / `comment_command` after approval.
- For CLI comment commands, write reply text to a temp file and substitute `{body_file}` with the path. Never interpolate raw reply text into the shell. If the configured command uses `{body}` instead of `{body_file}`, stop and ask the user to update workflow.md via `/setup` or print the reply manually for this run.
- If absent or skipped, print manual reply text.

## 3f. Re-request review

Only re-request review when the fix involves substantive changes (new logic, pushback, investigation-driven rewrites). Do NOT re-request when simply implementing what the reviewer asked for; the push and reply are enough.

If warranted and `pr_review_update.rerequest_command` exists, write JSON payload:

```json
{ "reviewers": ["<reviewer>"] }
```

Run configured command with `{json_file}`. If `rerequest_command` is absent/manual/skipped, print instructions.

## Outputs to run end

- pushed branch status
- replies posted or printed
- gate envelopes/status, skipped-by-stage/skipped-by-execution rich gates, and any accepted skips
- review re-request status if warranted
- probe/cache entries to write back
