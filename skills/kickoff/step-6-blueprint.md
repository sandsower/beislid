# kickoff step 6 blueprint v1

Authoritative JIT protocol for kickoff Step 6. Load when a single implementation slice is ready for design.

## Purpose

Invoke `blueprint` with complete context and require an approved implementation design before implementation planning.

## Protocol

Print the Step 6 entry one-liner from `kickoff-templates.md`.

Invoke `blueprint` with:

- ticket title/body/acceptance criteria
- attachments/screenshots
- codebase findings and likely files/tests
- domain context
- team config constraints
- `scope_classification`, derived route summary, and selected phase/slice if any
- approved Work Contract or derived Work Contract context when available
- approved spec lifecycle status/artifact path if `spec` returned one
- open risks/questions

Blueprint must produce an approved design before implementation begins. Blocking Work Contract unknowns are gaps that prevent choosing an implementation approach or change the `Problem`, `Desired Outcome`, `Constraints`, or acceptance outcomes; route those back to `spec`. Non-blocking unknowns, such as optional details, UI copy, or implementation-specific choices, may stay recorded in `Unknowns / Human Decisions`. If `scope_classification.kind` is `multi_slice`, route to `break-spec`; if `scope_classification.kind` is `project` with unresolved boundaries, route to `spec_refinement`; if `scope_classification.kind` is `project` with approved boundaries but no selected phase/slice, route to `break-spec`. An approved selected phase/slice bypasses this routing.

## Exit

Print the Step 6 exit one-liner after the design is approved. Required outputs: approved design summary, lifecycle status/artifact path returned by blueprint if any, key files/modules expected to change, tests/verification planned, risks/open questions, and implementation handoff context.

## Tripwires

- No implementation starts before approved design.
- Do not drop ticket/context/domain/team findings when invoking blueprint.
