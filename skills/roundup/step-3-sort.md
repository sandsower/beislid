# roundup step 3 sort v1

Authoritative JIT protocol for roundup Step 3. Load after all analysis cards exist.

## Purpose

Propose pens and waves from the Step 2 cards, then collect explicit per-pen human verdicts. Approval here is what makes any handoff possible; nothing approves itself.

## Protocol

Print the Step 3 entry one-liner from `roundup-templates.md`.

### Propose pens

- **AFK-ready** — meets the AFK bar, not human-shaped, no external blockers.
- **AFK-blocked** — automatable in principle but below the bar or externally blocked. Each entry is an **enrichment brief**: the exact gaps from its card plus 2–3 targeted spec questions, formatted per the pen sheet template. Route: `/spec`, manual paste of approved sections into the ticket body, re-run `/roundup`.
- **HITL** — human-shaped work, ordered for kickoff sessions with a one-line rationale per position.

### Propose waves (AFK-ready only)

- **Wave 1**: tickets with no unresolved dependency edges and no conflict flags against other wave-1 members. Every member carries a per-ticket justification naming both facts.
- **Later waves**: ordered by dependency edges; conflicting same-wave candidates are split across waves with the shared area named as the reason.
- Inferred edges count as real for wave assignment unless the human overrides.

### Collect verdicts

Render the pen sheet preview from `roundup-templates.md`, then ask the per-pen verdict prompt for each pen — AFK-ready (including its wave structure), AFK-blocked, HITL:

- **approve** — pen joins the handoff as listed.
- **modify** — the human moves tickets between pens, reorders, or merges/splits waves. Record each override with its reason; re-render; ask again. Reassignments are the point of the gate, not exceptions.
- **reject** — pen is excluded from handoff entirely; record why.

Silence, ambiguity, or a blanket "yes to everything" is not approval; walk each pen. A modification that contradicts an analysis card (e.g. "this actually meets the bar") goes back to Step 2 to update the card — sort never edits analysis substance inline.

### Terminal states

- **AFK-ready non-empty** — continue to Step 4 with all approved pens.
- **AFK-ready empty** (by analysis or verdict) — still continue to Step 4: the pen sheet, briefs, and HITL order remain the deliverable; Step 4 prints the zero-AFK terminal copy and performs no queue moves.

## Exit

Print the Step 3 exit one-liner. Required outputs: approved pens with verdicts and reasons, wave structure with per-ticket justifications, recorded overrides, verdict identity (`git config user.name`).

## Tripwires

- Per-pen verdicts; a prior blanket approval never substitutes.
- Every wave-1 member is individually justified (deps + conflicts).
- Blocked-pen entries below enrichment-brief quality go back to Step 2.
- Sort assigns and orders; it never decomposes, enriches, or edits tickets.
