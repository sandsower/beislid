<!-- beislid-workflow: v1 -->

# Beislið workflow config — small-oss-library

**Audience:** Solo maintainer or small team maintaining a focused open-source
library (one language, one package, one repository).

**Team policy:** Keep gates fast enough to run before every push. No babysit
automation — PRs are reviewed by human contributors. Ticket tracking is
lightweight: GitHub Issues via the `gh` CLI.

**Expected flow:** `kickoff` → `blueprint` → `implement` → `verify` →
`ready-for-review`. Review feedback arrives through GitHub PR comments; the
maintainer handles review-response manually.

## Issue tracker

GitHub Issues on this repo, accessed through the `gh` CLI. Ticket IDs are bare
issue numbers; the branch pattern expects `{number}-short-slug`.

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body,labels'
id_pattern: '^#?\d+$'
link_template: 'https://github.com/my-org/my-lib/issues/{id}'
```

```beislid:branch_pattern
^(\d+)-
```

```beislid:ticket_update
type: cli
comment_command: 'gh issue comment {id} --body-file {body_file}'
```

## PR target

Pull requests target `main` from the default `origin` remote. No custom
configuration needed — Beislið derives these automatically.

## PR reviews

GitHub PR review feedback through the `gh` CLI. Inline review threads are
consumed alongside top-level comments.

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

Lint and test run before every PR. Both are cheap enough for every push.

```beislid:gates
- name: lint
  command: 'npx eslint . --max-warnings 0'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: test
  command: 'npm test'
  parallel_safe: false
  mutates: false
  cost: moderate
```

## Action policy

Unattended runs may push and create PRs. All other remote git actions ask.

```beislid:action_policy
modes:
  unattended-auto:
    actions:
      git.push: allow
      gh.pr.create: allow
```

## Babysit

Babysit monitors the PR loop but does not auto-merge or auto-close. Every
closeout step requires human approval.

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

1. Replace `my-org/my-lib` in `link_template` with your repo.
2. Adjust the `branch_pattern` if your convention differs.
3. Add or replace gates to match your project's lint/test tooling.
4. Run `/doctor` to audit the result before your first real run.