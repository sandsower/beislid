# workspace placement Codex adapter v1

This adapter describes target behavior and does not itself establish a verified Codex capability.

## Orchestrator transition

Codex task association and command working directory are separate state.
A current task cannot prove that it has transferred itself merely by creating or entering a worktree in the shell.

When native task worktree placement is requested, use the host task-fork or handoff surface and wait for a resolvable task identifier plus destination acknowledgment.
An asynchronous fork that returns only an unresolved client identifier is not success.
Return `manual-transition-required`, provide the created durable path when one exists, and stop before repository mutation.

Never infer that the task shown in the sidebar changed because `pwd`, `git status`, or a shell session points at another worktree.
The user-visible task transition must be acknowledged independently from Git preflight.

## Mutating delegates

Codex collaboration subagents are not assumed to have per-agent worktree or working-directory isolation.
Do not create a user-visible child task merely to represent a mutating subagent.

Native delegate placement is `verified-native` only after the collaboration surface proves a dedicated path, exact SHA, runtime profile delivery, and committed handoff end to end.
Manual delegate placement is `verified-manual` only when the orchestrator can provision a durable worktree and enforce that absolute path for every mutating command.
If path anchoring or runtime binding delivery cannot be enforced, return `unavailable` and execute the batch sequentially in the orchestrator-owned worktree.

Read-only subagents may share context only when they run no tests, generators, formatters, builds, database commands, or other artifact-producing work.
Treat any uncertain helper as mutating.

## Acknowledgment

Before dispatch, capture and compare:

- absolute `git rev-parse --show-toplevel`
- dedicated branch
- exact `git rev-parse HEAD`
- clean `git status --porcelain`
- placement ID and run-ledger receipt path
- active runtime profile names

The delegate must echo the acknowledged path, branch, SHA, placement ID, authorized scope, and next action before its first mutation.
Mismatch or missing acknowledgment stops dispatch.

## Handoff and cleanup

Require a clean committed handoff and validate it through the universal protocol before cherry-pick.
Codex task-created worktrees use `cleanup_owner: host` and the host lifecycle.
Beislið-created manual worktrees use `cleanup_owner: beislid` and remain retained until integration and all cleanup gates pass.
Unknown ownership is `user` and is never removed automatically.
