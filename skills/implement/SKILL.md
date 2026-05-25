---
name: implement
description: "Use when you have an approved design or requirements for a multi-step task, before writing code. Creates a file-level implementation plan with TDD as the default rhythm, host-agent task tracking, and parallel task batching."
---

# Implementation Plan

Creates a structured plan, tracks it with the host agent's todo/task mechanism, and executes with TDD as the default rhythm.

If the handoff includes an explicit design artifact path from `blueprint`, read it as your primary input; design artifacts are checkpoint-compatible state seeds for implementation planning. Otherwise, look for a matching design artifact in `plans/` using the ticket/feature slug when known (for example, `plans/<feature>-design.md` from `blueprint`). If exactly one match exists, read it as your primary input. If multiple candidates remain, ask the user to choose the artifact path. Only fall back to conversation context when no design artifact is available.

If the user is resuming with phrases such as `continue this ticket`, `continue implementation`, or `continue from checkpoint`, read `.beislid/checkpoints/latest.json` when present. Prefer an `implementation_plan_created` checkpoint matching the current branch and ticket ID when known; otherwise fall back to a matching `kickoff_context_ready` checkpoint or ask the user to choose among matching latest entries. Read the referenced checkpoint artifact as primary context before falling back to conversation context. Missing, unreadable, or malformed latest pointers are non-blocking; warn when malformed, then ignore the pointer and fall back to a matching checkpoint artifact or conversation context. If durable run-ledger state is available, `beislid run-ledger resume --flow implement --ticket-id <id> --branch <branch>` may identify the latest running/interrupted/failed external run, but checkpoint artifacts/design artifacts remain the primary content seed for implementation planning.

Action-risk decisions follow `action-policy-protocol.md`; read it before checkpoint writes, workspace edits, dependency installs, local git operations, or configured side-effect hooks. For durable run evidence, best-effort `beislid run-ledger init/resume ... --flow implement` when the CLI is available and ticket/branch context is known. Record transcript-safe events for plan creation, task-batch starts/completions, verification results, and interruptions. When a workflow checkpoint artifact is written, add a ledger checkpoint payload that links to the artifact path and includes a `resume_hint` for the next safe task boundary. Ledger failures warn but never replace task tracking, verification, or checkpoint artifact behavior.

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

If a task is non-TDD, explicitly note why. If a run ledger is active, record the final approved plan or task list path as a ledger checkpoint before starting code changes.

### Batch Independent Tasks

Group tasks that have no dependencies on each other into batches. Within a batch, tasks can be dispatched to parallel subagents.

Mark dependencies explicitly:
```
Batch 1 (parallel): Task A, Task B, Task C
Batch 2 (after batch 1): Task D (depends on A), Task E (depends on B+C)
Batch 3 (after batch 2): Task F (integration)
```

### Checkpoint before code changes

If inside a git repo with `.beislid/workflow.md`, read only the `beislid:lifecycle_actions` block and execute supported `events.implementation_plan_created.actions[]` entries after the implementation plan is written and before Phase 2 task tracking / Phase 3 code changes. If workflow.md is missing, the block is absent, or the lifecycle YAML is malformed, warn and skip automatic checkpoint handling; preserve standalone behavior by printing the plan in chat.

Supported P0 action shape:

```yaml
- name: write-implementation-plan-checkpoint
  type: artifact
  approval: prompt # optional; defaults to prompt when omitted
  path: 'checkpoints/{event}-{ticket_id}.md' # optional default
```

Before each checkpoint artifact write, evaluate action policy for `checkpoint.implementation_plan_created.<name>` with class `workspace-write`. Execute only `type: artifact`; skip other providers as reserved. Multiple artifact actions are allowed and run in order. Use the same artifact safety posture as planning artifacts: `approval: prompt` asks write/skip and shows action name, resolved path, content summary, and parent directory creation; `approval: auto` writes automatically only when the target does not exist; existing targets always prompt for overwrite / choose another path / skip. Skip, failed writes, and reserved actions do not block implementation, but code changes must not start until checkpoint handling and the boundary prompt are complete.

Default path: `checkpoints/{event}-{ticket_id}.md` when ticket context is known, otherwise `checkpoints/{event}-{feature}.md`. Supported placeholders are `{event}` (`implementation_plan_created`), `{feature}`, `{kind}` (`checkpoint`), and `{ticket_id}` when ticket context is known. Derive `{feature}` from the implementation goal, then approved design title/path, then ticket title, then branch name; ask for a filename stem if none is available. Slug values by lowercasing, replacing non-alphanumeric runs with `-`, collapsing repeats, stripping edge `-`, and keeping names readable (about 60 chars). If `{ticket_id}` is used without ticket context, ask for another path or skip. Paths must be relative, stay inside the repo root, contain no `..`, and end in `.md`.

Checkpoint content must be human-readable Markdown with stable sections: `Checkpoint Metadata`, `State Summary`, `Key Context`, `Decisions`, `Next Step`, `Open Risks / Questions`, and optional `Related Artifacts`. Include ticket id/title when known, branch, source skill `implement`, event name, approved design source/path, goal, architecture, files touched, task decomposition, batches/dependencies, verification plan, and open risks. Summarize architecture, tasks, and approach only when they match the approved design or implementation plan; do not introduce new implementation decisions.

After a checkpoint artifact is written, update `.beislid/checkpoints/latest.json` with a replaceable latest-pointer entry containing event, path, `ticket: {id, title}` when known, branch, source skill, and written timestamp when available. This pointer is convenience state for fresh-context rediscovery only: no run ID, no event history, no gate logs, and no resume state machine. If a durable run ledger is active, record the checkpoint path there as run history, but do not replace or reinterpret the `.beislid/checkpoints/latest.json` pointer. If the pointer update fails, report it but keep the artifact result.

When a checkpoint is written, print host-neutral fresh-context guidance and pause before code changes: tell the user this is the safest point to run `/clear` or `/new`, and that after restarting they can say `continue implementation` or `continue from checkpoint` so the latest pointer can be rediscovered. Do not invoke `/clear` or `/new` automatically.

## Phase 2: Track tasks

Create an item for every task in the host agent's todo/task mechanism. If the host has no dedicated todo tool, maintain the task list visibly in chat. This is mandatory — the todo list is the spine that prevents skipping steps.

- Mark `in_progress` when starting a task
- Mark `completed` only after verification passes
- If blocked, stop and surface the issue — don't skip ahead

## Phase 3: Execute

### Single tasks
Work through the todo list in order. Evaluate action policy before workspace writes, dependency installs, and local git operations (`file.write`, `dependency.install`, `git.commit` or a more specific stable action id). Follow the TDD rhythm. Commit after each task or logical group only when policy allows or `ask` is approved.

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

Only then mark the plan as done. Invoke `verify` if needed. If a run ledger is active, write a final implementation checkpoint or finalize event with verification evidence, policy decisions, sandbox status, remaining risks, changed files summary, and the next recommended workflow (`ready-for-review`, `rinse`, or user follow-up).
