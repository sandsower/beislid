<!-- beislid-workflow: v1 -->

# Beislið workflow config — frontend-app

**Audience:** Frontend team shipping a Next.js web application. One repo, one
`package.json`, deployed through Vercel.

**Team policy:** TypeScript typechecking, linting, and unit tests run as
pre-PR gates. Integration tests and build checks are moderate-cost gates that
run before review. Babysit is enabled but asks before every closeout step.

**Expected flow:** `kickoff` fetches Linear tickets. `blueprint` produces an
implementation plan. `implement` writes code with TDD. `verify` runs the
configured gates. `ready-for-review` creates the PR and runs the full gate
suite. `review-response` handles PR feedback.

## Issue tracker

Linear issues in the frontend team's workspace. Ticket IDs match `FE-1234`.

```beislid:ticket_source
type: mcp
tool: mcp__linear__get_issue
id_pattern: '^FE-\d+$'
link_template: 'https://linear.app/myteam/issue/{id}'
```

```beislid:branch_pattern
^[^/]+/(fe-\d+)
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

Gates are ordered from cheapest to most expensive. Lint and typecheck run in
parallel; tests and build run after.

```beislid:gates
- name: lint
  command: 'npx eslint . --max-warnings 0'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: typecheck
  command: 'npx tsc --noEmit'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: test
  command: 'npx vitest run'
  parallel_safe: false
  mutates: false
  cost: moderate
- name: build
  command: 'npx next build'
  parallel_safe: false
  mutates: false
  cost: expensive
```

## Action policy

Unattended runs may push and create PRs. Review replies are auto-allowed so
babysit can handle feedback without human prompts for each comment.

```beislid:action_policy
modes:
  unattended-auto:
    actions:
      pr.review.reply: allow
      git.push: allow
      gh.pr.create: allow
```

## Babysit

Babysit monitors the PR loop and can auto-reply to actionable review feedback.
Closeout requires explicit human approval for merge, memento, retro, and
cleanup — cleanup has no key of its own, so it inherits merge's `ask`.

```beislid:babysit
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 60
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

1. Replace the `id_pattern` and `link_template` with your actual Linear team
   prefix and URL.
2. Adjust the `branch_pattern` to match your branch naming convention.
3. Swap `vitest` for `jest` or your test runner of choice.
4. Add Playwright or Cypress E2E gates if you run them pre-PR.
5. If you deploy through a different platform (Netlify, Cloudflare Pages),
   replace the `build` gate command.