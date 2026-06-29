# Worktree isolation for agent work

Beislið treats git worktrees as the isolation layer for repo-mutating agent work when a task needs to stay separate from the main checkout.

## Policy

- Prefer an isolated worktree when a slice will edit repo files, especially when parallel work or experiments are involved.
- Keep the default checkout path available for read-only or low-risk work.
- Do not silently delete a worktree after use; cleanup is always explicit.
- Clean-eval remains separate: it validates PR readiness in a clean surface, but it is not the same thing as day-to-day agent isolation.

## When to recommend or create one

- **Recommend** a worktree when the current checkout is shared, dirty, or otherwise unsafe for mutation.
- **Create or reuse** a worktree only when the workflow already has an explicit isolated-session boundary or another configured boundary that clearly owns fresh-surface creation.
- If a workflow does not own the boundary, Beislið should surface the recommendation and keep the choice explicit.

## Safety checks before implementation starts

Before the first file mutation in a slice, the workflow should preserve the current checkout/worktree context and decide whether the work belongs in an isolated worktree.
If the task would otherwise contaminate the main checkout, surface the recommendation early so the operator can move the slice before edits begin.

## Flow-specific notes

- **kickoff / implement**: capture the active checkout/worktree context and use it to decide whether isolation should be recommended before code changes.
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
