# kickoff step 1 ticket v1

Authoritative JIT protocol for kickoff Step 1. Load after workflow.md and probe cache init; if unreadable, stop.

## Purpose

Fetch enough ticket context to plan safely. Do not continue blind when ticket fetching fails.

## Protocol

Print the Step 1 entry one-liner from `kickoff-templates.md`.

### Extract ticket ID

Apply configured `branch_pattern` to `git branch --show-current`; capture group 1. If `ticket_source.id_pattern` case differs, normalize to that pattern. If no pattern matches, ask: `What is the ticket ID?`

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

Run actions in order after ticket fetch. Evaluate action policy for `lifecycle.kickoff_start.<name>`, using action metadata classes when present, otherwise `workspace-write` for local mutations and `network-read`/`git-remote` for external tracker writes. Substitute only `{ticket_id}`, `{id}`, `{branch}`, and `{event}` = `kickoff_start`; argv-pass or shell-quote values, never raw-splice branch/ticket text. `approval: auto` runs once configured. `approval: prompt` shows name/command and asks: run / skip this action / skip remaining / abort; silence or ambiguity means no side effect and prompts again or skips per choice.

Each action may set `on_failure: prompt | continue | abort`; omitted means `prompt`. On command failure:

- `prompt`: use the `kickoff-templates.md` lifecycle-action prompt: `(a)` retry, `(b)` skip remaining lifecycle actions this session, `(c)` abort. Skips are `session_skip` and excluded from probe cache writeback.
- `continue`: warn, record the failed action in lifecycle-action status, and continue.
- `abort`: stop kickoff with action name, command, exit status, and transcript-safe stderr/stdout summary. Do not run remaining lifecycle actions or write probe-cache updates.

## Exit

Print the Step 1 exit one-liner. Required outputs: `ticket_id`, title, body, acceptance criteria, labels/metadata, attachments/screenshots summary, ticket-source status, and lifecycle-action status.

## Tripwires

- Ticket-source failure `(b)` is strict paste fallback, not blind skip.
- Do not infer or search unrelated tickets when a ticket ID is absent.
- Lifecycle actions are side effects, not quality gates; do not silently ignore configured action failures or policy denials.
