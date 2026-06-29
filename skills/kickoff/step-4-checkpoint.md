# kickoff step 4 checkpoint v1

Authoritative JIT protocol for kickoff checkpoint handling. Load after Step 4 readiness has decided the route and before Step 5 scope.

## Purpose

Optionally write a boundary checkpoint artifact once kickoff context is ready to seed planning/design in a fresh context.

## Protocol

Print the checkpoint entry one-liner from `kickoff-templates.md`.

If `lifecycle_actions.events.kickoff_context_ready.actions[]` is not configured, skip and continue to Step 5.

Run configured `kickoff_context_ready` actions. This event means the kickoff context packet is ready to seed the next planning/design context, so it runs after readiness routing.

Supported P0 action shape:

```yaml
- name: write-kickoff-context-checkpoint
  type: artifact
  approval: prompt
  on_failure: prompt # optional; prompt when omitted, or continue | abort
  path: 'checkpoints/{event}-{ticket_id}.md'
```

Before each checkpoint artifact write, evaluate action policy for `checkpoint.kickoff_context_ready.<name>` with class `workspace-write`. Execute only `type: artifact`; skip other providers as reserved. Use the same artifact safety posture as `spec`/`blueprint`: omitted `approval` means `prompt`; `auto` writes only a missing target; existing targets always prompt for overwrite / choose path / skip; omitted `on_failure` means `prompt`. Skip, reserved actions, and policy denials do not block kickoff routing; record the skipped/denied status. On failed writes, `prompt` asks retry / skip or explicitly override / abort before routing, `continue` warns and routes without the checkpoint, and `abort` stops before Step 5.

Default path: `checkpoints/{event}-{ticket_id}.md` when ticket context is known, otherwise `checkpoints/{event}-{feature}.md`. Supported placeholders are `{event}` (`kickoff_context_ready`), `{feature}`, `{kind}` (`checkpoint`), and `{ticket_id}`. Derive `{feature}` from ticket title, then branch; ask if none. Paths must be relative repo-local `.md` files with no `..`.

Checkpoint content is human-readable Markdown with stable sections: `Checkpoint Metadata`, `State Summary`, `Key Context`, `Decisions`, `Next Step`, `Open Risks / Questions`, and optional `Related Artifacts`. Include ticket, branch, source skill `kickoff`, event, readiness route, acceptance criteria, attachments, codebase findings, domain/team status, uncertainties, and approved spec summary/lifecycle status when spec ran. Do not add unapproved implementation decisions.

After a checkpoint write, update `.beislid/checkpoints/latest.json` with replaceable latest-pointer metadata: event, path, `ticket: {id, title}` when known, branch, source skill, and timestamp when available. This is convenience rediscovery state only: no run ID, history, gate logs, or resume state machine. Report pointer update failures without changing the artifact result.

When a checkpoint is written, print host-neutral fresh-context guidance and pause: this is a safe point to run `/clear` or `/new`; after restarting, say `continue this ticket` or `continue from checkpoint`. Do not invoke `/clear` or `/new` automatically.

## Exit

Print the checkpoint exit one-liner. Required outputs: checkpoint status (`written`, `auto-written`, `skipped`, `not configured`, `failed`, or `reserved`), checkpoint path when written, pointer status, and whether the user chose to continue in the same context.

## Tripwires

- Do not run checkpoint actions before readiness routing is known.
- Do not treat `.beislid/checkpoints/latest.json` as a run ledger.
- Do not invoke host context-clearing commands automatically.
