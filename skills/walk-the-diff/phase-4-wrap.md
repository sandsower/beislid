# walk-the-diff phase 4 wrap v1

Authoritative JIT protocol for Phase 4. Load only after Phase 3 has completed or flagged every planned chunk. If the interactive gate is still waiting on the current chunk, do not load this phase.

## Purpose

Close the walkthrough, collect the reviewer's overall take, save feedback notes outside the repo, and stop.

## Protocol

### Summarize open items

List anything the reviewer flagged, questions that were not fully resolved, and areas both sides agreed need follow-up. Each item should be actionable without re-reading the whole diff.

### Ask for overall feedback

Ask:

> Any other concerns, or are you comfortable with these changes overall?

Record the answer. If the reviewer raises new concerns, capture them as open items; do not fix them.

### Save feedback

Create a feedback file under `${BEISLID_STATE_DIR:-~/.local/state/beislid}/feedback/`. Create the directory if needed. Use legacy `~/.claude/feedback/` only if the host setup requires it.

Feedback docs live in user state, not the repo. If a ticket ID is associated, include it in the filename.

Suggested filename:

```text
${BEISLID_STATE_DIR:-~/.local/state/beislid}/feedback/{descriptive-name}-{ticket-id}.md
```

Use this format:

```markdown
# Review Feedback: {Brief Description}

**Date**: {date}
**Branch**: {branch name}
**Ticket**: {ticket ID if any}

## Chunks Reviewed

### {Chunk 1 name}
- Status: {approved / needs changes / discussed}
- Feedback:
  - {description of feedback item}
    - Files: {filename:line_number for each relevant location}
    - Context: {what the current code does and why the change is suggested}
    - Suggestion: {concrete description of what should change}

## Open Items
- {description} — `{filename:line_number}` — {why and what to change}

## Overall Assessment
{reviewer's overall take}
```

If there are no open items, write `None` under `## Open Items`.

## Exit

Tell the reviewer where the feedback file was saved and that the review is complete. Stop immediately after that.

## Tripwires

- Do not write feedback docs inside the repo.
- Do not skip saving feedback because there were no open items.
- Do not start fixing, implementing, committing, pushing, or addressing feedback.
- The feedback doc is the deliverable; acting on it is a separate conversation.
