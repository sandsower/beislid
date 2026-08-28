<!-- beislid-workflow: v1 -->

# Beislið workflow config — beislid

This is the Beislið distribution repo's own workflow config. It dogfoods the v0.2 markdown-as-config pattern and supersedes the legacy per-skill YAML config files deleted in this PR.

## Issue tracker

Linear issues in the personal `teotl` workspace, team `beislid`, accessed via Linear MCP. Issue IDs use the `BEI-<number>` key scheme.

```beislid:ticket_source
type: mcp
tool: mcp__linear__get_issue
id_pattern: '^BEI-\d+$'
link_template: 'https://linear.app/teotl/issue/{id}'
```

Linear-created branches use lowercase issue keys such as `vic/bei-56-...`; the branch pattern lets orchestrators recover and normalize the ticket ID when present. Other branch shapes still fall back to asking for the ticket ID.

```beislid:branch_pattern
^[^/]+/([a-z]+-\d+)
```

```beislid:ticket_update
type: mcp
comment_tool: mcp__linear__save_comment
issue_tool: mcp__linear__save_issue
```

## Lifecycle actions

```beislid:lifecycle_actions
events:
  break_spec_approved:
    actions:
      - name: write-structure-artifact
        type: artifact
        approval: prompt
        path: 'plans/{feature}-structure.md'
  spec_approved:
    actions:
      - name: write-spec-artifact
        type: artifact
        approval: prompt
        path: 'plans/{feature}-spec.md'
      - name: post-spec-body-to-tracker
        type: tracker
        approval: prompt
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        path: 'plans/{feature}-design.md'
```

## PR reviews

GitHub PR review feedback is read and updated through the `gh` CLI. Reply bodies are written through JSON temp files; user-authored text is never interpolated into shell commands.

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

AgenticReviewer is a scarce final-review role; CodeRabbit is this repo's current provider. Do not trigger it for WIP or routine iteration; run local gates and Beislið review first, then opt in by adding the configured label or PR body keyword.

```beislid:review_policy
agentic_reviewer:
  mode: opt_in_final_review
  provider: coderabbit
  label: coderabbit-ready
  description_keyword: coderabbit:review
risk:
  max_auto_closeout_risk: low
  high_risk_paths:
    - '**/config/**'
    - '**/.github/workflows/**'
    - 'bin/**'
    - 'packaging/**'
    - 'scripts/test_install.sh'
    - 'scripts/install*.sh'
    - 'skills/**/SKILL.md'
    - 'tests/agent-smoke/**'
    - '.beislid/**'
    - '.nopal/**'
  low_risk_paths:
    - 'docs/**'
    - '**/*.md'
    - '**/*.markdown'
    - '**/*.mdx'
    - 'README*'
    - 'CHANGELOG.md'
  high_risk_file_count: 12
  high_risk_total_changes: 500
  low_risk_file_count: 3
  low_risk_total_changes: 120
```

## Quality gates

The repo has no scope separation because it is a single Markdown distribution.
The cheap whitespace gate catches malformed diffs early, then the local CI mirror runs every blocking deterministic check from the repo root once.

```beislid:gates
- name: diff-whitespace
  command: 'git diff --check origin/main...HEAD'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: local-ci-mirror
  stage: pre-pr
  kind: sensor
  execution: computational
  command: 'bash scripts/validate.sh'
  timeout_seconds: 900
  cost: expensive
  mutates: false
  parallel_safe: false
  failure:
    hint: 'Mirrors every CI-blocking check in .github/workflows/validate.yml (all check_*_consistency.py scripts, script tests, install/action-policy/run-ledger tests, npm test, committed export bundle validation, and the lychee link check where available locally). Run this once before opening a PR.'
```

Changes to `bin/beislid` runtime-layout checks or `packaging/` must run `bash scripts/test_install.sh` locally before push; the packaged-layout contract is only covered by the install integration tests.

Agent smoke is intentionally not a default quality gate because it spends model budget and can take several minutes. During `ready-for-review`, ask about Codex agent smoke only when the diff includes medium/large Beislið skill changes, protocol changes (`skills/`, `.beislid/`), installer/test-install changes, or smoke harness changes (`tests/agent-smoke/`). For tiny docs-only skill prose changes, record `Codex agent smoke skipped by workflow: docs-only skill prose change` and continue without prompting. When smoke is required, stop before running it and ask exactly: `This change touches Beislið skill/smoke paths. Run Codex agent smoke now? Claude support is temporarily unavailable; this uses broad fixture permissions, model budget, and can take several minutes. [y/N]`. Default is no; do not run on silence, ambiguity, or prior blanket approval. If accepted and the host supports background subagents/tasks, start the smoke command in a non-blocking subagent, continue other side-effect-free ready-for-review work while it runs, then join before PR creation; never push/open the PR until the smoke result is known or the user explicitly accepts skipping/ignoring it. If no background runner is available, run it in the main session. Use:

