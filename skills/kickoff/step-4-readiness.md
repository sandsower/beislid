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

If the tracker issue already contains enough stable planning context, derive a `work-contract-v1` context packet for downstream handoff as a structured Markdown section following the template in `configuration.md`, including `Kind: work-contract-v1`, `Status`, and the named sections. Use `Status: draft` when unknowns remain and `Status: approved` only when required fields are complete. The packet is an initial contract draft that `spec` may finalize or `blueprint` may consume directly when approved. Include full `scope_classification` (`kind`, `confidence`, `rationale`, `recommended_route`, `requires_human_approval`, `requires_split`, `split_reason`). Derive `proof_requirements` deterministically from explicit ticket evidence plus configured gate metadata: for each applicable runnable gate, map it through the gate→`command_gate` proof-requirement rules in `configuration.md`/`workflow-md-format.md`; use `[]` only when no explicit proof and no applicable configured gate can yield a proof. Default reserved slots to `slice_plan: null` and `children: []`, and keep missing fields as explicit unknowns. `kind: unknown` is draft-only and routes to `spec_refinement`. Do not invent missing decisions. Broad/project work should not jump directly to scaffolding by default. If the ticket or contract already carries step-aware routing intent, preserve it as `model_routing` step hints for kickoff phases such as `ticket_context`, `context_discovery`, `scope_classification`, and `implementation_ready`; do not collapse those phases into the broad skill default.

If using `spec`, carry ticket text, acceptance criteria, attachments, codebase findings, domain context, team config, and any derived Work Contract fields into it. When spec returns, retain the approved spec or Work Contract plus any artifact status/path it reports for downstream scope, break-spec, blueprint, and ticket-update context. Do not design implementation details before spec approval.

After readiness is decided, continue to the checkpoint step (Step 4b) before Step 5 scope. The checkpoint step owns any `kickoff_context_ready` side effects.

## Exit

Print the Step 4 exit one-liner. Required outputs: readiness decision (`spec` or `blueprint` path), rationale, Work Contract status when derived or approved, spec artifact status/path if spec ran, and context packet to carry forward.

## Tripwires

- Do not patch vague requirements with implementation guesses.
- Do not drop codebase/domain/team context when routing to spec.
