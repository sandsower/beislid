<!-- beislid-workflow: v1 -->

# Beislið workflow config — monorepo

**Audience:** Team maintaining a monorepo with frontend (`apps/web`), backend
(`apps/api`), shared packages (`packages/types`, `packages/utils`), and
documentation (`docs/`).

**Team policy:** Gate sets select only the gates relevant to changed files.
A docs-only PR skips the full app test suite. A backend-only PR skips
frontend linting. Shared package changes gate both frontend and backend.
Linear tickets; GitHub PRs.

**Expected flow:** `kickoff` (reads Linear ticket, explores entire monorepo
but gates only run for changed scopes) → `blueprint` → `implement` →
`verify` → `ready-for-review` (gate sets selected by diff; PR created).

## Issue tracker

```beislid:ticket_source
type: mcp
tool: mcp__linear__get_issue
id_pattern: '^MONO-\d+$'
link_template: 'https://linear.app/myteam/issue/{id}'
```

```beislid:branch_pattern
^[^/]+/(mono-\d+)
```

```beislid:ticket_update
type: mcp
comment_tool: mcp__linear__save_comment
```

## PR target

```beislid:pr_base
default: main
```

## PR reviews

```beislid:pr_review_source
type: cli
summary_command: 'gh pr view --json url,number,reviewDecision,reviews,comments'
threads_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments'
```

```beislid:pr_review_update
type: cli
reply_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments --method POST --input {json_file}'
```

## Gate sets

Each gate set runs in the relevant package directory. Selectors match changed
files and union the matching sets. A PR touching `apps/web/components` and
`packages/types` runs frontend + shared gates exactly once.

```beislid:gate_sets
sets:
  frontend:
    cwd: apps/web
    gates:
      - name: fe-lint
        command: 'pnpm lint'
        parallel_safe: true
        mutates: false
        cost: cheap
      - name: fe-typecheck
        command: 'pnpm typecheck'
        parallel_safe: true
        mutates: false
        cost: cheap
      - name: fe-test
        command: 'pnpm test'
        parallel_safe: false
        mutates: false
        cost: moderate
  backend:
    cwd: apps/api
    gates:
      - name: be-lint
        command: 'cargo clippy -- -D warnings'
        parallel_safe: true
        mutates: false
        cost: cheap
      - name: be-test
        command: 'cargo test'
        parallel_safe: false
        mutates: false
        cost: moderate
  shared:
    gates:
      - name: shared-test
        command: 'pnpm -r --filter "./packages/*" test'
        parallel_safe: false
        mutates: false
        cost: moderate
      - name: shared-build
        command: 'pnpm -r --filter "./packages/*" build'
        parallel_safe: false
        mutates: false
        cost: moderate
  docs:
    gates:
      - name: docs-lint
        command: 'markdownlint docs/ --ignore node_modules'
        parallel_safe: true
        mutates: false
        cost: cheap
selectors:
  - name: frontend-files
    paths:
      - 'apps/web/**'
    gate_sets: ['frontend']
  - name: backend-files
    paths:
      - 'apps/api/**'
    gate_sets: ['backend']
  - name: shared-files
    paths:
      - 'packages/**'
    gate_sets: ['shared']
  - name: docs-files
    paths:
      - 'docs/**'
      - 'README.md'
    gate_sets: ['docs']
```

## Action policy

```beislid:action_policy
modes:
  unattended-auto:
    actions:
      pr.review.reply: allow
      git.push: allow
      gh.pr.create: allow
```

## Babysit

```beislid:babysit
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 120
closeout:
  merge:
    mode: ask
    method: squash
    delete_branch: true
  memento:
    mode: ask
  retro:
    mode: ask
```

## Ready-for-review

```beislid:ready_for_review
approval_gates:
  pr_title_body: prompt
  gate_failure: prompt
  autofix_commit: prompt
  clean_eval_failure: prompt
  reduced_review_coverage: prompt
```

## Turn this into your own config

1. Replace `cargo` with your backend tooling if you use Node, Go, or Python.
2. Adjust `cwd` values and gate commands to match your monorepo structure.
3. Add more selectors if you have additional packages (mobile, design system,
   infrastructure).
4. The selectors are evaluated in order; the more specific selectors should
   come before broad ones like `shared-files` if de-duplication matters.
5. If your monorepo uses Turborepo or Nx, you can wrap gate commands with
   `turbo run lint --filter="<scope>"` for caching.