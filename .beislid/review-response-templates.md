# Beislið review-response — output templates

Review-response-specific copy: orientation, phase one-liners, mode prompts, PR review source/update notes, fast-path authorization, and probe failure variants. Loaded from `skills/review-response/SKILL.md` through the per-skill auxiliary symlink. Shared primitives live in `output-templates.md`.

## Orientation

≤240 chars:

```
📋 Addressing feedback on `<branch>`. Reading `.beislid/workflow.md`; PR review, ticket, gate, and update capabilities will be probed only when needed. Cache: <fresh|stale|cold>.
```

## Phase one-liners

Entry:

```
🔄 Phase 1: Detect — finding the ticket, PR, and feedback source.
🔄 Phase 2: Fix — categorizing feedback and applying approved changes.
🔄 Phase 3: Push — running needed gates, syncing triggered work, and pushing.
```

Exit:

```
✓ Phase 1: Feedback loaded — <N> item(s) from <sources>.
✓ Phase 2: Fixes complete — <N> commit(s), <M> manual reply draft(s).
✓ Phase 3: Pushed `<branch>`; replies <posted|printed|not needed>.
```

## Mode prompt

When a current PR is found:

```
📋 I found PR `<url>`. Handle (a) PR review comments, (b) QA/ticket feedback, or (c) both? [default: a]
```

When no current PR is found:

```
📋 No current PR detected. Handle (a) QA/ticket feedback from `<ticket-id>` or (b) pasted feedback? [default: a]
```

## PR review source notes

Detection boundary:

```
🔒 PR detection is identity-only. `gh pr view` does not authorize PR review reads; feedback retrieval must use configured `pr_review_source` or strict paste.
```

Absent source:

```
⚠️ `pr_review_source` is not configured. I will not fetch PR review feedback with ad-hoc `gh` commands.
Paste the full source, including unresolved threads, author/source, status, file/line if relevant, and links if available.
```

Missing `threads_command`:

```
⚠️ PR review source has no `threads_command`; I can read PR-level comments but may miss inline review threads.
```

`type: paste`:

```
⚠️ Using pasted PR feedback for this run. Config stays unchanged and probes will retry next run.
Paste the full source, including unresolved threads, author/source, status, file/line if relevant, and links if available.
```

## PR review update notes

Manual update:

```
💭 PR review updates are manual for this project — I'll print reply and re-request instructions instead of posting.
```

Absent update:

```
💭 No PR review update path is configured — I'll print reply and re-request instructions instead of posting through ad-hoc `gh` commands.
```

Update boundary:

```
🔒 PR review updates require configured `pr_review_update`; absent/manual/skipped update paths mean print-only replies and no ad-hoc PR comments, inline replies, or review re-requests.
```

JSON-file write rule:

```
🔒 Writing PR replies through `{json_file}` payloads — comment bodies are never interpolated into shell commands.
```

## Fast-path authorization

Offer only when every item is obviously clear and all required sources/updates are non-manual and probed ok:

```
All items are obvious clear fixes or already addressed. Want me to fix, commit, run gates, push, post `Fixed in <short-sha>` replies, and re-request review only if warranted? [y/N]
```

Never offer fast path for product judgment, architecture tradeoffs, ambiguous intent, pushback, clarification, child-ticket creation, pasted/manual sources, or manual update paths.

## Probe failure prompts

`pr_review_source`:

```
⚠️ The capability `pr_review_source=<value>` failed: <reason>.
Ticket/QA feedback can still be handled if configured; PR review feedback needs a source.
What now? (a) retry, (b) paste PR review feedback manually, (c) abort.
```

`pr_review_update`:

```
⚠️ The capability `pr_review_update=<value>` failed: <reason>.
Fixes can still be pushed; only PR-thread replies/re-request review are blocked.
What now? (a) retry, (b) print reply instructions manually, (c) abort.
```

`ticket_source`:

```
⚠️ The capability `ticket_source=<value>` failed: <reason>.
PR review feedback can still be handled if configured; ticket/QA feedback needs a source.
What now? (a) retry, (b) paste QA/ticket feedback manually, (c) abort.
```

`ticket_update`:

```
⚠️ The capability `ticket_update=<value>` failed: <reason>.
Fixes can still be pushed; only ticket replies or child-ticket creation are blocked.
What now? (a) retry, (b) print ticket updates manually, (c) abort.
```

`gate command` probe:

```text
⚠️ The gate command `<name>` failed to resolve: <reason>.
Feedback fixes are still staged locally; verification is blocked until this check can run or you approve skipping it.
What now? (a) retry, (b) skip this gate for this session, (c) abort.
```

Gate execution failures use the shared Gate result envelope from `output-templates.md`:

```text
⚠️ Gate `<name>` failed: <envelope.summary>.
Failures: <top envelope.failures entries>. Retryable: <true|false>. Environment: <true|false>.
Suggested next action: <envelope.suggested_next_action>. Raw logs: <path or safe summary>.
What now? fix / retry / print manual next steps / abort.
```

## Char budgets

- Orientation: ≤240 chars.
- Phase one-liners: ≤120 chars.
- Probe failure prompt: ≤700 chars.
