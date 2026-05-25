# kickoff step 1 ticket v1

Authoritative JIT protocol for kickoff Step 1. Load only after workflow.md and probe cache are initialized. If this file cannot be read, kickoff must stop rather than reconstructing ticket behavior from memory.

## Purpose

Fetch enough ticket context to plan safely. Do not continue blind when ticket fetching fails.

## Protocol

Print the Step 1 entry one-liner from `kickoff-templates.md`.

### Extract ticket ID

If `branch_pattern` is configured, apply it to `git branch --show-current` and capture group 1. If `ticket_source.id_pattern` is configured and the captured value's case does not match, normalize to the configured pattern's case. If no pattern matches or no branch pattern is configured, ask: `What is the ticket ID?`

### Fetch the body

If `ticket_source.type: paste`, ask for title, full body, acceptance criteria, and attachments/screenshots using the strict paste shape from `kickoff-templates.md`.

Otherwise `probe(ticket_source)` before fetching. For `mcp`/`cli`/`file` fetches that leave the local process or filesystem, evaluate action policy for `ticket.fetch` with class `network-read` or `read` as appropriate before fetching. On failure:

- `(a)` retry the probe.
- `(b)` means strict manual paste now — title, full body, acceptance criteria or `none`, attachments/screenshots or `none`.
- `(c)` abort.

Fetch based on `ticket_source.type`:

- **mcp:** call configured `tool` with the ticket ID; extract body and attachments/images when available.
- **cli:** run configured `command` with `{id}` substituted.
- **file:** read the file from configured `file_glob` that contains the ticket ID.
- **paste:** use the pasted title/body.

Summarize ticket title, body, labels/metadata, attachments, and acceptance criteria for later steps.

### Run `kickoff_start` lifecycle actions

If `lifecycle_actions.events.kickoff_start.actions` is configured, probe only that event as `lifecycle_actions.kickoff_start` before running actions. P0 supports `type: cli` only; for other types, stop and say the provider is reserved for a later Beislið version.

Run actions in configured order after ticket fetch succeeds. Evaluate action policy for `lifecycle.kickoff_start.<name>` before each configured action, using classes from action metadata when present, otherwise `workspace-write` for local mutations and `network-read`/`git-remote` for external tracker writes. Substitute only these placeholders: `{ticket_id}`, `{id}` (alias), `{branch}`, and `{event}` = `kickoff_start`. Placeholder values must be passed through argv construction when the host supports it, or shell-quoted before command execution; never splice raw branch/ticket text into a shell. `approval: auto` runs once configured. `approval: prompt` shows the action name/command and asks: run / skip this action / skip remaining lifecycle actions / abort; silence or ambiguity means no side effect and prompts again or skips per user choice. On command failure, use the lifecycle-action prompt from `kickoff-templates.md`: `(a)` retry this action, `(b)` skip remaining lifecycle actions this session, `(c)` abort. Skipped results are `session_skip` and excluded from probe cache writeback.

## Exit

Print the Step 1 exit one-liner. Required outputs: `ticket_id`, title, body, acceptance criteria, labels/metadata, attachments/screenshots summary, ticket-source status, and lifecycle-action status.

## Tripwires

- Ticket-source failure `(b)` is strict paste fallback, not blind skip.
- Do not infer or search unrelated tickets when a ticket ID is absent.
- Lifecycle actions are side effects, not quality gates; do not silently ignore configured action failures or policy denials.
