---
name: kickoff
description: Use when starting work on a ticket after checking out the feature branch. Fetches the ticket, explores the codebase, routes vague tickets through spec, routes large work through break-spec, then hands implementation-ready work to blueprint and implement. Adapts to whatever ticket tracker and domain tooling the environment provides — driven by `<repo>/.beislid/workflow.md`.
---

# Start Work on Ticket

Turn a checked-out feature branch and ticket into an implementation-ready plan. Kickoff is the front door of the Beislið lifecycle: ticket → context → spec/blueprint/breakdown → ticket update → `implement`.

**Don't use this for:** creating PRs, handling review/QA feedback, or PR handoff for completed work. Use `ready-for-review` or `review-response` for those.

Project config lives at `<repo>/.beislid/workflow.md` (typed-key fenced YAML blocks; format reference at `workflow-md-format.md`). Capabilities are probed lazily on first need per `probe-semantics.md`. Output prose follows `output-templates.md` and `kickoff-templates.md`.

---

## Read workflow.md

Read `<repo>/.beislid/workflow.md`. If missing, hard-fail and stop:

> 🛑 No `workflow.md` found in `.beislid/`. If this is a fresh project, run `/setup` to create one. If you moved your config, restore it to `<repo>/.beislid/workflow.md`.

Validate line 1 is exactly `<!-- beislid-workflow: v1 -->`. If missing or wrong, hard-fail and stop; kickoff will not silently mis-parse.

Compute cache identifiers:

```bash
repo_hash=$(git rev-list --max-parents=0 HEAD | sort | head -c 12)
workflow_hash=$(git hash-object .beislid/workflow.md)
```

Try to read `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/probes/<repo_hash>.json`:

- Missing → empty in-memory probe state; cache state `cold`.
- `workflow_hash` mismatch → empty in-memory probe state; cache state `stale`.
- Hash matches → load capability entries; cache state `fresh`. Per-cap freshness uses `probe_cache.ttl_hours`, default 24.

Print orientation prose from `kickoff-templates.md` (≤240 chars).

If the user is resuming with phrases such as `continue this ticket` or `continue from checkpoint`, read `.beislid/checkpoints/latest.json` when present before Step 1. Prefer a `kickoff_context_ready` entry matching the current branch and ticket ID when known; otherwise ask the user to choose among matching latest entries. Use the referenced checkpoint artifact as primary context for downstream planning, but still fetch or confirm the current ticket context before side effects. Missing or unreadable latest pointers are non-blocking; continue with normal kickoff.

## Internal: probe(<cap>)

Reusable lazy-probe contract. Do not re-probe within a run; the in-memory probe state is authoritative.

1. Look up `<cap>` in memory.
2. If present, `status: ok`, and within TTL → return ok; no probe ran.
3. Else run the probe per `probe-semantics.md` for the cap kind (`mcp`, `cli`, `file`, `paste`, `skill`, `subagent`, `path`). Multi-command logical CLI caps such as `lifecycle_actions.kickoff_start` probe every configured binary for the current event once. Record the result in memory.
4. On success → return ok.
5. On failure → use the call-site-specific prose prompt from `kickoff-templates.md` with retry / proceed-this-session fallback / abort.
6. On retry → re-probe. On fallback → mark `session_skip: true`; exclude from run-end writeback. On abort → stop and do not write cache.

On clean run end, write probed/re-probed capability entries back to `<repo_hash>.json`, excluding `session_skip`. Preserve top-level fields doctor owns; orchestrators do not update `doctor_run_at`.

## Global tripwires

- `.beislid/workflow.md` is the only project config source; no legacy YAML fallback.
- Do not execute a step from memory if its aux file cannot be read.
- Ticket-source fallback means strict pasted ticket context, not blind continuation.
- No implementation starts before approved design.
- Show and approve ticket update bodies before posting.
- CLI ticket updates must use `{body_file}`, never raw body interpolation.
- Lifecycle actions are configured side effects; run only supported providers and do not silently ignore failures.

## Step protocol loading

Complete steps in order. At each step entry, read the step aux file and follow it as the authoritative protocol. Do not execute a step from memory if the aux read fails; hard-fail and stop:

> 🛑 Could not read `skills/kickoff/<step-file>.md`. Kickoff cannot safely execute this step from memory; reinstall Beislið or restore the file.

When `BEISLID_VERBOSE=1`, print one aux load stamp after successfully reading a step file, e.g. `✓ kickoff/step-1-ticket v1 loaded`, and include step exit checks in the transcript/output when practical.

## Checklist and required outputs

1. **Ticket** — read `step-1-ticket.md`. Outputs: `ticket_id`, title, body, acceptance criteria, labels/metadata, attachments/screenshots summary, ticket-source status, lifecycle-action status.
2. **Context** — read `step-2-context.md`. Outputs: relevant files/patterns/tests/docs, domain context status, open uncertainties.
3. **Team guidance** — read `step-3-team-guidance.md`. Outputs: team config status and constraints.
4. **Readiness** — read `step-4-readiness.md`. Outputs: route to `spec` or blueprint path, with rationale.
4b. **Checkpoint** — read `step-4-checkpoint.md`. Outputs: `kickoff_context_ready` checkpoint artifact/pointer status when configured.
5. **Scope** — read `step-5-scope.md`. Outputs: `single PR` or `needs breakdown`, with selected phase if any.
6. **Blueprint** — read `step-6-blueprint.md`. Outputs: approved design summary, expected files/modules, tests, risks/open questions.
7. **Discoveries** — read `step-7-discoveries.md`. Outputs: discovery status and any durable notes recorded.
8. **Ticket update** — read `step-8-ticket-update.md`. Outputs: update status/body and implement handoff context.

## Run end: write back probe cache

After Step 8 or a clean routed handoff, write in-memory probe state to `<repo_hash>.json`: update probed/re-probed entries, exclude `session_skip: true`, preserve `doctor_run_at`, update `workflow_hash`, and keep the workflow TTL. If workflow.md changed mid-run or the run aborted, do not overwrite stale state.

## Common mistakes

- Continuing without ticket context.
- Treating `knowledge_store.path` as useful alone.
- Posting ticket updates without approval.
- Dropping ticket + codebase findings + domain summary + team config between gates.

## Key principles

- Workflow.md is the source of truth.
- Lazy probes, not preflight tables.
- No blind planning.
- Blueprint before implement.
