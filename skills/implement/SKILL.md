---
name: implement
description: "Use when you have an approved design or requirements for a multi-step task, before writing code. Creates a file-level implementation plan with TDD as the default rhythm, host-agent task tracking, and parallel task batching."
---

# Implementation Plan

Creates a structured plan, tracks it with the host agent's todo/task mechanism, and executes with TDD as the default rhythm.

If the handoff includes an explicit design artifact path from `blueprint`, read it as your primary input. Otherwise, look for a matching design artifact in `plans/` using the ticket/feature slug when known (for example, `plans/<feature>-design.md` from `blueprint`). If exactly one match exists, read it as your primary input. If multiple candidates remain, ask the user to choose the artifact path. Only fall back to conversation context when no design artifact is available.

## Phase 1: Write the Plan

### Header
Every plan starts with:
- **Goal**: one sentence
- **Architecture**: 2-3 sentences on how it fits together
- **Files touched**: list every file that will be created or modified

### Task Decomposition

The first task in each batch should be a tracer bullet — a thin vertical slice that cuts through all layers end-to-end (UI, API, data, tests). This proves the architecture works before widening to other tasks.

Break work into bite-sized tasks (2-5 minutes each). Each task specifies:
- Exact file path(s)
- What changes: test code, implementation code, or both
- Expected outcome (test passes, output matches, etc.)

**Default rhythm for each task is TDD:**
1. Write the test that describes expected behavior
2. Run it — confirm it fails (red)
3. Write minimal code to pass (green)
4. Refactor if needed
5. Commit

**TDD exceptions** — mark tasks as non-TDD only when testing doesn't apply:
- CSS/styling changes
- Config file changes
- Database migrations
- Documentation
- Dependency updates

If a task is non-TDD, explicitly note why.

### Batch Independent Tasks

Group tasks that have no dependencies on each other into batches. Within a batch, tasks can be dispatched to parallel subagents.

Mark dependencies explicitly:
```
Batch 1 (parallel): Task A, Task B, Task C
Batch 2 (after batch 1): Task D (depends on A), Task E (depends on B+C)
Batch 3 (after batch 2): Task F (integration)
```

## Phase 2: Track tasks

Create an item for every task in the host agent's todo/task mechanism. If the host has no dedicated todo tool, maintain the task list visibly in chat. This is mandatory — the todo list is the spine that prevents skipping steps.

- Mark `in_progress` when starting a task
- Mark `completed` only after verification passes
- If blocked, stop and surface the issue — don't skip ahead

## Phase 3: Execute

### Single tasks
Work through the todo list in order. Follow the TDD rhythm. Commit after each task or logical group.

### Parallel batches
When a batch has 3+ independent tasks, dispatch subagents:
- Each subagent gets: focused scope, full context for their task, specific success criteria
- After all return: review diffs, verify no conflicts, run full test suite
- Don't dispatch parallel agents for fewer than 3 tasks — the overhead isn't worth it

### Escalation
- If a task fails 3 times, stop. Question the approach, not the implementation
- If blocked on a dependency, surface to the user immediately
- If the plan needs to change, update the plan AND the todo list before continuing

## Phase 4: Verify

When all tasks are complete, run the full verification:
- All tests pass
- Linter clean
- Build succeeds
- No regressions

Only then mark the plan as done. Invoke `verify` if needed.
