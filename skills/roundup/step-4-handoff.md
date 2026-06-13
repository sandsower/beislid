# roundup step 4 handoff v1

Authoritative JIT protocol for roundup Step 4. Load only after Step 3 verdicts exist for every pen.

## Purpose

Write the pen sheet, dispatch wave 1 to the configured queue, and route. Everything here is mechanical; no new judgments.

## Protocol

Print the Step 4 entry one-liner from `roundup-templates.md`.

### Write the pen sheet

Evaluate action policy for `roundup.pensheet.write` with class `workspace-write`. Render the approved pens — and only approved content — into `plans/<stem>-roundup.md` per the template in `roundup-templates.md`, including verdict identity, source description, repo pin (`git rev-parse HEAD`), overrides, and conflict-flag resolutions. An existing target always prompts: overwrite / choose another path / skip. A skipped or failed write is reported and does not block the queue dispatch.

### Dispatch wave 1 (queue moves)

Only when `beislid:afk_queue` is configured; otherwise print the degradation copy from `roundup-templates.md` and skip to routing.

1. `probe(afk_queue)` lazily per `probe-semantics.md`.
2. Print the queue dispatch summary (wave-1 ids → `queue_ref`).
3. Evaluate action policy for `ticket.queue.move` (tracker write) once for the wave boundary; `ask` is answered once for the listed set — per-ticket re-asking would duplicate the approval. `deny` prints the manual move instructions and continues to routing.
4. On allow/approval, move each wave-1 ticket into `queue_ref` via `move_tool`. Record per-ticket outcomes; report partial failures verbatim and never roll back completed moves.

**Wave 1 only.** Later waves never move in this run — membership in the queue is the run trigger, and ordering is only enforceable by what enters it. Zero AFK-ready tickets: print the zero-AFK terminal copy instead; no moves.

### Routing close

- **HITL pen** — the ordered kickoff list, verbatim from the pen sheet.
- **AFK-blocked pen** — `/spec <id>` per brief; paste approved sections into the ticket body (manual until a tracker-writeback lifecycle action exists); then re-run `/roundup`.
- **Remainder** — "re-run `/roundup` on the remaining tickets once wave 1 lands"; the live tracker is the state, the pen sheet is a consumed seed.

### Finalize

Write back probed capability entries to the probe cache as `kickoff` does. Finalize the run ledger with pens, verdicts, overrides, pen sheet path, queue-move outcomes, and policy envelopes when active.

## Exit

Print the Step 4 exit one-liner. Required outputs: pen sheet path (or skip reason), per-ticket move outcomes, routing summary.

## Tripwires

- Nothing in this step runs without Step 3 verdicts; unapproved content never reaches the pen sheet or the queue.
- Waves 2+ never move, no matter how confident the analysis.
- Single channel: this step never references or invokes `envelope`; the queue is the only dispatch path.
- Policy-check every side effect; a `deny` degrades to printed manual instructions, never to silence.
