# envelope step 1 intake v1

Authoritative JIT protocol for envelope Step 1. Load after workflow.md and probe cache are initialized.

## Purpose

Resolve the input into approved planning context and candidate slices. Do not author envelopes from vague or unapproved input.

## Protocol

Print the Step 1 entry one-liner from `envelope-templates.md`.

### Detect input kind

In order:

1. **Manifest/bundle** — a JSON file (or `.beislid/exports/` path) whose `kind` is `approved-slice-plan-export-v0` or whose `schema` is `approved-slice-v1`/`rondo-execution-request-v1`. Stop with the revision-mode refusal from `envelope-templates.md`. Revision mode ships in a later version.
2. **Ticket id** — matches `ticket_source.id_pattern` (or the user names a ticket). `probe(ticket_source)`, evaluate action policy for `ticket.fetch` (`network-read`), and fetch title/body/acceptance criteria as `kickoff` Step 1 does, including the strict paste fallback on probe failure.
3. **File path** — an approved Work Contract, spec, or break-spec structure file (e.g. `plans/*-structure.md`). Read it as primary planning context. `Status: draft` contracts are not exportable input; route through `spec` first.
4. **None of the above** — ask the user for a ticket id, contract/structure path, or batch. v1 batch input (ticket list / Linear project) is accepted but this version packages one ticket per run; tell the user multi-ticket graphs land in a later phase.

### Establish approved planning context

An envelope needs an approved decomposition with explicit slices. If the input already provides one (approved structure file with phases, or Work Contract with `slice_plan`/`children`), use it directly.

Otherwise, run the planning route in this session — that is the point of the strong-model session. Reuse, do not reimplement: `spec` when the problem/outcome is unclear, `break-spec` when multi-slice work lacks a slice structure, `blueprint`-depth design where a slice needs implementation shape before it can be scoped honestly. Carry results forward as the planning context.

Candidate slices are the AFK-marked (or plausibly AFK) slices from the structure. HITL-marked slices are noted but not authored.

### Derive bundle-id

Slug from the primary input (ticket id + short feature stem, e.g. `bei-76-envelope-orchestrator`): lowercase, non-alphanumeric runs → `-`, collapse repeats, strip edge `-`, ≤60 chars. Confirm with the user. If `.beislid/exports/<bundle-id>/` already exists, stop with the collision message from `envelope-templates.md`.

## Exit

Print the Step 1 exit one-liner. Required outputs: input kind, ticket/contract reference, planning context summary, candidate slice list with AFK/HITL markings, bundle-id.

## Tripwires

- Manifest input is a refusal, not a silent re-author.
- No envelope authoring from unapproved or sliceless context.
- Bundle-id collision is a hard stop, not an overwrite prompt.