```bash
python3 tests/agent-smoke/run.py gate ready-for-review --hosts codex --timeout 900 --changed-only
```

## Ready-for-review

This repo auto-approves auditable PR metadata and policy-checked autofix commits.
Failures, clean-evaluation exceptions, and reduced review coverage still require explicit human judgment.

```beislid:ready_for_review
approval_gates:
  pr_title_body: auto
  gate_failure: prompt
  autofix_commit: auto
  clean_eval_failure: prompt
  reduced_review_coverage: prompt
```

```beislid:clean_eval
mode: require
surface: auto
artifact_root: .beislid/clean-eval
```

## Workflow signals

Dogfood local workflow-state fan-out for Beislið's own Pi-managed runs. Signals are best-effort and local; missing `tmux-glance` or non-tmux sessions must not block workflow progress.

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
skills:
  ready-for-review: auto
  poke-holes: auto
  babysit: auto
  review-response: auto
```

## Babysit

Enable all closeout steps by default for this repo. Babysit may merge, capture memento, run/apply retro, and then run cleanup automatically after the green audit; each action is still bounded by runtime safety stops.

`closeout.cleanup.mode` is deliberately left unset so this repo exercises the inherited default: cleanup follows `closeout.merge.mode`, which is `auto` here. Cleanup closes the merged Linear issue through the configured `ticket_update` issue channel, assigns it to the PR author, deletes the remote branch, and reports the worktree path and branch as ready for removal. It never removes the worktree or the local branch — the supervising session does that after reading the report.

This repo runs ticket work in secondary worktrees, so `gh pr merge --delete-branch` fails its local checkout step (`main` is checked out in the primary worktree) and leaves the remote branch undeleted. Cleanup covers that gap: verify the merge via `gh pr view --json state`, then delete the remote branch with `gh api repos/{owner}/{repo}/git/refs/heads/{branch} --method DELETE`.

```beislid:babysit
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 60
closeout:
  merge:
    mode: auto
    method: squash
    delete_branch: true
  memento:
    mode: auto
  retro:
    mode: auto
    apply_findings: auto
```

## Action policy

This repo auto-allows supervised PR handoff and closeout actions, including review replies, pushes, PR creation, AgenticReviewer label edits, merge/retro/memento closeout, and the cleanup stage's ticket close and remote-branch delete.

```beislid:action_policy
modes:
  supervised-auto:
    actions:
      # ticket.fetch is read-only and needed by orchestrators alongside review replies.
      ticket.fetch: allow
      # Kickoff comments and approved PR handoff actions are low-friction in this repo.
      ticket.comment: allow
      pr.review.reply: allow
      git.push: allow
      gh.pr.create: allow
      gh.pr.edit.label: allow
      gh.pr.merge: allow
      pr.merge: allow
      memento.capture: allow
      retro.run: allow
      retro.apply: allow
      # Babysit cleanup closes the merged issue and drops the remote branch.
      ticket.update: allow
      tracker.issue.transition: allow
      git.remote.branch.delete: allow
```

## Nopal seam

This repo dogfoods the Nopal seam.
`.nopal/` is committed and generated by `nopal import beislid-workflow --source .beislid/workflow.md --output-dir .nopal --write --overwrite --json`.
After workflow changes, `nopal import beislid-workflow --source .beislid/workflow.md --output-dir .nopal --check --json` must pass.

```beislid:nopal_seam
mode: prefer
binary: nopal
```

## Translation sync

Disabled for this project — Beislið has no user-facing translations.

## Browser compat

Disabled for this project — no frontend code.

## Domain capture

Disabled for this project — Beislið distributes tenant-neutral skills only; there is no domain expert subagent or knowledge store wired here. Consuming repos configure their own.

## PR description

Disabled — the repo doesn't run drafts through a formatter skill.

## Guided walkthrough

Defaults apply: 5 files / 200 lines. No fenced block needed.

## Probe cache

```beislid:probe_cache
ttl_hours: 24
```
