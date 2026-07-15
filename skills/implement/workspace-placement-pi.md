# workspace placement Pi adapter v1

This adapter describes target behavior and requires end-to-end conformance before any capability is reported as verified.

## Orchestrator transition

Pi does not assume a native same-session task transition.
For `orchestrator: manual`, create a durable manual worktree, print its absolute path and expected SHA, and require a relaunch from that directory.
Return `manual-transition-required` and stop before the first repository write in the old process.

After relaunch, verify root, branch, exact SHA, clean state, placement receipt, and the intended next skill before mutation.

## Mutating delegates

Pi may use a manually provisioned worktree with `subagent_start(cwd=...)` only after conformance proves that the child remains anchored to that directory for every mutating command.
The orchestrator provisions one fresh path and branch per delegate and passes the absolute path as `cwd`.
The child acknowledges root, branch, SHA, placement ID, scope, runtime profiles, and next action before mutation.

If `cwd` enforcement or runtime delivery is unavailable, do not dispatch parallel mutating children.
Run sequentially in the orchestrator-owned worktree.
Read-only helpers may share only when they produce no artifacts or external mutations.

## Runtime and handoff

Run delegate commands through `beislid workspace exec` when a runtime profile is required.
Do not pass binding values in prompts, command arguments, receipts, or transcripts.
Require a clean committed handoff and validate it with the universal protocol before integration.

## Cleanup

Pi manual worktrees normally use `cleanup_owner: beislid`.
Release runtime leases first, then remove the worktree only after integration, verification, reachability, clean state, and action-policy authorization.
Retain uncertain or failed placements for explicit recovery.
