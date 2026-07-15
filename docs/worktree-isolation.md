# Worktree isolation for agent work

Beislið uses Git worktrees as one layer of isolation for repository-mutating agent work.
A worktree does not isolate external mutable state.
A worktree does not isolate databases, ports, services, generated artifacts, or host task association, so those concerns have separate gates.

## Two placement boundaries

`ensure_orchestrator_workspace` owns the user-visible top-level task transition before the first repository write.
`place_mutating_delegate` owns a mutating subagent workspace without creating a user-visible child task.

These boundaries are distinct because changing a shell working directory does not prove that a host task is associated with that worktree.
Likewise, creating a new user-visible task is not required to isolate a subagent when the host can enforce a dedicated working directory.

## Workflow activation

The optional `beislid:agent_isolation` block declares desired strategy and fallbacks.
An absent block preserves legacy behavior and does not opt into native placement.
Host adapters report only `verified-native`, `verified-manual`, or `unavailable`, based on end-to-end conformance rather than configuration, documentation, or tool presence.
Positive evidence must come from a trusted end-to-end runner and be fresh and bound to the requested host, operation, adapter build, repository, and proof artifacts.
The current distribution has no trusted runner, so synthetic evidence remains unavailable.

If the selected capability is unavailable, use the configured manual transition or sequential delegate fallback.
Never infer success from `pwd`, a created directory, an unresolved host task identifier, or a version string.

## Codex delegate context

Codex context transport is separate from mutation isolation.
Immediately before a Codex subagent dispatch, `implement` loads its Codex delegate-context protocol and builds a self-contained packet from the approved artifact and current repository facts.
When supported by the host, a complete packet permits no-history context forking by default.
Missing packet fields stop dispatch, and conversation context is narrowed to the smallest bounded recent context needed for a named gap.
Claude, Pi, generic, and future host adapters keep their existing transport behavior.

The normal external Beislið state location remains the default.
A Codex run may opt into workspace-local state through the existing `BEISLID_STATE_DIR` environment variable only when the selected path is inside the repository, untracked, and confirmed ignored by `git check-ignore`.
Beislið does not create or use an unsafe local state path, and it never edits `.gitignore` automatically.

## Fresh placement

Every automatic placement receives a fresh unique worktree path and branch from the exact requested SHA.
Beislið never adopts or reuses an existing path or branch automatically because names do not prove ownership, base commit, cleanliness, or lifecycle state.
`workspace create` requires `--operation ensure_orchestrator_workspace` or `--operation place_mutating_delegate` so the receipt preserves the correct boundary.

The portable root order is:

1. `BEISLID_WORKTREE_ROOT` when set by the runtime.
2. Workflow `manual_root` when configured.
3. `<repo-parent>/<repo-name>-worktrees` for `repo-sibling`.

Do not use `/tmp`, `/private/tmp`, `/var/tmp`, another ephemeral root, or a location inside the source repository as the sole progress copy.

## Hard gates before mutation

Every parallel mutating agent must have a different dedicated worktree and branch before dispatch.
Require and record:

- the absolute destination from `git rev-parse --show-toplevel`
- a dedicated non-default branch
- exact equality between `HEAD` and the full expected SHA
- clean tracked and untracked status
- a clean source before a requested top-level transition
- successful configured preparation with no tracked changes
- successful readiness checks
- an allowed action-policy envelope for the concrete side effect
- disjoint authorized write scopes for concurrent delegates
- a verified atomic runtime lease for every required profile

Reject a host-created worktree that starts from the wrong SHA.
Stop before mutation when the destination cannot acknowledge its path, branch, SHA, placement ID, scope, runtime profiles, and next action.
Parallel manual placements share one `--concurrency-group`; Beislið serializes placement and rejects definite or potential overlap with active receipts in that group.

## Durable receipts

Automatic placement requires a running external Beislið run ledger.
The receipt lives at `artifacts/workspaces/<placement_id>/receipt.json` inside that run and uses `workspace-placement-receipt-v1`.

The receipt records repository and workspace identity, operation, expected and actual SHA, declared `scope.write` patterns, placement status, capability, clean state, creator, and cleanup owner.
Manual creation records `placement_status: verified` for the checked instance but keeps host `capability: unavailable` until a trusted conformance runner exists.
The run ledger rejects incomplete or malformed versioned receipts before persisting them.
Placement lifecycle events record runtime leases, handoff validation, integration, retention, and cleanup.
Workspace placement does not create a second state directory automatically.

Runtime binding values live in permission-restricted external secret state.
Ledger evidence contains only profile, lease ID, expiry, binding names, and keyed fingerprints.

## Runtime isolation

One atomic runtime profile may bundle primary, shadow, analytics, and other database entrypoints together with caches, queues, ports, or services.
The orchestrator owns lease lifecycle, the configured provider owns allocation semantics, the host adapter transports placement identity, and the delegate only consumes bindings.
`beislid workspace lease --workflow-file .beislid/workflow.md --profile <name>` deterministically materializes the selected normalized profile into the runtime lease contract.

Missing, empty, partial, shared, or unverified bindings fail the whole profile and prevent concurrent mutation.
Partial allocation triggers best-effort release.
Lease allocation is serialized per placement and profile, and an expired lease cannot complete allocation or deliver bindings.
Run delegated commands through `beislid workspace exec` so binding delivery stays out of prompts and command arguments.

## Handoff and integration

Mutating delegates return committed changes from a clean worktree, with base SHA, final commits, changed paths, verification evidence, and cleanup disposition.
The orchestrator rejects scope drift, dirty state, missing or unreachable commits, unexpected bases, and absent evidence.
It passes that envelope to `beislid workspace validate-handoff` before integration.

Parallel delegates start from one frozen SHA and declare integration order before dispatch.
The orchestrator cherry-picks handoffs serially and verifies after each integration.
Cleanup evidence maps every source commit to its reachable cherry-picked commit, and Beislid verifies patch equivalence before deleting its branch.
A conflict or regression stops the remaining batch and retains all unintegrated placements for recovery.

## Cleanup ownership

`cleanup_owner` is `host`, `beislid`, or `user`.
Host-owned worktrees use only the host lifecycle.
Beislið removes only manual worktrees it created.
Unknown ownership is user-owned and never removed automatically.

Automatic Beislið cleanup requires clean handoff, successful integration and verification, commit reachability, runtime release, and an allowed `agent.workspace.cleanup` action.
The orchestrator supplies those facts as `workspace-cleanup-evidence-v1` to `beislid workspace cleanup --evidence-file <file>`.
Retain failed, conflicted, interrupted, dirty, unknown, or unintegrated placements.

Doctor may report stale worktrees, expired leases, and orphan candidates from receipts and read-only Git state.
Doctor never removes worktrees or releases and reclaims runtime resources.
