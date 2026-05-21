# Beislið kickoff — output templates

Kickoff-specific copy: orientation, step one-liners, paste fallback prompts, ticket-update prompts, and domain-pair notes. Loaded from `skills/kickoff/SKILL.md` through the per-skill auxiliary symlink. Shared primitives live in `output-templates.md`.

## Orientation

≤240 chars:

```
📋 Starting `<ticket-id>` on `<branch>`. Reading `.beislid/workflow.md`; ticket, domain, and update capabilities will be probed only when needed. Cache: <fresh|stale|cold>.
```

If the ticket ID is not known yet:

```
📋 Starting work on `<branch>`. Reading `.beislid/workflow.md`; I’ll ask for the ticket ID if the branch doesn't provide it. Cache: <fresh|stale|cold>.
```

## Step one-liners

Entry:

```
🔄 Step 1: Ticket — fetching the request and attachments.
🔄 Step 2: Context — exploring code, configured explore skills, and optional domain knowledge.
🔄 Step 3: Team guidance — checking local team notes if present.
🔄 Step 4: Readiness — deciding whether this needs spec first.
🔄 Step 4b: Checkpoint — writing kickoff context artifact if configured.
🔄 Step 5: Scope — checking whether this fits one PR.
🔄 Step 6: Blueprint — designing the implementation.
🔄 Step 7: Discoveries — recording new domain knowledge if configured.
🔄 Step 8: Ticket update — posting or printing the approved plan.
```

Exit:

```
✓ Step 1: Ticket loaded — <summary>.
✓ Step 2: Context gathered — <N> files, explore <default|replace|enhance>, domain <used|skipped>.
✓ Step 3: Team guidance <found|not configured>.
✓ Step 4: Readiness decided — <spec|blueprint>.
✓ Step 4b: Checkpoint <status>.
✓ Step 5: Scope decided — <single PR|needs breakdown>.
✓ Step 6: Blueprint approved.
✓ Step 7: Discoveries <recorded|skipped>.
✓ Step 8: Plan <posted|printed>; handing to implement.
```

## ticket_source paste fallback

When `ticket_source` probe fails and the user chooses `(b)`, do not continue blind. Ask for structured paste:

```
⚠️ Using pasted ticket context for this run. Config stays unchanged and probes will retry next run.

Paste the ticket in this shape:
- Title:
- Full body:
- Acceptance criteria: <text or none>
- Attachments/screenshots: <links, descriptions, or none>
```

## explore.skill failure

When `explore.mode: replace` is configured and the skill fails, do not continue blind:

```
⚠️ The explore replacement skill `<skill>` failed: <reason>.
Default exploration can still run, but the configured replacement did not provide context.
What now? (a) retry, (b) fall back to default exploration this session, (c) abort.
```

For `explore.mode: enhance`, failed skill context is non-blocking:

```
💭 Explore enhancer `<skill>` unavailable — continuing with default exploration findings.
```

## lifecycle_actions failure

When a configured `kickoff_start` lifecycle action fails:

```text
⚠️ Lifecycle action `<name>` failed: <reason>.
This side effect did not complete, but no code changed.
What now? (a) retry this action, (b) skip remaining lifecycle actions this session, (c) abort.
```

## ticket_update fallback

When `ticket_update` is absent, manual, skipped, or fails and the user proceeds without it:

```
💭 Ticket update isn't available for this run — I'll print the plan here so you can post it manually.
```

Probe failure prompt:

```
⚠️ The capability `ticket_update=<value>` failed: <reason>.
The implementation plan is still ready; only posting back to the tracker is blocked.
What now? (a) retry, (b) print the update for manual posting, (c) abort.
```

## Domain-pair notes

`domain_expert.agent` alone is useful for read-only kickoff context:

```
💭 Domain expert configured without `knowledge_store.path` — I'll use it for context, but skip discovery recording.
```

`knowledge_store.path` alone is not useful for kickoff context:

```
⚠️ `knowledge_store.path` is set but `domain_expert.agent` isn't — discovery recording needs both, so I'll skip it.
```

When no new durable discovery was found:

```
💭 No new domain knowledge surfaced — skipping discovery recording.
```

## Char budgets

- Orientation: ≤240 chars.
- Step one-liners: ≤120 chars.
- Probe failure prompt: ≤700 chars.
