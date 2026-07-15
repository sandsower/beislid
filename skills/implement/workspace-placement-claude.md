# workspace placement Claude adapter v1

This adapter describes target behavior and does not mark Claude support verified without the universal end-to-end conformance run.

## Orchestrator transition

When `orchestrator: native` is requested, Claude may use `EnterWorktree` before the first repository write.
Immediately verify the resulting repository root, dedicated branch, exact expected SHA, and clean state.
A native worktree created from the wrong base is rejected and follows the configured manual transition fallback.

Record host ownership in the placement receipt.
The task may continue in the same user-visible session only after both the host transition and Git preflight are acknowledged.

## Mutating delegates

Use a native isolated agent only when its host surface has passed conformance for a distinct worktree, enforceable working directory, runtime profile delivery, and committed handoff.
Otherwise provision a fresh Beislið manual worktree and launch the delegate only when the host can enforce its absolute path.
If neither path is verified, execute sequentially.

Do not dispatch nested mutating delegates in v1.
Read-only helpers remain allowed when they cannot write artifacts or external state.

Before dispatch, require the delegate to acknowledge its absolute root, branch, exact SHA, placement ID, write scope, runtime profiles, and next action.
Run preparation and runtime allocation only after destination preflight succeeds.

## Handoff and cleanup

The delegate returns clean committed changes and the universal handoff fields.
The orchestrator validates scope and commits, then integrates in declared order with verification after each cherry-pick.

Use `cleanup_owner: host` for `EnterWorktree` or other host-managed worktrees and call only the host cleanup lifecycle.
Use `cleanup_owner: beislid` for helper-created manual worktrees.
Retain any failed, interrupted, dirty, conflicted, or unintegrated placement.
