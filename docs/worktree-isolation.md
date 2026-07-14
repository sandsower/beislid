# Worktree isolation for agent work

Beislið treats git worktrees as the isolation layer for repo-mutating agent work when a task needs to stay separate from the main checkout.

## Policy

- Use an isolated worktree when a slice will edit repo files in parallel with another actor or when the active checkout is shared, dirty, or reserved for coordination.
- Keep the default checkout path available for read-only or low-risk work.
- Allow only one mutating agent to own a worktree at a time.
- Every parallel mutating agent must have a different dedicated worktree and branch before dispatch.
- Read-only agents may share a worktree when they run no mutating commands or generators.
- Do not silently delete a worktree after use; cleanup is always explicit.
- Clean-eval remains separate: it validates PR readiness in a clean surface, but it is not the same thing as day-to-day agent isolation.

## When to recommend or create one

- **Recommend** a worktree when the current checkout is shared, dirty, or otherwise unsafe for mutation.
- **Create or reuse** a worktree only when the workflow already has an explicit isolated-session boundary or another configured boundary that clearly owns fresh-surface creation.
- **Parallel mutating delegation is an owned boundary**: the orchestrator must provision or verify one dedicated worktree per mutating delegate before dispatch.
- If the host cannot provision distinct worktrees, execute the batch sequentially in one owned worktree.
- If a workflow does not own the boundary, Beislið should surface the recommendation and keep the choice explicit.

## Safety checks before implementation starts

Before the first file mutation in a slice, the workflow should preserve the current checkout/worktree context and decide whether the work belongs in an isolated worktree.
If the task would otherwise contaminate the main checkout, surface the recommendation early so the operator can move the slice before edits begin.

Before dispatching a mutating agent, verify and record:

- the absolute worktree path from `git rev-parse --show-toplevel`
- a dedicated non-default branch for the assigned slice
- a clean starting state, or explicitly preserved changes owned by the same slice
- a path distinct from the orchestrator and every other mutating delegate
- the worktree's cleanup path: keep, merge, PR, or discard

Do not keep the sole copy of uncommitted progress under `/tmp` or another ephemeral directory.

## Runtime isolation

A worktree does not isolate external mutable state.
Concurrent mutating agents must also receive distinct runtime resources, including application and test-server ports, database project identities and ports, generated artifact directories, and hard-unique migration identifiers.
If those resources cannot be isolated, do not run the conflicting commands concurrently.

## Flow-specific notes

- **kickoff / implement**: capture the active checkout/worktree context before code changes and hard-gate parallel mutating delegation on distinct verified worktrees.
- **ready-for-review**: keep worktree/branch context visible in the handoff so reviewers can understand which checkout to inspect and how cleanup should happen.
- **review-response**: preserve the same worktree context when fixing feedback so follow-up edits stay in the intended isolated surface.
- **handoff**: copy-only; it may recommend a separate worktree for the receiving agent, but it does not create one.

## Cleanup paths

Document the cleanup path explicitly for each isolated slice:

- keep
- merge
- PR
- discard

These are workflow decisions, not hidden automation.
