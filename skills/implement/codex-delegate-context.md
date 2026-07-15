# Codex delegate context v1

Load this file just in time before a Codex subagent dispatch, or when a smoke fixture explicitly requests protocol proof.
This is a transport contract, not proof that the current host exposes every control it names.
In verbose mode, emit `✓ implement/codex-delegate-context v1 loaded` immediately after reading this file.

## Complete packet

Build a self-contained packet from durable artifacts and current repository facts.
Include:

- objective and focused task
- approved artifact path plus the relevant requirements or decisions
- workspace receipt and placement ID when mutation isolation applies
- repository root, branch, and exact SHA
- authorized scope and relevant files
- success criteria and required gates
- action-policy boundaries that affect the delegate
- handoff contract, including expected evidence and commit behavior

Do not replace durable artifact paths with a conversation summary.
Do not include unrelated history, broad repository dumps, secrets, or runtime binding values.
The delegate must acknowledge the exact SHA, authorized scope, success criteria, required gates, and handoff contract before work.

## Context selection

When the Codex collaboration surface exposes context forking and the packet is complete, dispatch with `fork_turns: "none"` by default.
When the delegate needs a conversation detail that cannot be recovered from durable artifacts or repository state, pass the smallest bounded recent context that resolves the named gap and record the reason in the packet.
Full-history delegation is an explicit exception for a named dependency that bounded context cannot satisfy.
Never use full history as the default.

When the host does not expose a context-fork control, use its supported dispatch surface without claiming that history was omitted.
Packet completeness remains required.
If required packet fields are missing, stop before dispatch and resolve them.

## Workspace-local state

The normal external Beislið state location remains the default.
Workspace-local state is opt-in only when `BEISLID_STATE_DIR` is explicitly set to a path inside the current repository.
Before creating or using that path, resolve it under the repository root and run `git check-ignore -q -- <relative-path>` from the root.
Proceed only when the command succeeds and the path is not tracked.
If the path escapes the repository, is tracked, is not ignored, or cannot be checked, do not create or use it.
Fall back to normal external state and disclose why the optimization was skipped.
Never edit `.gitignore` automatically.

## Handoff

Read-only delegates return findings and evidence without creating artifacts.
Mutating delegates continue to use the workspace-placement protocol and return its clean committed handoff.
Context minimization never relaxes isolation, verification, action-policy, or run-ledger requirements.
