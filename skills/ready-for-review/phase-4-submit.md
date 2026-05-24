# ready-for-review phase 4 submit v1

Authoritative protocol for Phase 4. Normal mode loads it after Phase 3 has no unaccepted blocking findings; fast-path may preload it after Phase 1 but must not enter it until Phase 3 passes. Existing-PR fast path never enters this phase.

## Entry contract

Inputs: branch, base, ticket ID or `none`, diff stats, fast-path state, Phase 2/3 status, accepted/reduced-coverage risks, workflow config, in-memory probe state, verbose/transcript handles, and loaded-aux metadata. Outputs: PR URL/title/base, final notes, domain-capture status, memory brief status, and Phase 4 exit status. Main owns cache write-back.

Print the Phase 4 entry one-liner from `ready-for-review-templates.md`; verbose mode appends load/entry transcript events and exit checks.

## Hard gate

The user must explicitly approve the final PR title and body before any push/PR creation. Draft PR creation also requires this approval. Ask that blocking approval question exactly once in user-visible output: show the title/body as context, then put the single approval question in the final/blocking response, or do not restate it if the visible context already asked it. Marking a draft PR ready requires a second explicit approval after bot review/fixes. Do not treat silence, ambiguous approval, or prior Phase 3 approval as PR approval.

## 4-pre. Paired-set front-load

Before ticket title fetch or PR handoff side effects, evaluate `domain_expert.agent` ↔ `knowledge_store.path` as one paired set:

- Both configured: `probe(domain_expert.agent)` and `probe(knowledge_store.path)`. If either fails, use the paired-set retry/skip/abort prompt from `ready-for-review-templates.md`.
- Exactly one configured: do not probe; add the paired-half-missing note and treat Phase 4d as disabled.
- Neither configured: do not probe; treat Phase 4d as unconfigured and print disabled note only at 4d.

A session skip suppresses re-check at 4d.

## 4a. Fetch ticket title

If `ticket_id = none`, skip ticket-source probing/fetching. Record `no issue`; PR title must not get a ticket prefix.

If `ticket_source.type: paste`, ask the user for the title while drafting. Otherwise call `probe(ticket_source)` on first need. On failure, use the Phase 4a prompt; proceed-this-session means the user pastes the title manually with no workflow.md change.

On probe success, fetch by configured source: `mcp`, `file`, `cli` with `{id}` substitution and JSON-title parsing, or `paste`.

Do not infer a ticket by listing/searching open issues. If a possible issue is discovered incidentally, ask before associating it.

## 4b. Draft PR and approval

Compose the proposed PR:

- Title: `<TICKET-ID>: <ticket title>` only when a real ticket id is confirmed; otherwise a concise no-ticket title. Never render `none` as a prefix; `none: <title>` is invalid.
- Base: Phase 1 base.
- Body: terse record-facing summary of changes, why, verification, reviewer warnings, accepted risks, and reduced review coverage if any.
- Include carried warnings such as AI-generated translation notices.
- Labels/reviewers only when configured or requested.

If `pr_description.formatter_skill` is configured, probe it on first need; on failure use the Phase 4b prompt and raw draft for proceed-this-session. If no formatter is configured, print the raw-draft note.

Show final title/body and wait for explicit approval. Do not ask one approval question in progress prose and then a second shorter approval question in the final response.

If draft PRs plus provider bot review are supported, after approval offer draft-bot-review. On yes: create draft, handle valid bot findings like Phase 3 review findings, rerun applicable gates after functional fixes, commit/push accepted fixes, then ask for explicit approval before marking ready.

## 4c. Push and create PR

Before push, if the PR provider is GitHub/`gh` and changed files include `.github/workflows/`, preflight auth for `workflow` scope (for example `gh auth status`). If scope is missing or cannot be checked, warn and ask retry / proceed-with-warning / abort. This preflight is skipped for non-GitHub/non-`gh` providers.

Run push/PR commands from explicit repo cwd. Always pass the branch with `--head <branch>`; do not rely on `gh` inferring upstream, especially when uncommitted/untracked files exist.

Normal path:

```bash
git push -u origin HEAD
gh pr create --head "<branch>" --title "<title>" --base "<base>" --body "<description>"
```

Draft path adds `--draft`; readying later uses provider command such as `gh pr ready` only after second explicit approval.

On network/sandbox failure, surface retry with needed permissions/escalation or abort. Do not re-draft or change approved title/body unless the user asks.

Report the PR URL with the success template. Include notes after the success prose. Verbose mode records transcript events for push, PR creation, bot-review choice, fixes, ready-marking, and auth preflight.

## 4d. Capture domain knowledge

If Phase 4-pre disabled domain capture, print no extra prose beyond the relevant inline note due at this boundary.

If configured and available, decide whether the review-submitted work uncovered durable domain knowledge. Skip purely mechanical work; otherwise spawn `domain_expert.agent` with a concise submitted-work summary and target `knowledge_store.path`. Domain capture is best-effort after PR creation; failure does not invalidate the PR.

## 4e. Structured session memory / memento brief

Generic session-end auto-capture does not satisfy this step. On successful PR handoff, or on abort after Phase 2 starts or any side effect, complete this checklist before final run-end output:

1. If host memory exists or `BEISLID_MEMENTO_CAPTURE=1`, attempt one structured brief.
2. Append/print exactly one literal marker: `kind: ready-for-review-session-memory-v1` with the brief, or `memory brief unavailable:<reason>`.
3. Include repo, branch, base, ticket id or `none`, PR URL if any, phase path (`new-pr-fast-path` when used), aux loaded, transcript path/unavailable reason, gates including parallel mode, review/final-check or combined-review status including cancellation/partial output, accepted risks, side effects, host, timestamp, and duration if known.
4. If a run ledger is active: `finalize` only after successful PR handoff; on abort, record `beislid run-ledger interrupt` with context.

Do not finish with only prose such as “brief summarized”; that fails smoke. Do not include secrets, env values, auth headers, or raw stdout/stderr.

## Exit

Print the Phase 4 exit one-liner from `ready-for-review-templates.md`. In verbose mode, append Phase 4 exit check and loaded/not-reached aux status per `ready-for-review-templates.md`.

## Phase-local tripwires

- Never create/ready a PR without the explicit approvals defined above.
- Ticket association is confirmed id or `none`; never guessed from issue lists.
- Always create PRs with explicit repo cwd and `--head <branch>`.
