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

If using `spec`, carry ticket text, acceptance criteria, attachments, codebase findings, domain context, and team config into it. When spec returns, retain the approved spec plus any artifact status/path it reports for downstream scope, break-spec, blueprint, and ticket-update context. Do not design implementation details before spec approval.

If requirements are clear, continue to Step 5 scope gate.

After readiness is decided, continue to the checkpoint step before Step 5 scope. The checkpoint step owns any `kickoff_context_ready` side effects.

## Exit

Print the Step 4 exit one-liner. Required outputs: readiness decision (`spec` or `blueprint` path), rationale, spec artifact status/path if spec ran, and context packet to carry forward.

## Tripwires

- Do not patch vague requirements with implementation guesses.
- Do not drop codebase/domain/team context when routing to spec.
