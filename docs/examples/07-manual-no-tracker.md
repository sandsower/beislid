<!-- beislid-workflow: v1 -->

# Beislið workflow config — manual-no-tracker

**Audience:** Solo developer, prototyping, or ad-hoc project without a formal
issue tracker. Tickets are pasted manually. Work is personal or experimental;
branches don't follow a ticket-key convention.

**Team policy:** No issue tracker integration. Paste the ticket text when
`kickoff` asks for it. Quality gates are minimal — just lint and test. No
babysit automation; PRs are created and reviewed manually. This config is
deliberately lightweight: it removes every integration point that needs a
tracker or review tool.

**Expected flow:** `spec` (optional, for vague ideas) → `blueprint` (manual
paste) → `implement` → `verify` → `ready-for-review` (manual PR creation
from the branch). Review-response uses manual paste for PR feedback if the
repo is on GitHub.

## Issue tracker

No automated ticket source. The agent asks you to paste the ticket text. This
is the fallback for all tracker types.

```beislid:ticket_source
type: paste
id_pattern: '.*'
```

No branch pattern — branches are free-form.

## PR target

```beislid:pr_base
default: main
```

## PR reviews

If the repo is on GitHub and `gh` CLI is authenticated, use the CLI source.
Otherwise, paste the PR feedback manually when review-response needs it.

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

Keep gates to the essentials. Every gate should run in under 30 seconds on a
laptop.

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
  cost: cheap
```

## Action policy

Unattended runs may push to non-default branches. All remote git actions and
PR creation ask by default.

```beislid:action_policy
modes:
  unattended-auto:
    actions:
      git.push: allow
```

## Babysit

Babysit is configured but all closeout steps ask. No auto-merge, no auto-
memento, no auto-retro. The human drives every decision.

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

1. This config assumes you have `gh` CLI authenticated. If you don't, change
   `pr_review_source` and `pr_review_update` to `type: manual`.
2. Swap `eslint` and `npm test` for your actual lint/test tools.
3. Add a `typecheck` gate if your language supports it (`npx tsc --noEmit`,
   `mypy`, etc.).
4. If you later adopt a tracker, run `/setup` to configure `ticket_source`
   and `branch_pattern` without rewriting the rest.
5. This config is a good starting point for new projects — you can add more
   sections as your workflow matures.