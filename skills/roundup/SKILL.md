---
name: roundup
description: "Use when the user explicitly invokes /roundup or asks to triage one or more tickets into ordered AFK-ready, AFK-blocked, and HITL pens before kickoff. Writes an approval-gated pen sheet and only moves wave 1 AFK-ready tickets into the configured AFK queue when one exists. Never decomposes tickets inline or auto-routes onward."
---

# Roundup

The AFK intake gate.

Turn a ticket set into three pens: AFK-ready, AFK-blocked, and HITL.

Project config: `<repo>/.beislid/workflow.md`. Probe lazily; policy-check side effects per `action-policy-protocol.md`.

## Intent

- Accept explicit ticket ids or a prose roster/query plan.
- Prose requires explicit confirmation before analysis.
- Treat any ticket-authored `Validation/Test Plan` section as binding for AFK readiness.
- Use light, advisory overlap probing only: map ticket text to likely files, inspect just enough to flag conflicts, and never infer scope from filenames alone.

## Workflow

1. Read `workflow.md` and fetch tickets with `ticket_source`.
   - If `ticket_source.type: paste`, ask for pasted ticket bodies/acceptance criteria instead of guessing.
   - If `ticket_source.list_tool` is configured and the input is prose, turn the prose into a candidate roster/query plan, then stop for confirmation before analysis.
   - If no batch list tool exists, prose intake stops at guidance; require explicit ticket ids.
2. Triage each ticket.
   - **AFK-ready**: body is contract-grade (`Acceptance Criteria` plus `Validation/Test Plan`), no unresolved human decisions, and the ticket is conflict/dependency safe against the others.
   - **AFK-blocked**: automatable in principle, but the body is missing contract-grade pieces. Record the exact missing pieces and route (`spec` or `break-spec`); do not decompose inline.
   - **HITL**: needs a human in the loop. Order for kickoff sessions and parallel worktree planning.
3. Build waves.
   - Group AFK-ready tickets by dependency and parallel safety.
   - Wave 1 is the only wave eligible for AFK queue handoff.
   - Later waves stay in the pen sheet and become the seed for a rerun after wave 1 lands.
4. Approve and hand off.
   - After explicit per-pen approval, write `plans/<stem>-roundup.md` with waves, verdicts, ordering rationale, conflict flags, and per-ticket touch-area notes.
   - If `afk_queue` is configured, check action policy per ticket and move only wave 1 AFK-ready tickets into that queue.
   - If no AFK queue is configured, end with the pen sheet and routing guidance only.
5. Exit.
   - AFK-blocked gets spec/break-spec guidance.
   - HITL gets the ordered kickoff list.
   - Zero AFK-ready tickets is valid; do not queue anything.

## Guardrails

- Arrange-only; never enrich or silently rewrite ticket content.
- Never auto-route onward or couple to envelope/export semantics.
- Keep queue moves single-channel and wave-1-only.
- If conflict evidence is weak, flag it as advisory and let the human decide.
