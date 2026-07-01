# Workflow authoring guide

Beislið keeps project policy in the repo. Teams author `<repo>/.beislid/workflow.md` to declare ticket sources, quality gates, review sources, and automation boundaries. This guide covers how to write and test that config.

For the full configuration reference, see [Configuration](./configuration.md). If you are rolling this out to teammates, start with the [team rollout guide](./team-rollout.md) before choosing optional strictness layers. For the format grammar, see [workflow.md format](../.beislid/workflow-md-format.md).

## Getting started

Run the `setup` skill to create a workflow.md interactively:

```text
/setup
```

Setup walks through each section, shows diffs before writing, and won't silently overwrite. Use `doctor` afterwards to audit the result:

```text
/doctor
```

For starter policy shapes, see [Setup templates](./setup-templates.md); for scope examples, see [Work Contract examples](./work-contract-examples.md).

If you prefer to write workflow.md by hand, create the file and add the required version stamp:

```markdown
<!-- beislid-workflow: v1 -->
```

The stamp must be the first line. Doctor rejects files without it.

## Core sections

### Issue tracker

Tell Beislið how to fetch tickets. This is needed for `kickoff` and `review-response`.

````markdown
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
````

Three source types are supported:

- **`mcp`**: call an MCP tool with the ticket ID. Use for Linear, Jira, and similar trackers exposed through MCP servers.
- **`cli`**: call a CLI command with `{id}` substituted. Example: `gh issue view {id} --json title,body,comments`.
- **`file`**: read a file matching a glob that contains the ticket ID.
- **`paste`**: strict manual paste (fallback only).

For MCP-backed trackers, an equivalent host-adapter alias is acceptable when the host registers one; probes and audits should say whether the configured tool was matched exactly or via alias.

The `id_pattern` is a regex that validates extracted ticket IDs. `branch_pattern` extracts ticket IDs from branch names: the first capture group is the ID. If your branches use names like `vic/bei-43-fix-thing`, the pattern `^[^/]+/([a-z]+-\d+)` captures `bei-43`.

Also add `ticket_update` to let orchestrators post plan comments and status updates; its issue channel is also reused by `spec_approved` tracker actions that update the ticket body:

````markdown
```beislid:ticket_update
type: mcp
comment_tool: mcp__linear__save_comment
issue_tool: mcp__linear__save_issue
```
````

### Quality gates

Gates are commands that verify branch readiness. Beislið runs them before pushes and PR creation.

**Good gate example:**

````markdown
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
  cost: expensive
- name: typecheck
  command: 'npx tsc --noEmit'
  parallel_safe: true
  mutates: false
  cost: cheap
```
````

This is good because each gate does exactly one thing (`lint`, `test`, `typecheck`), they're independent (lint and typecheck can run in parallel), and they fail fast with readable output.

**Bad gate examples:**

```yaml
# Bad: wraps everything into one opaque script that can't report which part failed
- name: check-everything
  command: 'bash scripts/check_all.sh'
```

```yaml
# Bad: modifies the working tree during a gate run
- name: format
  command: 'npx prettier --write .'
  mutates: true
```

```yaml
# Bad: installs dependencies as a gate instead of a setup step
- name: install
  command: 'npm ci'
  cost: expensive
  mutates: true
```

Mutating gates (`mutates: true`) should be rare and deliberate. Dependency installs are prerequisites, not quality proof. Legacy scopes can also use a scope-level `setup` command for codegen, installs, or other prereqs that must run once before any gates in that scope.

#### Gate metadata

| Field | Purpose |
|---|---|
| `name` | Short, unique identifier |
| `command` | Shell command to run |
| `parallel_safe` | Can run alongside other gates (`true`/`false`) |
| `mutates` | Changes the working tree (`true`/`false`) |
| `cost` | `cheap`, `moderate`, or `expensive` |
| `stage` | When the gate runs: `per-edit`, `pre-commit`, `pre-pr` (default), `post-pr`, `continuous`, `human-interrupt` |
| `kind` | `sensor` (checks something) — the only executed kind in current orchestrators |
| `execution` | `computational` (runs a command) — the only executed kind in current orchestrators |
| `timeout_seconds` | Optional timeout |

#### Gate sets (changed-file-aware selection)

When a project has different gate needs for different parts of the codebase, use `gate_sets`:

````markdown
```beislid:gate_sets
sets:
  docs:
    gates:
      - name: docs-lint
        command: 'markdownlint docs/'
  skills:
    gates:
      - name: validate-skills
        command: 'python3 scripts/validate_skills.py'
