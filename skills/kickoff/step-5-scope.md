# kickoff step 5 scope v1

Authoritative JIT protocol for kickoff Step 5. Load after requirements are clear or after spec returns approved requirements.

## Purpose

Decide whether the work fits one coherent PR or needs decomposition.

## Protocol

Print the Step 5 entry one-liner from `kickoff-templates.md`.

Route to `break-spec` when the work:

- spans multiple independently shippable vertical slices
- has unclear phase boundaries
- would be too large for one reviewable PR
- mixes product areas that should be reviewed or released separately

If the work fits one coherent PR, continue to Step 6 blueprint.

When routing to `break-spec`, carry the approved spec/requirements, any spec artifact status/path returned by `spec`, ticket, context, domain notes, team constraints, and risks.

## Exit

Print the Step 5 exit one-liner. Required outputs: scope decision (`single PR` or `needs breakdown`), rationale, spec artifact status/path if present, and selected phase if breakdown is invoked and a phase is chosen.

## Tripwires

- Do not let kickoff proceed to blueprint for multi-PR work without explicit phase selection.
- Keep vertical slices shippable; do not decompose by technical layer only.
