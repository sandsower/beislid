# Worktree Support for Isolated Agent Work

## Problem Statement
Beislið can coordinate ticketed work, review handoff, and checkpoints, but it does not yet describe how an agent should keep repo-mutating work isolated from the main checkout.

## Current State
- Kickoff routes ticket work and can hand off through checkpoints.
- Ready-for-review and review-response understand clean-eval and PR handoff, but they do not explicitly preserve or explain worktree context.
- Handoff is copy-only and currently warns against creating worktrees itself.
- Clean-eval already models a clean worktree/container surface for PR verification, but that is separate from day-to-day isolated agent work.

## Desired State
- When a workflow is about to mutate repo files, Beislið can recommend an isolated git worktree instead of continuing in the shared checkout.
- When a fresh isolated boundary already exists, Beislið can treat that worktree as the working surface for the slice.
- Ready-for-review and review-response preserve enough branch/worktree context that a later step can verify, review, and clean up the right checkout.
- Cleanup remains explicit: keep, merge, PR, or discard.

## User Stories
- As an agent operator, I want Beislið to steer mutating work into an isolated worktree so the main checkout stays clean.
- As a reviewer, I want PR handoff notes to make the active worktree/branch obvious.
- As a maintainer, I want cleanup paths documented so failed experiments can be handled without guesswork.

## Key Decisions
- Default policy: recommend-first, not silent auto-creation.
- Auto-creation is reserved for explicit isolated-session boundaries, not every skill invocation.
- This ticket is about workflow semantics and documentation; no separate worktree manager CLI is introduced here.
- Existing clean-eval behavior stays intact.

## Out of Scope
- A new worktree-management command.
- Automatic merge/PR/discard actions for worktrees.
- Host-specific filesystem orchestration beyond the existing workflow semantics.

## Kind
work-contract-v1

## Status
approved

## Source
- Linear: BEI-22
- GitHub: sandsower/beislid#11

## Problem
Agent work can contaminate the shared checkout when multiple tasks or experiments need isolation.

## Desired Outcome
Beislið can describe and route isolated agent work through git worktrees without regressing existing kickoff, handoff, or PR-review flows.

## Constraints
- Preserve current repo-local workflow semantics.
- Do not break clean-eval, ready-for-review, or review-response.
- Keep read-only workflows lightweight.
- Cleanup stays explicit and visible.

## Acceptance Outcomes
- The workflow explains when to recommend a worktree and when to use the existing checkout.
- The workflow makes branch/worktree context visible in handoff and PR-facing flows.
- The workflow documents cleanup paths: keep, merge, PR, discard.
- Existing clean-eval behavior remains separate and unchanged.

## Unknowns / Human Decisions
- None blocking; implementation details remain to be chosen in blueprint.

## Risk Classification
Medium — touches multiple workflow-facing docs and skill semantics, but stays within repo-local Beislið behavior.

## Extension Slots

```yaml
scope_classification:
  kind: single_pr
  confidence: medium
  rationale: "One coherent workflow-semantics change spanning docs and portable skill guidance, without splitting into independently shippable slices."
  recommended_route: blueprint
  requires_human_approval: false
  requires_split: false
  split_reason: null

proof_requirements:
  - type: command_gate
    id: diff-whitespace
    status: required
  - type: command_gate
    id: install-integration-tests
    status: required
  - type: command_gate
    id: skill-size-budgets
    status: required
  - type: command_gate
    id: validate-skills
    status: required
  - type: command_gate
    id: approved-planning-lifecycle-consistency
    status: required
  - type: command_gate
    id: visual-surfaces-consistency
    status: required
  - type: command_gate
    id: artifact-templates-consistency
    status: required
  - type: command_gate
    id: workflow-signals-consistency
    status: required
  - type: command_gate
    id: lifecycle-hooks-consistency
    status: required
  - type: command_gate
    id: model-routing-step-hints-consistency
    status: required
  - type: command_gate
    id: run-ledger-skill-examples-consistency
    status: required

slice_plan: null
children: []
```

## Ownership Boundary
Beislið owns the workflow semantics, portable skill guidance, and repo-local planning artifacts. Rondo/external runners own execution, git worktree mechanics, and run evidence.

## Artifact Context
- Event: kickoff / spec refinement
- Ticket: BEI-22
- Branch: rondo/BEI-22
- Source: current workspace exploration and Linear ticket context
