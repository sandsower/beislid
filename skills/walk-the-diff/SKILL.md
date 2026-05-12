---
name: walk-the-diff
description: Use when the user wants to walk through their local changes interactively before or instead of a PR review — e.g., "guided review", "walk me through the changes", "review my branch", "let's go through the diff". Also use when the user explicitly invokes the walk-the-diff skill through the host agent. This is for interactive human-facing walkthroughs of code changes, not automated code review.
---

# Guided Review

Simulate sitting next to a colleague who wrote the code and having them walk you through the changes. Present diffs in a logical order with context about why each change was made, highlight decision points and scrutiny areas, then pause so the reviewer can ask questions before moving on.

**Don't use this for:** automated review findings, PR comment posting, fixing feedback, or durable visual reports. Use `review`, `pr-patrol`, `review-response`, or explicit `show-me` instead.

## Global interactive contract

You are the author/presenter, not the reviewer. Explain and defend the change honestly without preemptively rejecting your own code.

The chunk gate is mandatory: never present a new chunk until the reviewer explicitly selects `Move on` or `Flag for follow-up`. If the reviewer types free text, treat it as a question/comment, answer it, present the same three options again, and stop.

The three options at every pause are exactly:

- `Move on` — advance to the next chunk
- `I have questions` — stay on this chunk; the reviewer will type their question next
- `Flag for follow-up` — note this chunk as needing revisit, then advance

## JIT phase protocol

Walk-the-diff phases are authoritative only after their aux files are read. Complete phases in order. At each phase boundary, read the matching file and follow it. If a phase file cannot be read, hard-fail instead of continuing from memory:

> 🛑 Could not read `skills/walk-the-diff/<phase-file>.md`. Walk-the-diff cannot safely execute this phase from memory; reinstall Beislið or restore the file.

- Phase 1: `skills/walk-the-diff/phase-1-context.md`
- Phase 2: `skills/walk-the-diff/phase-2-tour-plan.md`
- Phase 3: `skills/walk-the-diff/phase-3-present.md`
- Phase 4: `skills/walk-the-diff/phase-4-wrap.md`

When `BEISLID_VERBOSE=1`, print one aux load stamp after successfully reading each phase file. Stamp format is `✓ walk-the-diff/<phase-file-stem> v1 loaded` for `phase-1-context`, `phase-2-tour-plan`, `phase-3-present`, and `phase-4-wrap`.

## Checklist and outputs

1. **Gather context** — read `phase-1-context.md`. Outputs: base branch/merge base, commits, linked ticket/plans/specs, changed files, surrounding-code notes.
2. **Plan the tour** — read `phase-2-tour-plan.md`. Outputs: ordered chunk list, grouping rationale, reviewer preference if asked.
3. **Present chunks** — read `phase-3-present.md`. Outputs: each reviewed chunk, questions answered, flags/open items, reviewer gate choices.
4. **Wrap up** — read `phase-4-wrap.md` only after all chunks are reviewed or flagged. Outputs: overall feedback, saved feedback doc path, final stop.

## Visual walkthrough artifact

If the user explicitly wants a durable visual walkthrough, proof deck, or local HTML report instead of an interactive chunk-by-chunk review, invoke `show-me`. Do not run `show-me` automatically; it is manual/user-requested only in v1.

## Global tripwires

- One chunk at a time; never dump the whole diff.
- Do not advance on silence, ambiguity, or free-text approval. Require `Move on` or `Flag for follow-up`.
- Read commits and surrounding code before presenting diffs.
- Save feedback docs in user state, not the repo.
- Do not fix, implement, commit, push, or act on feedback during or after the walkthrough.
- After Phase 4 saves feedback, stop. Acting on feedback is a separate conversation.

## Common mistakes

- Presenting all chunks at once.
- Critiquing the code instead of explaining it as the author.
- Skipping context gathering and showing raw diffs without intent.
- Only reading diffs, not surrounding code.
- Advancing without the explicit chunk-gate choice.
- Fixing code during the review.
- Acting on feedback after wrap-up.

## Key principles

- Interactive pacing beats completeness dumps.
- Be honest about uncertainty; do not invent rationale missing from commits or plans.
- Adapt depth to reviewer questions.
- The feedback doc is the deliverable.
