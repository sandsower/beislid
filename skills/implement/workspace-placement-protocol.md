# workspace placement protocol v1

Load this file for configured isolation or mutating delegation, then load one host adapter.

## Operations

`ensure_orchestrator_workspace` owns the user-visible task-to-workspace association before the first repository write.
`place_mutating_delegate` owns an isolated mutation surface without creating a user-visible child task.
Only the orchestrator places mutating delegates in v1.

## Request

Build one normalized request with:

- run ID, flow, operation, strategy, and fallback
- source repository, exact SHA, objective, next skill, and write scope
- preparation command, runtime profiles, and integration order
- action-policy envelopes for requested side effects

Initialize or resume the external run ledger before automatic placement.
If unavailable, disable automatic parallel placement and cleanup and use the configured fallback.

## Capability

Capability is `verified-native`, `verified-manual`, or `unavailable`.
Only end-to-end conformance across placement, SHA, preparation, runtime, handoff, integration, and cleanup proves capability.

## Placement hard gates

Before mutation, require all of the following:

1. The destination is the requested repository on a fresh unique path and branch.
2. `HEAD` equals the full expected SHA exactly.
3. Tracked and untracked status is clean at the destination.
4. The source is clean when an orchestrator transition is requested.
5. Preparation exits zero, leaves tracked state unchanged, and passes readiness checks.
6. Action policy allows each transition, provision, lease, commit, or cleanup.
7. Concurrent delegates have disjoint authorized write scopes.
8. Every runtime profile has one verified atomic lease with all required bindings.

Never adopt or reuse an existing path or branch automatically.
Never keep sole progress under an ephemeral root.

Use `beislid workspace create --write-scope <pattern>` for manual placement, `preflight` for preparation, and `exec` for runtime delivery inside the recorded worktree.

## Receipt and handoff

Store `workspace-placement-receipt-v1` at `artifacts/workspaces/<placement_id>/receipt.json` in the run ledger.
Record identity, operation, capability, repository, SHAs, path, branch, clean state, creator, cleanup owner, run ID, and flow.
Runtime events record profile, lease ID, expiry, binding names, and keyed fingerprints, never binding values.

A mutating delegate returns the base SHA, commit list, clean status, changed paths, verification evidence, worktree path, and cleanup disposition.

Validate the handoff with `beislid workspace validate-handoff` before integration.
Reject wrong bases, scope drift, missing or unreachable commits, dirty state, or absent evidence.

## Integration

Start parallel delegates from one frozen SHA and declare their integration order before dispatch.
Cherry-pick committed handoffs serially and verify after each integration.
Stop the remaining batch on conflict or regression and retain every unintegrated placement.
Replan failed or dependent slices from the new SHA.

## Runtime and cleanup

The orchestrator owns lease lifecycle, the provider owns allocation, the adapter transports identity, and the delegate consumes bindings.
Missing, shared, partial, or unverified bindings make the placement unavailable for concurrent mutation.
Release is idempotent and reconciliation may reclaim only confirmed owned resources after action-policy authorization.

`cleanup_owner` is `host`, `beislid`, or `user`.
Use the host lifecycle for host-owned worktrees.
`beislid workspace cleanup --evidence-file <file>` removes only Beislið manual worktrees after integration, verification, reachability, clean handoff, lease release, and authorization pass.
Retain failed, conflicted, interrupted, unknown, dirty, or unintegrated placements for explicit recovery.
