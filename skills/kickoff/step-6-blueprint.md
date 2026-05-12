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
- scope decision and selected phase if any
- approved spec artifact status/path if `spec` returned one
- open risks/questions

Blueprint must produce an approved design before implementation begins. If blueprint discovers unclear product behavior, route back to `spec`; if it discovers the slice is too large, route to `break-spec`.

## Exit

Print the Step 6 exit one-liner after the design is approved. Required outputs: approved design summary, artifact status/path returned by blueprint if any, key files/modules expected to change, tests/verification planned, risks/open questions, and implementation handoff context.

## Tripwires

- No implementation starts before approved design.
- Do not drop ticket/context/domain/team findings when invoking blueprint.
