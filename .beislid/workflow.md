<!-- beislid-workflow: v1 -->

# Beislið workflow config — beislid

This is the Beislið distribution repo's own workflow config. It dogfoods the v0.2 markdown-as-config pattern and supersedes the legacy per-skill YAML config files deleted in this PR.

## Issue tracker

Linear issues in the personal `teotl` workspace, team `beislid`, accessed via Linear MCP. Issue IDs use the `BEI-<number>` key scheme.

```beislid:ticket_source
type: mcp
tool: mcp__linear_personal__get_issue
id_pattern: '^BEI-\d+$'
link_template: 'https://linear.app/teotl/issue/{id}'
```

Linear-created branches use lowercase issue keys such as `vic/bei-56-...`; the branch pattern lets orchestrators recover and normalize the ticket ID when present. Other branch shapes still fall back to asking for the ticket ID.

```beislid:branch_pattern
^[^/]+/([a-z]+-\d+)
```

```beislid:ticket_update
type: mcp
comment_tool: mcp__linear_personal__save_comment
issue_tool: mcp__linear_personal__save_issue
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

## Quality gates

The repo has no scope separation (single markdown distribution). Top-level gates run skill size budgets and the skill frontmatter validator from the repo root.

```beislid:gates
- name: diff-whitespace
  command: 'git diff --check origin/main...HEAD'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: skill-size-budgets
  command: 'python3 scripts/check_skill_size_budgets.py'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: validate-skills
  command: 'python3 scripts/validate_skills.py'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: visual-surfaces-consistency
  command: 'python3 scripts/check_visual_surfaces_consistency.py'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: workflow-signals-consistency
  command: 'python3 scripts/check_workflow_signals_consistency.py'
  parallel_safe: true
  mutates: false
  cost: cheap
```

Agent smoke is intentionally not a default quality gate because it spends model budget and can take several minutes. During `ready-for-review`, ask about Codex agent smoke only when the diff includes medium/large Beislið skill changes, protocol changes (`skills/`, `.beislid/`), installer/test-install changes, or smoke harness changes (`tests/agent-smoke/`). For tiny docs-only skill prose changes, record `Codex agent smoke skipped by workflow: docs-only skill prose change` and continue without prompting. When smoke is required, stop before running it and ask exactly: `This change touches Beislið skill/smoke paths. Run Codex agent smoke now? Claude support is temporarily unavailable; this uses broad fixture permissions, model budget, and can take several minutes. [y/N]`. Default is no; do not run on silence, ambiguity, or prior blanket approval. If accepted and the host supports background subagents/tasks, start the smoke command in a non-blocking subagent, continue other side-effect-free ready-for-review work while it runs, then join before PR creation; never push/open the PR until the smoke result is known or the user explicitly accepts skipping/ignoring it. If no background runner is available, run it in the main session. Use:

```bash
python3 tests/agent-smoke/run.py gate ready-for-review --hosts codex --timeout 900 --changed-only
```


## Babysit

Enable all closeout steps by default for this repo. Babysit may merge, capture memento, and run/apply retro automatically after the green audit; each action is still bounded by runtime safety stops.

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

This repo auto-allows PR review reply posting in supervised review-response runs while keeping other remote git/PR actions on the built-in approval path.

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
      gh.pr.merge: allow
      pr.merge: allow
      memento.capture: allow
      retro.run: allow
      retro.apply: allow
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