selectors:
  - name: docs-files
    paths: ['docs/**', 'README.md']
    gate_sets: ['docs']
  - name: skill-files
    paths: ['skills/**', '.beislid/**']
    gate_sets: ['skills']
```
````

When multiple selectors match, their gate sets are unioned deterministically. This keeps docs-only PRs fast while skill changes still run the full validation.

### PR reviews

Configure how Beislið reads PR review feedback and posts replies:

````markdown
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
````

The `{owner}`, `{repo}`, `{number}`, `{json_file}` placeholders are substituted at runtime. Reply bodies are written to temp files first — never interpolated into shell commands.

### Review feedback prompt profiles

Use this when PR review comments already contain agent-ready instructions but you want `review-response` to prefer the extracted prompt instead of the whole comment body. Profiles are ordered, first match wins, and they only enrich loaded feedback — they do not add a new review backend or mode.

````markdown
```beislid:review_feedback_profiles
- name: coderabbit
  match:
    source: pr_review
    author_regex: '^coderabbit(ai)?$'
  extract:
    prompt_regex: '(?s)### Agent prompt\n(?P<agent_prompt>.+)$'
    prompt_format: coderabbit
```
````

Use this for already-posted GitHub review comments. CodeRabbit CLI or "run a new review now" workflows stay out of scope here.

### AgenticReviewer opt-in policy

Use `review_policy` when an AI reviewer is a scarce final-review resource. AgenticReviewer is the role; `provider` can name CodeRabbit or another concrete service.

````markdown
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
````

`ready-for-review` adds the configured label only for PRs whose risk is above the closeout threshold; `label` is required for automatic opt-in. `babysit` blocks closeout for those PRs until a real provider review exists; skipped/rate-limited/deferred comments do not count.

### PR target

If your default base is not `main`, or you use a non-`origin` remote:

````markdown
## PR target

```beislid:pr_base
default: develop
```

```beislid:pr_host
owner: my-org
repo: my-repo
remote: upstream
```
````

### Action policy

Action policy controls what risky side effects are allowed without human approval. Two modes:

- **`supervised-auto`**: human is present, can approve prompts. Reads and network reads auto-allow; writes and local git ask; destructive operations deny.
- **`unattended-auto`**: runs AFK. Reads and network reads auto-allow; workspace writes and local git ask; remote git, destructive, and secret-bearing operations deny.

Override per-class or per-action:

````markdown
## Action policy

```beislid:action_policy
modes:
  unattended-auto:
    actions:
      pr.review.reply: allow
      git.push: allow
      gh.pr.create: allow
```
````

This relaxes review replies, pushes, and PR creation in unattended mode — useful for babysit loops. Protected classes (`destructive`, `secret-bearing`) can never be relaxed per-action; you must change the mode-wide class rule instead.

### Babysit

For automated PR babysitting and closeout:

````markdown
## Babysit

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
````

- `loop.use_review_response: false` if you want babysit to summarize feedback rather than auto-fixing.
- `closeout.merge.mode: ask` requires explicit approval before merging.
- `closeout.retro.apply_findings: auto` auto-applies safe workflow recommendations.

### Lifecycle actions

Lifecycle actions run side effects at named workflow events. They are not quality gates — gates verify branch readiness; lifecycle actions update external systems, write planning artifacts, or run configured approval-time hooks. For before/after phase hooks, use `lifecycle_hooks`.

````markdown
## Lifecycle actions

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: assign-ticket
        type: cli
        command: 'gh issue edit {id} --add-assignee @me'
        approval: auto
        on_failure: prompt
  spec_approved:
    actions:
      - name: write-spec-artifact
        type: artifact
        approval: prompt
        path: 'plans/{feature}-spec.md'
      - name: post-spec-body-to-tracker
        type: tracker
        approval: prompt
      - name: run-approved-spec-hook
        type: cli
        command: 'planning-hook {event} {ticket_id} {artifact_path}'
        approval: prompt
        classes: [git-remote]
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        path: 'plans/{feature}-design.md'
```
````

