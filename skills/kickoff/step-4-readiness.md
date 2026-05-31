# kickoff step 4 readiness v1

Authoritative JIT protocol for kickoff Step 4. Load after ticket, codebase, domain, and team context are available.

## Purpose

Decide whether requirements are clear enough for implementation design.

## Protocol

Print the Step 4 entry one-liner from `kickoff-templates.md`.

Route to `spec` when any of these are unclear:

- problem or user workflow
- desired behavior
- success criteria / acceptance outcomes
- constraints or edge cases
- multiple plausible product interpretations

If the tracker issue already contains enough stable planning context, derive a `work-contract-v1` context packet for downstream handoff as a structured Markdown section following the template in `configuration.md`, including `Kind: work-contract-v1`, `Status`, and the named sections. Use `Status: draft` when unknowns remain and `Status: approved` only when required fields are complete. The packet is an initial contract draft that `spec` may finalize or `blueprint` may consume directly when approved. Include shallow `scope_classification`; include explicit or derived `proof_requirements` when the ticket/gates name done evidence, otherwise `[]`; default reserved slots to `slice_plan: null` and `children: []`; keep missing fields as explicit unknowns. Do not invent them. Broad/project work should not jump directly to scaffolding by default.

If using `spec`, carry ticket text, acceptance criteria, attachments, codebase findings, domain context, team config, and any derived Work Contract fields into it. When spec returns, retain the approved spec or Work Contract plus any artifact status/path it reports for downstream scope, break-spec, blueprint, and ticket-update context. Do not design implementation details before spec approval.

After readiness is decided, continue to the checkpoint step (Step 4b) before Step 5 scope. The checkpoint step owns any `kickoff_context_ready` side effects.

## Exit

Print the Step 4 exit one-liner. Required outputs: readiness decision (`spec` or `blueprint` path), rationale, Work Contract status when derived or approved, spec artifact status/path if spec ran, and context packet to carry forward.

## Tripwires

- Do not patch vague requirements with implementation guesses.
- Do not drop codebase/domain/team context when routing to spec.
