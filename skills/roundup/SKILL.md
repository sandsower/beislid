---
name: roundup
description: Triage a set of tickets into AFK-ready, AFK-blocked, and HITL pens with dependency-safe waves, then hand wave 1 to the configured AFK intake queue. Use only when the user explicitly invokes /roundup with ticket ids or a prose description of a ticket set. Other skills may recommend it but must never auto-route into it. Ends with an approved pen sheet and queue moves; it never implements, decomposes, or enriches tickets.
---

# Roundup

The judgment gate on the AFK boundary: sort a ticket set into pens — **AFK-ready** (contract-grade, conflict-checked, in dependency-safe waves), **AFK-blocked** (named gaps, routed to `spec`), **HITL** (ordered for `kickoff`) — take explicit per-pen verdicts, then write the pen sheet and move wave 1 into the queue the runner polls.

**Trigger is explicit only.** Sending work AFK is the highest-stakes process judgment in the workflow; the human invokes this gate deliberately. Skills may *recommend* `/roundup`; they never auto-route here, and roundup never auto-routes onward.

**Don't use this for:** starting a single ticket (`kickoff`), slicing one feature (`break-spec`), authoring execution envelopes (`envelope`), or running anything — execution, scheduling, and run evidence belong to the runner. Roundup arranges existing tickets; it never decomposes or enriches them.

Project config: `<repo>/.beislid/workflow.md`. Probe lazily per `probe-semantics.md`; policy-check side effects per `action-policy-protocol.md`. Output copy lives in `roundup-templates.md`.

## Read workflow.md

Read `<repo>/.beislid/workflow.md` and validate line 1 is exactly `<!-- beislid-workflow: v1 -->`; hard-fail and stop if missing or wrong (run `/setup` for fresh projects). Initialize the probe cache exactly as `kickoff` does (`repo_hash`, `workflow_hash`, `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/<repo_hash>.json`, fresh/stale/cold). Print orientation prose from `roundup-templates.md` (≤240 chars).

Optional config this skill consumes: `ticket_source.list_tool` (enables prose intake) and the `beislid:afk_queue` block (enables queue dispatch). Both degrade gracefully when absent — id-list intake and pen-sheet-only handoff still work.

For durable evidence, best-effort `beislid run-ledger init --skill roundup --flow roundup` with roster/branch context when known. Warn on ledger failure; never block.

## Step protocol loading

Complete steps in order. At each step entry, read the step aux file and follow it as the authoritative protocol. If a step file cannot be read, hard-fail and stop:

> 🛑 Could not read `skills/roundup/<step-file>.md`. Roundup cannot safely execute this step from memory; reinstall Beislið or restore the file.

## Checklist and required outputs

1. **Intake** — read `step-1-intake.md`. Outputs: confirmed roster, source description, stem.
2. **Analyze** — read `step-2-analyze.md`. Outputs: per-ticket cards — AFK-bar verdict with exact gaps, human-shaped notes, explored touch areas, dependency edges, conflict flags.
3. **Sort** — read `step-3-sort.md`. Outputs: approved pens with explicit verdicts, wave structure with per-ticket justification, recorded overrides.
4. **Handoff** — read `step-4-handoff.md`. Outputs: pen sheet path, wave-1 queue-move outcomes, routing summary.

## Global tripwires

- **Fail-closed:** no pen sheet content and no queue move exists without a Step 3 verdict behind it. Zero AFK-ready tickets is a valid terminal state — pen sheet and routing only, nothing queued.
- **Arrange-only.** Roundup never decomposes, enriches, or edits tickets, and never starts the work it is sorting. Unready tickets get enrichment briefs and a route, not fixes.
- **Single dispatch channel.** The configured queue is the only AFK handoff path; the handoff never references or invokes `envelope`.
- **Prose rosters are confirmed, never assumed.** Analysis of an unconfirmed prose-derived roster is a defect.
- **Wave 1 only.** Later waves enter via a fresh `/roundup` re-run on live tracker state; the pen sheet is a consumed seed, not maintained campaign state.
- **Reuse planning skills** (`spec`, `break-spec`) by recommendation; never reimplement their protocols here.
- Policy-check every side effect (`ticket.fetch`, `roundup.pensheet.write`, `ticket.queue.move`); `ask` requires approval, `deny` degrades to printed manual instructions.

## Run end

Write back probed capability entries to the probe cache as `kickoff` does (exclude `session_skip`, preserve doctor-owned fields). Finalize the run ledger with pens, verdicts, pen sheet path, and queue-move outcomes when active.

## Key principles

- One bounded judgment session: roster in, verdicts out, session ends.
- The human is the gate — reassignments between pens are the feature, not the exception.
- The tracker and the queue are the living state; roundup re-derives, it never maintains.
