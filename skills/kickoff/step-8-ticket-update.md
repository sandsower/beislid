# kickoff step 8 ticket update v1

Authoritative JIT protocol for kickoff Step 8. Load after blueprint approval and discovery handling.

## Purpose

Post or print the implementation-plan update, then hand off to `implement`.

## Protocol

Print the Step 8 entry one-liner from `kickoff-templates.md`.

### 8a. Update ticket

Compose a concise implementation-plan update:

- approach summary
- key files/modules expected to change
- tests/verification planned
- risks/open questions
- planning artifact paths/status when useful, labeled as local repo files rather than external links

If `ticket_update` is not configured, print the update for manual posting using `kickoff-templates.md` copy.

If configured: `probe(ticket_update)` before posting. Kickoff uses only the comment channel:

- **mcp:** call `ticket_update.comment_tool` with ticket ID and body.
- **cli:** write the approved body to a temp file, then run `ticket_update.comment_command` with `{id}` and `{body_file}` substituted. Never interpolate the raw body into the shell.

If the configured command uses `{body}` instead of `{body_file}`, stop and ask the user to update workflow.md via `/setup` or print the update manually for this run.

Show the exact body and wait for user approval before posting. On probe failure `(b)`, print the body for manual posting; do not write the skipped result to cache.

### 8b. Transition to implementation

Once the update is posted or printed, invoke `implement` with the approved design, any design artifact path returned by blueprint, and gathered context. `implement` handles task decomposition, TDD rhythm, task tracking, and parallel batching.

## Exit

Print the Step 8 exit one-liner. Required outputs: update status (`posted` or `printed`), approved update body, ticket-update side effect if any, and implement handoff context.

## Tripwires

- Always show the ticket update body before posting.
- CLI updates must use temp-file placeholders; never interpolate raw body text.
- Do not start implementation before approved blueprint and update handling.
