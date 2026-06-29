<!-- beislid-workflow: v1 -->

# Beislið workflow config — backend-service

**Audience:** Backend team shipping a Go API service behind a PostgreSQL
database. Docker Compose for local development; CI runs integration tests
against ephemeral databases.

**Team policy:** Lint and unit tests run per-edit. Integration tests and
migration checks run before PR. Linear tickets feed into GitHub PRs. Babysit
is configured but asks before merging.

**Expected flow:** `kickoff` (Linear ticket) → `blueprint` (implementation
design) → `implement` (TDD, gates run per-edit) → `verify` (full gate suite) →
`ready-for-review` (PR + clean eval) → `review-response` (handle feedback).

## Issue tracker

```beislid:ticket_source
type: mcp
tool: mcp__linear__get_issue
id_pattern: '^API-\d+$'
link_template: 'https://linear.app/myteam/issue/{id}'
```

```beislid:branch_pattern
^[^/]+/(api-\d+)
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

## Quality gates

Cheap linting and unit tests run first. Integration tests require Docker and
are marked `cost: expensive` so orchestrators can schedule them appropriately.

```beislid:gates
- name: lint
  command: 'golangci-lint run ./...'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: unit-test
  command: 'go test -short ./...'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: integration-test
  command: 'docker compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from test'
  parallel_safe: false
  mutates: false
  cost: expensive
- name: migration-check
  command: 'go run ./cmd/migrate check'
  parallel_safe: false
  mutates: false
  cost: moderate
```

## Action policy

Unattended runs may push, create PRs, and reply to review comments. Destructive
and secret-bearing actions remain denied.

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

## Turn this into your own config

1. Replace the `id_pattern` and `team prefix` with your Linear setup.
2. If your backend is Python, Node, or Rust, swap the gate commands
   (`golangci-lint` → `ruff` / `pylint`, `go test` → `pytest`, etc.).
3. If you don't use Docker Compose for tests, replace the integration gate
   with your equivalent.
4. Remove the `migration-check` gate if your project doesn't have database
   migrations.
5. Add an OpenAPI/Swagger validation gate if you generate API specs.