<!-- beislid-workflow: v1 -->

# Beislið workflow config — jira-gitlab-team

**Audience:** Enterprise team using Jira for issue tracking and GitLab
(self-hosted or cloud) for source control and merge requests. Team works on
a backend service in Python.

**Team policy:** Jira issues drive all work. GitLab merge requests are the
review surface. `glab` CLI provides programmatic access to MR comments and
status. Quality gates run linting, type checking, and tests before every MR.
Babysit is configured but asks before merging — this team requires a human
merge decision.

**Expected flow:** `kickoff` (fetches Jira ticket via MCP) → `blueprint` →
`implement` → `verify` → `ready-for-review` → GitLab MR → `review-response`/
`babysit` → human merges when approved.

## Issue tracker

Jira tickets accessed through the Jira MCP server. The branch pattern expects
the ticket key to appear after the author prefix.

```beislid:ticket_source
type: mcp
tool: mcp__jira__get_issue
id_pattern: '^[A-Z]{2,6}-\d+$'
link_template: 'https://mycompany.atlassian.net/browse/{id}'
```

```beislid:branch_pattern
^[^/]+/([a-z]+-\d+)
```

Jira MCP also provides a comment tool for ticket updates.

```beislid:ticket_update
type: mcp
comment_tool: mcp__jira__add_comment
```

## PR target

The team uses `develop` as the integration branch and merges to `main` on
release.

```beislid:pr_base
default: develop
```

```beislid:pr_host
owner: my-org
repo: backend-service
remote: origin
```

## PR reviews

GitLab merge request feedback through the `glab` CLI. Summary and threads
commands read MR-level and inline comments.

```beislid:pr_review_source
type: cli
summary_command: 'glab mr view --repo {owner}/{repo} --output json'
threads_command: 'glab api projects/{owner}%2F{repo}/merge_requests/{number}/discussions'
```

```beislid:pr_review_update
type: cli
reply_command: 'glab api projects/{owner}%2F{repo}/merge_requests/{number}/discussions --method POST --input {json_file}'
```

## Quality gates

Python backend gates: lint with ruff, typecheck with mypy, test with pytest.
Integration tests are a separate expensive gate.

```beislid:gates
- name: lint
  command: '.venv/bin/python -m ruff check .'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: typecheck
  command: '.venv/bin/python -m mypy src/'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: unit-test
  command: '.venv/bin/python -m pytest tests/unit/ -v'
  parallel_safe: false
  mutates: false
  cost: moderate
- name: integration-test
  command: '.venv/bin/python -m pytest tests/integration/ -v'
  parallel_safe: false
  mutates: false
  cost: expensive
```

## Lifecycle actions

Assign the Jira ticket and move it to "In Progress" on kickoff start.

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: assign-to-me
        type: cli
        command: 'jira issue assign {id} $(jira me)'
        approval: auto
      - name: transition-in-progress
        type: cli
        command: 'jira issue move {id} "In Progress"'
        approval: auto
```

## Action policy

Unattended runs may push, create MRs (through `glab`), and reply to MR
comments. GitLab MR creation is modeled as `gh.pr.create` in the action
registry.

```beislid:action_policy
modes:
  unattended-auto:
    actions:
      pr.review.reply: allow
      git.push: allow
      gh.pr.create: allow
```

## Babysit

Babysit loops at 90-second intervals to avoid rate-limiting the self-hosted
GitLab instance.

```beislid:babysit
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 90
closeout:
  merge:
    mode: ask
    method: repo-default
    delete_branch: true
  memento:
    mode: ask
  retro:
    mode: ask
```

## Model routing

Use Anthropic for design work and Codex/DeepSeek for implementation throughput
via OpenRouter.

```beislid:model_routing
defaults:
  models: [openrouter:deepseek/deepseek-v4-pro]
  mode: prefer
overrides:
  - skills: [spec, blueprint, poke-holes]
    models: [anthropic:claude-opus-4.8]
    mode: require
  - skills: [implement, ready-for-review]
    models: [openrouter:deepseek/deepseek-v4-pro, openai:gpt-5.1-codex]
    mode: prefer
```

## Turn this into your own config

1. Verify your Jira MCP tool name — it might be `mcp__atlassian_jira__get_issue`
   or similar. Run `/doctor` and check the probe output.
2. If you use `gitlab` CLI instead of `glab`, adjust the PR review commands.
   The project path encoding (`%2F` for `/`) is `glab`-specific.
3. Replace `.venv/bin/python` with your Python environment path.
4. Adjust the `branch_pattern` if your team uses a different naming convention.
5. If your GitLab instance uses a different URL, update the `link_template`
   and ensure `glab` is authenticated.
6. Remove or replace `transition-in-progress` if your Jira workflow uses
   different status names.