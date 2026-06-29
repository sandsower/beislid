# review-response phase 1 detect v1

Authoritative JIT protocol for Phase 1. Load after workflow.md/cache setup. If unreadable, hard-fail instead of reconstructing from memory.

## Entry / exit output

Print the Phase 1 entry one-liner from `review-response-templates.md`. In verbose mode, emit `✓ review-response/phase-1-detect v1 loaded` after reading this file. Print the Phase 1 exit one-liner after feedback is normalized.

## 1a. Extract ticket ID

If `branch_pattern` is configured, apply it to `git branch --show-current` and capture group 1. If `ticket_source.id_pattern` is configured and the captured value's case doesn't match, normalize to the configured pattern's case. If no pattern matches or no branch pattern is configured, ask: "What is the ticket ID?"

## 1b. Validate branch state

Run:

```bash
git status --short
git branch --show-current
```

If there are uncommitted changes, summarize them and ask before continuing. Do not overwrite or mix uncommitted user work into feedback fixes without explicit approval.

## 1c. Derive PR host and detect PR

`pr_host` is pure address/config data, not a probed capability.

Derive owner/repo from workflow.md explicit `pr_host.owner` + `pr_host.repo` if present. Otherwise parse `git remote get-url <remote>`, where `<remote>` is `pr_host.remote` or `origin`. Understand SSH (`git@github.com:owner/repo.git`) and HTTPS (`https://github.com/owner/repo`).

Detect current PR when possible:

```bash
gh pr view --json url,number,baseRefName,headRefName 2>/dev/null
```

This detection is best-effort and does not replace configured PR review sources. `gh pr view` is only a convenience for GitHub-shaped repos; a configured `pr_review_source` still makes PR-review mode available when `gh` is absent, irrelevant, or returns nothing.

If PR mode is chosen and owner/repo/number/url cannot be resolved from detection, ask for the missing values before running `pr_review_source`. Hard-abort only if the configured source requires those placeholders and the user cannot provide them. If the source command has no PR placeholders, run it as configured.

## 1d. Choose mode

Use hybrid detect + confirm:

- If a current PR is found, ask from `review-response-templates.md`: PR review comments, QA/ticket feedback, or both? Default PR review.
- If no PR is found but `pr_review_source` is configured, still offer PR review mode: "I didn't detect a current PR, but `pr_review_source` is configured. Handle PR review comments, QA/ticket feedback, both, or pasted feedback?" Default PR review.
- If no PR is found and `pr_review_source` is absent, ask: QA/ticket feedback from `<ticket-id>` or pasted feedback? Default QA/ticket.

## 1e. Gather PR review feedback

Run only if mode includes PR review.

If `pr_review_source` is absent, ask for pasted PR review feedback and note that PR review source is not configured.

If `pr_review_source.type: paste`, ask for pasted PR review feedback using the strict prompt in `review-response-templates.md`.

If `type: cli`:

1. If `threads_command` is missing, print the non-blocking warning from `review-response-templates.md`.
2. `probe(pr_review_source)`.
3. Substitute `{owner}`, `{repo}`, `{number}`, and `{url}` in configured commands.
4. Run `summary_command`; run `threads_command` if configured.
5. Extract unresolved review comments/threads, PR-level comments, author, body, status, file/line, comment ID, reviewer username, and URLs when available.

On probe failure `(b)`, ask for strict PR feedback paste. Do not continue blind.

## 1f. Gather QA/ticket feedback

Run only if mode includes QA/ticket.

If `ticket_source.type: paste`, ask for pasted QA/ticket feedback.

Otherwise `probe(ticket_source)` before fetching. On failure `(b)`, ask for strict pasted QA/ticket feedback with source, author, status if known, and links if available.

Fetch based on `ticket_source.type`:

- **mcp:** call configured `tool` with ticket ID; extract comments/feedback.
- **cli:** run configured `command` with `{id}` substituted.
- **file:** read configured `file_glob` matching ticket ID.
- **paste:** use pasted feedback.

## 1g. Normalize feedback queue

Normalize PR review, QA/ticket, and pasted feedback into one queue:

```yaml
source: pr_review | ticket_qa | pasted
source_url: optional
author: optional
body: string
status: optional
file: optional
line: optional
comment_id: optional
reviewer: optional
```

If a PR review item is from CodeRabbit and the body says `Review skipped`, `Review limit reached`, `rate limited`, or `draft detected`, set `status: deferred_review` and keep it as evidence, not actionable review feedback. Preserve the bot comment text and source metadata so babysit and release summaries can surface the gap. Do not route deferred-review items into Phase 2 fixes unless the body also contains an actual actionable request.

If mode is both, categorize one combined queue so duplicate requests across sources are fixed once. Preserve `source` metadata so replies go back to the right place.

## Outputs to Phase 2

- ticket ID if known
- PR owner/repo/number/url when available
- selected mode
- normalized feedback queue with source metadata
- any configured-source limitations or paste/manual fallback notes
