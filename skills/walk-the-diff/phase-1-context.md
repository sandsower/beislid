# walk-the-diff phase 1 context v1

Authoritative JIT protocol for Phase 1. Load when starting a guided diff walkthrough. If unreadable, the main skill must stop instead of reconstructing this behavior from memory.

## Purpose

Build a mental model of the change set before presenting anything.

## Protocol

### Determine base and merge-base

Find the base branch. Prefer `main`; use `master` only when `main` does not exist. Use simple single git commands and store the merge-base SHA for later commands:

```bash
git merge-base HEAD main
git diff <merge-base-sha>...HEAD --stat
git log <merge-base-sha>..HEAD --oneline
```

If neither base exists or merge-base fails, ask the user which base to use. Do not guess from unrelated branches.

### Read commit intent

Read commit messages as the primary source of author intent:

```bash
git log <merge-base-sha>..HEAD --format="%H%n%s%n%b%n---"
```

Capture why the change exists, important decisions, and any uncertainty in terse notes for Phase 2.

### Find linked context

Look for ticket IDs or feature names in the branch name and commit messages:

- Issue IDs such as `ABC-123` or `#456`.
- Planning docs under `plans/`, `docs/plans/`, or configured equivalents.
- Spec docs under `specs/`, `docs/specs/`, or configured equivalents.

Fetch/read only directly relevant context. If a ticket tracker is unavailable, say so and continue with commits/plans/code; do not invent requirements.

### Read changed files and surrounding code

Read the diff and enough surrounding code to explain each change:

```bash
git diff <merge-base-sha>...HEAD --name-status
git diff <merge-base-sha>...HEAD -- <path>
```

For each changed file, inspect nearby functions/classes/imports/tests so Phase 3 can answer questions without hand-waving. Note generated/noisy changes separately.

## Exit

Before Phase 2, summarize:

- base branch and merge-base SHA
- commit list and intent notes
- linked ticket/plan/spec context or `none found`
- changed files and notable surrounding-code findings
- uncertainties to surface during the tour

## Tripwires

- Do not present diffs before completing this context pass.
- Do not treat commit messages as sufficient when changed code needs surrounding context.
- Do not fetch unrelated tickets or broad docs just because a string matched loosely.
