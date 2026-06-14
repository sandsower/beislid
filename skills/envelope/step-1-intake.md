# envelope step 1 intake v1

Authoritative JIT protocol for envelope Step 1. Load after workflow.md and probe cache are initialized.

## Purpose

Resolve the input into approved planning context and candidate slices. Do not author envelopes from vague or unapproved input.

## Protocol

Print the Step 1 entry one-liner from `envelope-templates.md`.

### Detect input kind

In order:

1. **Manifest/bundle** — a JSON file (or `.beislid/exports/` path) whose `kind` is `approved-slice-plan-export-v0` or whose `schema` is `approved-slice-v1`/`rondo-execution-request-v1`. Revision signals: a delivery artifact (JSON referencing the bundle hash with `pause_reason`/`review_feedback`; see `docs/configuration.md`) or a non-approved `bundle.json` `status` carrying feedback. With a signal enter **REVISION MODE**: load the prior bundle dir, resolve its bundle-id, summarize feedback per envelope, print the revision-mode entry from `envelope-templates.md`. No feedback + `status: approved` → the nothing-to-revise refusal.
2. **Ticket id** — matches `ticket_source.id_pattern` (or the user names a ticket). `probe(ticket_source)`, evaluate action policy for `ticket.fetch` (`network-read`), and fetch title/body/acceptance criteria as `kickoff` Step 1 does, including the strict paste fallback on probe failure.
3. **File path** — an approved Work Contract, spec, or break-spec structure file (e.g. `plans/*-structure.md`). Read it as primary planning context. `Status: draft` contracts are not exportable input; route through `spec` first.
4. **Batch** — a list of ticket ids, or a Linear project naming several. Fetch each ticket via `ticket_source` exactly as in (2), with the per-ticket paste fallback on probe failure. The batch is ONE run: one planning context, one bundle, one dependency graph.
5. **None of the above** — ask the user for a ticket id, contract/structure path, or batch.

### Establish approved planning context

An envelope needs an approved decomposition with explicit slices. If the input already provides one (approved structure file with phases, or Work Contract with `slice_plan`/`children`), use it directly.

Otherwise, run the planning route in this session — that is the point of the strong-model session. Reuse, do not reimplement: `spec` when the problem/outcome is unclear, `break-spec` when multi-slice work lacks a slice structure, `blueprint`-depth design where a slice needs implementation shape before it can be scoped honestly. Carry results forward as the planning context.

Candidate slices are the AFK-marked (or plausibly AFK) slices from the structure. HITL-marked slices are noted but not authored. For batches, pool candidate slices across all tickets and record each slice's source ticket — it exports as `source_ticket` and feeds Step 2's cross-ticket dependency detection.

### Derive bundle-id

Revision mode reuses the prior bundle-id; skip derivation and the collision check. Otherwise: one bundle-id per run, batches included. Slug from the primary input — ticket id + short feature stem (e.g. `bei-76-envelope-orchestrator`); for batches, the project name, or joined ticket ids + stem when no project names the batch (e.g. `bei-12-bei-13-export-pipeline`): lowercase, non-alphanumeric runs → `-`, collapse repeats, strip edge `-`, ≤60 chars. Confirm with the user. If `.beislid/exports/<bundle-id>/` already exists, stop with the collision message from `envelope-templates.md`.

## Exit

Print the Step 1 exit one-liner. Required outputs: input kind, ticket/contract reference(s), planning context summary, candidate slice list with AFK/HITL markings and per-slice source ticket, bundle-id. Revision mode: prior bundle dir + bundle-id, per-envelope feedback — skip Steps 2–4, load `step-5-revise.md`.

## Tripwires

- Feedback-free approved manifests: refuse, never silently re-author.
- No envelope authoring from unapproved or sliceless context.
- Bundle-id collision is a hard stop, not an overwrite prompt.
