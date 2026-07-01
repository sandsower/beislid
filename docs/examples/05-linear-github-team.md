<!-- beislid-workflow: v1 -->

# Beislið workflow config — linear-github-team

**Audience:** Established product-engineering team using Linear for ticket
tracking and GitHub for code review. Multiple contributors per repo; PRs
require at least one approving review before merge.

**Team policy:**
- Linear issues drive all work; branches embed the ticket key.
- Quality gates run before every PR and after every babysit-owned push.
- Babysit auto-replies to actionable review feedback, re-runs gates, pushes
  fixes, and re-requests reviewers after changes.
- Merge is `ask`-mode: the human must approve the final merge.
- Memento capture and workflow retro run automatically after merge.
- Model routing prefers specific models for different skill tiers.

**Expected flow:** `kickoff` (fetches Linear ticket, assigns it) → `blueprint`
(design with heavy model) → `implement` (standard model, TDD, per-edit gates) →
`verify` (full gate suite) → `ready-for-review` (PR, clean eval, fresh-eyes) →
`review-response`/`babysit` (loop until approved) → merge + memento + retro.

## Issue tracker

```beislid:ticket_source
type: mcp
tool: mcp__linear__get_issue
id_pattern: '^[A-Z]{2,4}-\d+$'
link_template: 'https://linear.app/myteam/issue/{id}'
```

```beislid:branch_pattern
^[^/]+/([a-z]+-\d+)
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
rerequest_command: 'gh api repos/{owner}/{repo}/pulls/{number}/requested_reviewers --method POST --input {json_file}'
```

## Review policy

```beislid:review_policy
agentic_reviewer:
  mode: opt_in_final_review
  provider: coderabbit
  label: coderabbit-ready
  description_keyword: coderabbit:review
risk:
  max_auto_closeout_risk: low
  high_risk_paths: ['.github/workflows/**', 'config/**']
  low_risk_paths: ['docs/**', '**/*.md']
  high_risk_file_count: 12
  high_risk_total_changes: 500
  low_risk_file_count: 3
  low_risk_total_changes: 120
```

## Quality gates

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
  command: 'npm test'
  parallel_safe: false
  mutates: false
  cost: expensive
- name: build
  command: 'npm run build'
  parallel_safe: false
  mutates: false
  cost: expensive
```

## Lifecycle actions

Assign the ticket on kickoff, write planning artifacts after approval, and optionally run a configured approved-design hook.

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: assign-ticket
        type: cli
        command: 'gh issue edit {id} --add-assignee @me'
        approval: auto
        on_failure: prompt
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        path: 'plans/{feature}-design.md'
      - name: notify-design-approved
        type: cli
        command: 'planning-hook {event} {ticket_id} {artifact_path}'
        approval: prompt
        classes: [git-remote]
```

## Lifecycle hooks

Run repo-owned checks around phase boundaries without turning them into gates.

```beislid:lifecycle_hooks
phases:
  implement:
    before:
      actions:
        - name: consistency-check
          type: cli
          command: 'python3 scripts/check_break_spec_artifact_consistency.py'
          approval: auto
          when:
            paths: ['docs/**', 'plans/**']
  ready_for_review:
    after:
      actions:
        - name: workflow-signal-check
          type: cli
          command: 'python3 scripts/check_workflow_signals_consistency.py'
          approval: prompt
          when:
            paths: ['skills/**', '.beislid/**']
```

## Model routing

Use frontier models for design work (`spec`, `blueprint`, `poke-holes`) and
standard models for implementation and delivery. The team prefers Anthropic
for design reasoning and Codex for implementation throughput.

```beislid:model_routing
defaults:
  models: [openai:gpt-5.1-codex]
  mode: prefer
overrides:
  - skills: [spec, blueprint, poke-holes]
    models: [anthropic:claude-opus-4.8]
    mode: require
  - skills: [implement, ready-for-review, review-response]
    models: [openai:gpt-5.1-codex, anthropic:claude-sonnet-4.6]
    mode: prefer
tiers:
  light: [google:gemini-2.5-flash, anthropic:claude-haiku-4.5]
  standard: [openai:gpt-5.1-codex, anthropic:claude-sonnet-4.6]
  heavy: [anthropic:claude-opus-4.8, openai:gpt-5.1-codex]
  frontier: [anthropic:claude-opus-4.8, google:gemini-2.5-pro]
tier_mode: prefer
```

## Action policy

Unattended runs can push, create PRs, reply to reviews, and capture memento
memories. Closeout merge and retro still run through policy checks.

```beislid:action_policy
modes:
  unattended-auto:
    actions:
      pr.review.reply: allow
      git.push: allow
      gh.pr.create: allow
      memento.capture: allow
      retro.run: allow
```

## Babysit

Full babysit loop with auto-closeout for merge, memento, and retro.

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
    mode: auto
  retro:
    mode: auto
    apply_findings: auto
```

## Ready-for-review

Clean eval is required for this team. The agent works from a clean worktree
to verify the exact patch before creating the PR.

```beislid:ready_for_review
approval_gates:
  pr_title_body: prompt
  gate_failure: prompt
  autofix_commit: prompt
  clean_eval_failure: prompt
  reduced_review_coverage: prompt
```

```beislid:clean_eval
mode: require
surface: auto
artifact_root: .beislid/clean-eval
```

```beislid:ship_time_artifacts
mode: remind
```

## Turn this into your own config

1. Replace the `id_pattern` and Linear URL with your team's workspace.
2. Adjust the gate commands to match your tech stack.
3. Tune the model routing overrides: the `skills` lists are Beislið skill
   names; pick the models your team trusts for each tier.
4. Set `babysit.closeout.merge.mode` to `auto` if you want automatic merge
   after approval (requires green CI and no open review threads).
5. Set `ship_time_artifacts.mode` to `include` if you want ready-for-review
   to call out approved planning artifacts at handoff; leave it at `remind`
   (or omit the block) for the default reminder-only behavior.
6. Remove `clean_eval` or set its mode to `off` if you don't need clean-
   worktree verification before PR creation.
7. If you use GitHub Actions or another CI system for required checks, you
   may want `closeout.merge.method: repo-default` to follow branch protection
   rules.