# Beislið roundup — output templates

Roundup-specific copy: orientation, step one-liners, roster confirmation, pen sheet, verdict prompts, and terminal states. Loaded from `skills/roundup/SKILL.md` through the per-skill auxiliary symlink. Shared primitives live in `output-templates.md`.

## Orientation

≤240 chars:

```text
🐎 Roundup session for `<input>` on `<branch>`. I'll triage the set into AFK-ready / AFK-blocked / HITL pens, take per-pen verdicts, then write the pen sheet and move wave 1 to the queue. Cache: <fresh|stale|cold>.
```

## Step one-liners

Entry:

```text
🔄 Step 1: Intake — resolving the ticket roster.
🔄 Step 2: Analyze — judging readiness, touch areas, dependencies, conflicts.
🔄 Step 3: Sort — proposing pens and waves for verdicts.
🔄 Step 4: Handoff — writing the pen sheet and dispatching wave 1.
```

Exit:

```text
✓ Step 1: Roster confirmed — <N> tickets via <ids|query>.
✓ Step 2: Analyzed <N> — <a> meet the AFK bar, <b> below it, <c> human-shaped; <k> conflict flags.
✓ Step 3: Verdicts — AFK-ready <n> in <w> waves, blocked <m>, HITL <h>; <o> overrides.
✓ Step 4: Pen sheet <path|skipped>; queue moves <j>/<wave-1 size> <done|declined|unavailable>.
```

## Roster confirmation (prose-derived input)

```text
🔎 I read "<prose>" as: <filter summary from the query plan>.
Fetched <N> open tickets: <id — title, one per line>.
Confirm this roster, adjust the query, or add/remove ids. Analysis never starts on an unconfirmed prose-derived roster.
```

## Pen sheet template

Written to `plans/<stem>-roundup.md` after Step 3 verdicts:

```markdown
# Roundup — <stem> (<date>)

Source: <ids | interpreted query> · Repo: <remote> @ <base-sha> · Verdicts: <git identity>

## AFK-ready

### Wave 1 (dispatched)
- <ID> — <title>
  - Why safe: <contract-grade body; deps clear; conflict-free in wave>
  - Touch areas: <explored dirs/globs>

### Wave 2 (held — re-run /roundup after wave 1 lands)
- <ID> — <title> (after <ID>: <reason>)

## AFK-blocked — enrichment briefs
- <ID> — <title>
  - Missing: <exact gaps>
  - Spec questions: <2–3 targeted questions>
  - Route: /spec <ID>, then paste the approved sections into the ticket body (manual until a tracker-writeback lifecycle action exists), then re-run /roundup.

## HITL — kickoff order
1. <ID> — <title> — why human: <reason>

## Conflict flags (advisory)
- <ID> ↔ <ID>: <shared area> — <how it was resolved: sequenced | accepted | overridden>
```

## Per-pen verdict prompt

```text
Pen <name> (<n> tickets): <id list>
Verdict? (a) approve as listed, (m) modify — move tickets between pens or reorder, (r) reject pen — exclude from handoff entirely.
```

Modifications re-render the pen sheet preview; every pen gets an explicit verdict.

## Zero-AFK terminal

```text
💭 No tickets are AFK-ready — nothing will be queued (fail-closed: no queue moves).
Pen summary: <blocked briefs + HITL order>.
Next: /spec the blocked tickets, kickoff the HITL order, re-run /roundup after enrichment.
```

## Queue dispatch summary

```text
🚚 Wave 1 → <queue_ref>: <id list>. Later waves stay out by design — re-run /roundup on the remainder once this wave lands.
```

## Degradation — no afk_queue configured

```text
ℹ️ No `beislid:afk_queue` block in workflow.md — queue handoff unavailable. The pen sheet, wave ordering, and routing still stand; add the block via /setup to enable dispatch.
```

## Refusal — prose input without list_tool

```text
⛔ Prose input needs `ticket_source.list_tool` in workflow.md. Provide explicit ticket ids (or paste ticket content), or add the key via /setup.
```

## Char budgets

- Orientation: ≤240 chars.
- Step one-liners: ≤120 chars.
- Refusal/terminal messages: ≤700 chars.