- `type: cli` actions run a command with safe placeholders. Kickoff supports `{ticket_id}`, `{id}`, `{branch}`, and `{event}`; planning approval events also support `{feature}`, `{kind}`, and `{artifact_path}`.
- `type: artifact` actions write a local Markdown file after approval. When the template is custom, keep it deterministic and prefer stable placeholders so downstream skills can rediscover the same path later from the workflow config and latest pointer context.
- `type: tracker` actions post the approved spec body into the current ticket body through the configured `ticket_update` issue channel and are gated by `ticket.update` policy.
- `approval: auto` runs a CLI/tracker action or creates a missing artifact without prompting; `approval: prompt` asks first. Existing artifact files still require an overwrite/choose/skip decision.
- `on_failure` is optional and defaults to `prompt`, preserving the retry / skip-this-session / abort flow. Use `continue` for best-effort side effects that should only warn, or `abort` for mandatory side effects that must stop the workflow on failure.
- Planning approval events support `artifact` and `cli`, with `tracker` additionally supported under `spec_approved`; checkpoint events remain artifact-only. Unsupported providers are reported by doctor and skipped by skills. Planning artifact writes should remain template-based so later-session rediscovery can resolve custom paths from the workflow config and latest pointer context, but only when those placeholder inputs are still recoverable.

`ready-for-review` can layer on `ship_time_artifacts` to summarize generated planning artifacts at handoff, including custom paths rediscovered from the workflow config or latest pointer when present. The policy is narration-only in v1; it does not auto-commit or auto-delete files.

```beislid:ship_time_artifacts
mode: remind
```

### Lifecycle hooks

Lifecycle hooks run around phase boundaries instead of named approval events. Use them for repo-owned checks or integrations before and after `spec`, `blueprint`, `implement`, `verify`, `review`, `fresh_eyes`, `ready_for_review`, or `review_response`.

````markdown
## Lifecycle hooks

```beislid:lifecycle_hooks
phases:
  implement:
    before:
      actions:
        - name: repo-health-check
          type: cli
          command: 'python3 scripts/check_workflow_signals_consistency.py'
          approval: auto
          when:
            paths: ['skills/**', '.beislid/**']
  ready_for_review:
    after:
      actions:
        - name: release-notes-check
          type: cli
          command: 'python3 scripts/check_model_routing_step_hints_consistency.py'
          approval: prompt
          when:
            paths: ['WORKFLOW.md', '.beislid/**']
            branch_pattern: '^feature/'
```
````

Hook actions use the same safety model as lifecycle actions: approval governs prompts, action policy governs side effects, and trigger rules can narrow execution to relevant files, scopes, or a `branch_pattern`. Hooks do not replace gates.

### Other sections

| Section | Purpose |
|---|---|
| `beislid:model_routing` | Declare preferred models per skill tier |
| `beislid:pi_handoff` | Configure Pi auto-handoff from checkpoint pointers |
| `beislid:visual_surfaces` | Route to optional Lavish visual surfaces |
| `beislid:workflow_signals` | Local tmux-glance tab markers |
| `beislid:lifecycle_hooks` | Custom phase-boundary hooks |
| `beislid:explore` | Custom explore skills for kickoff |
| `beislid:probe_cache` | Capability probe cache TTL |
| `beislid:guided_walkthrough` | Diff walkthrough thresholds |

See [Configuration](./configuration.md) for the full reference.

## Testing your workflow

### Run the doctor

After writing workflow.md, audit it:

```text
/doctor
```

Doctor checks:
- Version stamp and section grammar
- Known vs unknown config keys
- Fenced block syntax
- Whether configured commands and tools are reachable
- Probe cache freshness
- Action policy, model routing, and visual surface validity

### Run configured gates manually

