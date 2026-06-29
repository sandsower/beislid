# Lifecycle hooks protocol v1

This shared protocol defines custom phase-boundary hooks for Beislið skills. It is paired with the repo workflow's `beislid:lifecycle_hooks` config block, which lets a project run repo-owned side effects before and after major phases without hard-coding them into the core skills.

## What hooks are for

Use hooks for repo-specific checks and integrations that should happen around a phase boundary, such as ADR review, migration validation, changelog sync, i18n checks, browser compatibility, or domain-specific QA.

Hooks are not quality gates. Gates prove readiness; hooks run side effects or prerequisite checks around the phase.

## Hook phases

P0 phase names are:

- `spec`
- `blueprint`
- `implement`
- `verify`
- `review`
- `fresh_eyes`
- `ready_for_review`
- `review_response`

Each phase may define `before` hooks, `after` hooks, or both.

## Selection

A hook action runs only when its phase entry matches the current phase boundary and its trigger rules match the current run context.

Supported trigger rules in v1:

- `paths` — changed-file globs
- `exclude` — negative changed-file globs
- `scopes` — explicit workflow scope names
- `branch_pattern` — branch regex or glob, depending on repo policy

Trigger rules are additive: if a rule is present, the current run must satisfy it. Empty or missing trigger blocks mean the hook applies to the phase boundary unconditionally.

## Action shape

Hook actions reuse the same side-effect model as other lifecycle integrations:

- `name` — stable action name
- `type` — `cli` or `mcp` in P0
- `command` / `tool` — provider-specific executable
- `approval` — `prompt` or `auto`
- `when` — optional trigger rules

Hooks may mutate files, post comments, push, or create tickets only when the action policy allows the operation and the workflow policy requires or receives clear approval. `approval: auto` never bypasses action policy or safety prompts.

## Execution order

1. Read the workflow config.
2. Select hooks for the current phase boundary.
3. Evaluate action policy before each side effect.
4. Run `before` hooks before the phase body.
5. Run `after` hooks after the phase completes successfully.
6. If a hook fails, surface the failure and stop only when the configured policy says the failure is blocking.

## Audit

`doctor` must report whether `beislid:lifecycle_hooks` is configured, summarize which phases are covered, and validate hook shape/triggers without executing any side effects.

If the block is absent, phase skills continue normally.
