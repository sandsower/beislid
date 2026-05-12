# walk-the-diff phase 3 present v1

Authoritative JIT protocol for Phase 3. Load after Phase 2 has produced an ordered tour plan.

## Purpose

Present each chunk, answer reviewer questions, and enforce the interactive gate.

## Per-chunk protocol

### 1. Set the stage

Before code, briefly explain what this chunk accomplishes and why it exists. Reference ticket/plan/commit intent when relevant:

> This chunk adds the search endpoint required by ABC-123. I'll show the route first, then the filter builder it calls.

### 2. Show focused diff

Use fenced `diff` code blocks. For large files, show meaningful hunks only. Skip boilerplate such as import reordering unless significant. If multiple files form a logical unit, show them together with a note connecting them.

### 3. Call out what matters

After the diff, highlight:

- **Decision points:** trade-offs made; cite commits/plans when they explain why.
- **Areas for scrutiny:** weak error handling, limitations, edge cases, or uncertainty.
- **Non-obvious connections:** behavior outside the diff, indexes, config, migrations, or callers.

Be honest about uncertainty. If the source of intent is missing, say what the code appears to do rather than inventing rationale.

### 4. Pause and gate

After every chunk, print the three options and stop:

- `Move on` — advance to the next chunk
- `I have questions` — stay on this chunk; the reviewer will type their question next
- `Flag for follow-up` — note this chunk as needing revisit, then advance

Never present a new chunk until the reviewer explicitly selects `Move on` or `Flag for follow-up`.

## Handling questions/comments

- **Why not X?** Explain the trade-off honestly; say when intent is unknown.
- **Is this tested?** Point to the relevant test file and specific cases. If missing, flag it.
- **What happens if...?** Trace the relevant code path and edge handling.
- **I don't understand this.** Re-explain at a different abstraction level and show surrounding code if useful.

After answering any question/comment, present the same three options again and stop. Free text is not an advance signal.

## Exit

When all chunks have been reviewed or flagged, carry forward:

- chunk statuses
- questions answered
- unresolved questions
- follow-up flags with file/line context when possible
- reviewer's gate choices

Then load Phase 4.

## Tripwires

- Do not dump future chunks while explaining the current one.
- Do not advance on vague approval such as `looks good` unless it is paired with `Move on` or `Flag for follow-up`.
- Do not fix code when feedback appears; note it for wrap-up.
