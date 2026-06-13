# roundup step 1 intake v1

Authoritative JIT protocol for roundup Step 1. Load after workflow.md and probe cache are initialized.

## Purpose

Resolve the input into a confirmed ticket roster. Do not analyze, enrich, or decompose anything at intake.

## Protocol

Print the Step 1 entry one-liner from `roundup-templates.md`.

### Detect input kind

In order:

1. **Ticket-id list** — every comma/whitespace-separated token matches `ticket_source.id_pattern`. `probe(ticket_source)`, evaluate action policy for `ticket.fetch` (`network-read`), and fetch each ticket's title, body, state, and relations as `kickoff` Step 1 does, including the strict paste fallback on probe failure. Print the roster; no confirmation gate — the user already enumerated the set.
2. **Prose** — anything else (e.g. "the audit tickets", "this cycle's P1s"). Requires `ticket_source.list_tool`; if absent, print the refusal from `roundup-templates.md` and stop for ids or pasted content. Otherwise ground a query plan against the tool's **actual** filter schema — inspect its parameters; never invent filters it does not expose. Evaluate `ticket.fetch` (`network-read`) and fetch.
3. **Mixed** — fetch the ids, treat the remainder as prose, union the results; the union counts as prose-derived.

### Roster confirmation gate

Prose-derived rosters are never silently accepted. Present the interpreted query and fetched roster using the confirmation copy from `roundup-templates.md`. The user may confirm, adjust the query (iterate — fetches are read-only and cheap), or add/remove individual ids. Repeat until explicitly confirmed.

Tickets in terminal states (done/cancelled/duplicate) are excluded by default; note the exclusion and include one only on explicit request.

### Derive the stem

Slug for `plans/<stem>-roundup.md`: from the prose phrase or the ticket-id range (e.g. `audit-sweep`, `bei-12-20`): lowercase, non-alphanumeric runs → `-`, collapse repeats, strip edge `-`, ≤60 chars. Confirm with the user. Collisions with an existing pen sheet are handled at write time in Step 4 (existing targets always prompt).

## Exit

Print the Step 1 exit one-liner. Required outputs: confirmed roster (ids, titles, bodies, states, relations cached in session), source description (id list or interpreted query), stem.

## Tripwires

- Analysis never starts on an unconfirmed prose-derived roster.
- Never invent `list_tool` filters; the tool's schema is the vocabulary.
- Closed tickets stay out unless explicitly pulled in.
- Intake reads tickets; it never writes, enriches, or decomposes them.
