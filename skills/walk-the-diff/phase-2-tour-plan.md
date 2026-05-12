# walk-the-diff phase 2 tour plan v1

Authoritative JIT protocol for Phase 2. Load after Phase 1 has gathered branch, commit, linked-context, diff, and surrounding-code notes.

## Purpose

Turn the changed files into a reviewer-friendly route through the work.

## Protocol

Group and order changes by the story that makes review easiest. Common strategies:

- **User-facing first:** UI/API/behavior surface, then implementation and tests.
- **Data/model first:** structures or migrations, then producers, consumers, and tests.
- **Dependency order:** foundations/utilities first, then callers.
- **Narrative order:** follow one request/user action end to end.

If grouping is not obvious, ask the reviewer which route they prefer, for example:

> I see changes across `<areas>`. Want me to walk through it layer by layer, or follow the request flow end to end?

## Chunk rules

- Group related files together; a source file and its tests often belong in the same logical unit unless the smoke/user asks for a source-first split.
- Aim for 2-5 minutes per chunk.
- Typical size is 1-3 files or one cohesive hunk group.
- Split very large files into meaningful hunks instead of dumping full-file diffs.
- Put noisy generated/import-only changes at the end unless they are the point.

## Tour plan output

Before Phase 3, present a compact tour plan with:

- ordered chunks with names
- files/hunks in each chunk
- why this order helps review
- any known scrutiny areas from commits/plans/context

Do not include full diffs in Phase 2. Save diffs for Phase 3.

## Exit

Proceed to Phase 3 with the ordered chunk list, grouping rationale, reviewer preference if asked, and any flagged uncertainties.

## Tripwires

- Do not hide ambiguous ordering; ask the reviewer.
- Do not create one chunk per file by default when files form one logical unit.
- Do not present all diff hunks in the tour plan.
