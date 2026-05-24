<!-- beislid-workflow: v1 -->

# Beislið workflow config — beislid

This is the Beislið distribution repo's own workflow config. It dogfoods the v0.2 markdown-as-config pattern and supersedes the legacy per-skill YAML config files deleted in this PR.

## Issue tracker

GitHub Issues on `sandsower/beislid`, accessed via the `gh` CLI. Issue IDs are bare numbers (e.g. `#11`), no ticket-prefix scheme.

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json number,title,body,state,labels'
id_pattern: '^#?\d+$'
```

No project-wide branch pattern — taumar branches use a mix of `victor/<topic>`, `phase-N-<feature>`, and `release/<name>`. Skipping `branch_pattern` means orchestrators ask for the ticket ID at the start of each run when they need one.

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
- name: skill-size-budgets
  command: 'python3 scripts/check_skill_size_budgets.py'
- name: validate-skills
  command: 'python3 scripts/validate_skills.py'
```

Agent smoke is intentionally not a default quality gate because it spends model budget and can take several minutes. During `ready-for-review`, if the diff touches Beislið skill/protocol files (`skills/`, `.beislid/`), installer/test-install paths, or the smoke harness (`tests/agent-smoke/`), stop before running smoke and ask exactly: `This change touches Beislið skill/smoke paths. Run Codex agent smoke now? Claude support is temporarily unavailable; this uses broad fixture permissions, model budget, and can take several minutes. [y/N]`. Default is no; do not run on silence, ambiguity, or prior blanket approval. Recommend running it for medium/large skill changes, protocol changes, installer changes that affect skill discovery, and any change to the smoke harness itself. Record the answer in the ready-for-review summary. If accepted and the host supports background subagents/tasks, start the smoke command in a non-blocking subagent, continue other side-effect-free ready-for-review work while it runs, then join before PR creation; never push/open the PR until the smoke result is known or the user explicitly accepts skipping/ignoring it. If no background runner is available, run it in the main session. Use:

```bash
python3 tests/agent-smoke/run.py gate ready-for-review --hosts codex --timeout 900 --changed-only
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