Before relying on orchestrator gate execution, run each gate command from the repo root to verify it works:

```bash
# From the repo root, run each gate's command:
npx eslint . --max-warnings 0
npm test
python3 scripts/validate_skills.py
```

Fix any gate that fails or doesn't execute before expecting orchestrators to use it.

### Test with a trial branch

The surest test is a real branch:

1. Create a branch with a trivial change matching the files your gates should cover.
2. Run `/kickoff` (for ticket workflows) or `/ready-for-review` (for PR handoff).
3. Verify that configured gates run, ticket/PR sources work, and policy decisions match expectations.

### Dry-run action policy

Use the CLI to test action-policy decisions before relying on them:

```bash
beislid action-policy evaluate --mode unattended-auto --action git.push --sandbox-baseline separate-worktree
```

This returns the decision envelope without executing anything.

### Common pitfalls

- **Gate commands fail on a clean checkout.** Test each command from the repo root before wiring it as a gate. Prerequisites like `npm ci` or `pip install` are setup steps, not quality gates.
- **Parallel gates fight each other.** If two gates write to the same temp file, lock a resource, or depend on each other's output, mark them `parallel_safe: false` or use gate sets to run them separately.
- **`mutates: false` but the command writes files.** Linters with `--fix`, formatters with `--write`, and auto-generators are mutating gates. Mark them honestly.
- **Branch pattern doesn't match.** Test with `echo "vic/bei-43-some-feature" | grep -E '^[^/]+/([a-z]+-\d+)'`. The pattern must capture the ticket ID in group 1.
- **Ticket ID case mismatch.** The pattern `^[A-Z]{2,4}-\d+$` expects uppercase (`BEI-43`). If your branch extractor returns lowercase (`bei-43`), Beislið normalizes to the pattern's case. If both are uppercase, no normalization is needed.

## Examples

For complete, drop-in team workflow configurations, see [docs/examples/README.md](./examples/README.md). The examples there cover seven common team shapes and are intended to be copied into `.beislid/workflow.md`.

### Minimal workflow for a solo developer

```markdown
<!-- beislid-workflow: v1 -->

## Issue tracker

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body'
id_pattern: '^ISSUE-\d+$'
```

## Quality gates

```beislid:gates
- name: lint
  command: 'npx eslint .'
  parallel_safe: true
  mutates: false
  cost: cheap
- name: test
  command: 'npm test'
  parallel_safe: false
  mutates: false
  cost: expensive
```
```

### Team workflow with Linear, PR reviews, and babysit

```markdown
<!-- beislid-workflow: v1 -->

## Issue tracker

```beislid:ticket_source
type: mcp
tool: mcp__linear__get_issue
id_pattern: '^[A-Z]{2,4}-\d+$'
```

```beislid:branch_pattern
^[^/]+/([a-z]+-\d+)
```

```beislid:ticket_update
type: mcp
comment_tool: mcp__linear__save_comment
issue_tool: mcp__linear__save_issue
```

## PR reviews

```beislid:pr_review_source
type: cli
summary_command: 'gh pr view --json url,number,reviewDecision,reviews,comments'
```

```beislid:pr_review_update
type: cli
reply_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments --method POST --input {json_file}'
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
```

## Babysit

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
```

With this config, `kickoff` fetches Linear tickets, `ready-for-review` runs gates and creates PRs, `review-response` handles feedback, and `babysit` monitors the PR loop with human approval at closeout.

### Multi-scope project with gate sets

```markdown
<!-- beislid-workflow: v1 -->

## Gate sets

```beislid:gate_sets
sets:
  frontend:
    gates:
      - name: lint-fe
        command: 'cd web && npm run lint'
      - name: test-fe
        command: 'cd web && npm test'
  backend:
    gates:
      - name: lint-be
        command: 'cd api && cargo clippy'
      - name: test-be
        command: 'cd api && cargo test'
selectors:
  - name: frontend-files
    paths: ['web/**']
    gate_sets: ['frontend']
  - name: backend-files
    paths: ['api/**']
    gate_sets: ['backend']
```
```

Only the gates matching changed files run. A frontend-only PR skips the Rust gates entirely.
