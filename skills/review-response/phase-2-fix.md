# review-response phase 2 fix v1

Authoritative JIT protocol for Phase 2. Load after Phase 1 has normalized feedback. If unreadable, hard-fail instead of reconstructing from memory.

## Entry / exit output

Print the Phase 2 entry one-liner from `review-response-templates.md`. In verbose mode, emit `✓ review-response/phase-2-fix v1 loaded` after reading this file. Print the Phase 2 exit one-liner after fixes/drafts are complete.

## 2a. Categorize feedback

For each item, assign one category:

- **Clear fix** — concrete issue with an obvious solution (typo, mechanical rename, missing obvious guard/null check, requested mechanical change).
- **Needs investigation** — valid concern but surrounding code or behavior must be read before deciding.
- **Pushback candidate** — comment seems technically wrong, conflicts with prior decisions, or asks for unnecessary scope.
- **Already addressed** — thread/comment is outdated and current code already reflects the requested change.
- **Deferred review** — CodeRabbit says the review was skipped, rate-limited, or draft-deferred; keep it as not reviewed evidence, not a fix candidate.
- **Out-of-scope** — valid but belongs in a separate ticket.
- **Clarification needed** — feedback is ambiguous.

Present the categorized list with proposed action for each item. User may reclassify before fixes begin. Deferred-review items should stay as evidence unless paired with additional actionable feedback.

## 2b. Fast-path check

Offer the fast path only when every item is obviously clear or already addressed, all feedback was fetched from configured non-manual sources, all needed update paths are non-manual and probed ok, no child tickets/clarifications/pushback are needed, and expected diff is small.

Use the authorization copy from `review-response-templates.md`. If the user approves, that single approval authorizes:

- making clear fixes after policy `allow` or approved `ask`
- committing after policy `allow` or approved `ask`
- running gates
- pushing after policy `allow` or approved `ask`
- posting `Fixed in <short-sha>` PR replies when `pr_review_update` is CLI and ok and policy allows or `ask` is approved
- posting QA/ticket clear-fix replies when `ticket_update` is configured and ok
- re-requesting review only if warranted by the rule in Phase 3

Never fast-path product judgment, architectural tradeoffs, ambiguous intent, pushback, clarification, child-ticket creation, pasted/manual sources, or manual update paths.

## 2c. Fix clear/investigation items

Work item by item unless fast path was approved:

1. Read relevant files and surrounding code.
2. Evaluate action policy for the workspace write (`workspace-write` plus any known non-read class), then make the fix or investigation-driven change only when policy allows or `ask` is approved.
3. For pushback or clarification, draft reasoning instead of changing code.
4. Show substantive replies to the user before posting.

Commit strategy:

- Batch straightforward clear fixes into one commit: `Address feedback` or repo convention.
- Separate commits for investigation-driven changes when they are easier to review separately.
- Follow repository commit-message conventions when evident; don't assume ticket hooks.

## 2d. Out-of-scope and clarification handling

For out-of-scope QA/ticket items:

1. Draft a child-ticket title/body.
2. Ask for approval.
3. If approved and `ticket_update` has an issue channel, `probe(ticket_update)`, evaluate action policy for `ticket.create_child` with external write classes, and create it only when policy allows or `ask` is approved. For CLI issue commands, write title and body to temp files and substitute `{title_file}` + `{body_file}`; never interpolate raw text.
4. If absent/manual/skipped, print the child-ticket draft.
5. Draft a reply: `Tracked in <new-ticket-id>` or manual equivalent.

For clarification-needed items, draft a question and ask approval before posting or printing.

## Outputs to Phase 3

- fix commits made or note that no code changes were needed
- policy decision envelopes and accepted/declined `ask` outcomes
- changed files and whether changes are cosmetic or functional
- reply drafts plus source metadata
- approved fast-path status, if any
- pushback, clarification, child-ticket, or manual-update decisions
