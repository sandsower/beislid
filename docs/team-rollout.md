# Team rollout guide

Use this guide when you want a repository to be Beislið-ready for a whole team, not just one local agent session. The goal is to commit the minimum shared workflow first, prove it with `doctor`, then add stricter layers only when the team is ready for them.

## Rollout path

1. **Start with a pilot branch.** Install Beislið, run `/setup`, and let it create `.beislid/workflow.md` plus the `AGENTS.md` agent-skills block. Keep the first pass small enough that teammates can review the policy in one PR.
2. **Commit the minimum viable config.** At minimum, repo-aware workflows need the version stamp, a ticket source strategy, optional branch detection, and probe-cache settings. Add gates in the same PR only when the commands already pass from a clean checkout.
3. **Audit before relying on it.** Run `/doctor` after every config change. Fix missing tools, invalid fenced blocks, or unreachable integrations before asking agents to use the workflow unattended.
4. **Explain the human workflow.** Tell teammates which entry point to use (`kickoff`, `ready-for-review`, `review-response`, or `babysit`), what evidence gates run, and where the agent must stop for approval.
5. **Layer in strictness gradually.** Add ticket updates, PR review replies, domain checks, and babysit closeout only after the lower layers are trusted.

If you want a starter bundle instead of writing the policy from scratch, begin with [Setup templates](./setup-templates.md) and keep the first rollout small.

## Minimum viable `workflow.md`

A minimal repo-aware config is intentionally plain Markdown with typed fenced blocks:

````markdown
<!-- beislid-workflow: v1 -->

# Beislið workflow config — my-repo

## Issue tracker

```beislid:ticket_source
type: paste
id_pattern: '^[A-Z]+-\d+$'
```

```beislid:branch_pattern
^[^/]+/([a-z]+-\d+)
```

## Probe cache

```beislid:probe_cache
ttl_hours: 24
```
````

Use `type: paste` when the repo is not ready to wire a tracker yet; `kickoff` and PR handoff flows will ask for strict ticket context instead of guessing. For a GitHub Issues repo with `gh` available, replace the ticket source with:

````markdown
```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body,labels,url'
id_pattern: '^#?\d+$'
link_template: 'https://github.com/my-org/my-repo/issues/{id}'
```
````

For Linear, Jira, or another MCP-backed tracker, use the MCP tool that your host exposes:

````markdown
```beislid:ticket_source
type: mcp
tool: mcp__linear__get_issue
id_pattern: '^[A-Z]+-\d+$'
link_template: 'https://linear.app/my-workspace/issue/{id}'
```
````

## Strictness layers

Add these layers in order. Each layer should be committed, audited with `/doctor`, and exercised on a small branch before moving to the next.

| Layer | Add when | Typical config |
| --- | --- | --- |
| Ticket source + branch pattern | Agents need ticket context without pasting every run | `ticket_source`, `branch_pattern` |
| Quality gates | Commands pass locally and are stable on clean checkouts | `gates`, `gate_sets`, or `scopes` |
| PR review reading | `review-response` should categorize existing PR feedback | `pr_review_source` |
| Ticket updates | Kickoff plans and QA replies should be recorded in the tracker | `ticket_update` |
| PR review replies | Agents may post clear-fix replies after addressing feedback | `pr_review_update` plus action policy |
| Domain or triggered checks | Work needs repository-specific expertise beyond generic code search | `domain_expert`, `translation_sync`, `browser_compat` |
| Babysit closeout | The team trusts the loop to keep PRs green and, by policy, merge or run retros | `babysit`, `action_policy` |

Keep gates as proof, not setup. Put dependency installs, codegen, or cache warmups in a scope-level `setup` command (or an equivalent prereq step), not inside a gate that claims readiness.

## `AGENTS.md` block

`/setup` writes or updates this block so any agent opening the repo can find the workflow contract:

```markdown
## Agent skills

This repo uses [Beislið](https://github.com/sandsower/beislid) for orchestrator skills.

- Project config: `.beislid/workflow.md`
- Audit setup: `/doctor`
- Configure: `/setup`
```

Teams can add local house rules elsewhere in `AGENTS.md`, but keep this block short and stable. The detailed policy belongs in `.beislid/workflow.md`.

## After `/setup` writes config

Before merging the rollout PR:

1. Run `/doctor` and save or summarize the audit result in the PR.
2. Run every configured gate command from the repo root once.
3. Commit `.beislid/workflow.md` and `AGENTS.md` together.
4. Ask one teammate to read the strictness table and confirm the approval boundaries match how the team works.
5. Try one low-risk ticket branch with `kickoff → blueprint → implement → verify → ready-for-review`.

If any step fails, keep the lower layer and open a follow-up issue for the stricter integration rather than expanding the rollout PR.
