# Beislið workflow.md format — v1

Per-project Beislið config lives at `<repo>/.beislid/workflow.md`. The file mixes prose for humans with typed-key fenced YAML blocks that orchestrators parse for capability values.

## Version stamp

The first line of the file MUST be:

```
<!-- beislid-workflow: v1 -->
```

Doctor reads this line. A mismatch hard-fails with prose pointing at upgrading Beislið or downgrading workflow.md by hand. Future versions can offer migration when they encounter older stamps.

## Section grammar

Sections are H2 headings (`##`) with topic-based names. Doctor and orchestrators identify sections by these canonical names (case-insensitive on the first H2 occurrence):

- `Issue tracker`
- `PR target`
- `PR reviews`
- `Scopes`
- `Quality gates`
- `Lifecycle actions`
- `Translation sync`
- `Browser compat`
- `Domain capture`
- `PR description`
- `Guided walkthrough`
- `Probe cache`
- `Skill-specific overrides`
- `Ready-for-review`
- `Review-response`
- `Kickoff` (put `beislid:explore` here or under `Skill-specific overrides`)

Section order is irrelevant to parsing. Sections that aren't in this list are ignored with a `💭` inline note from doctor; their fenced blocks are skipped.

## Fenced block grammar

Typed-key fenced blocks are the structured input source for orchestrators. The info string format is:

````
```beislid:<key>
```
````

`<key>` is dot-pathed for nested capabilities (`domain_expert.agent`, `pr_description.formatter_skill`, `translation_sync.trigger_paths`). Block content is YAML. Single-value blocks may be a bare scalar.

Example:

````
```beislid:ticket_source
type: mcp
tool: mcp__plugin_linear_linear__get_issue
id_pattern: '^[A-Z]{2,4}-\d+$'
```

```beislid:branch_pattern
^([A-Z]{2,4}-\d+)
```
````

## Canonical fenced keys

Keys recognized by Beislið orchestrators. Optional fields are noted; the rest are required when the parent key is set.

**Issue tracker:**
- `ticket_source` — fields: `type` (`mcp` / `cli` / `file` / `paste`), `tool` (when `type: mcp`), `command` (when `type: cli`, with `{id}` placeholder), `file_glob` (when `type: file`), `id_pattern` (regex), `link_template` (optional, with `{id}` placeholder)
- `branch_pattern` — single regex string; per-project only, never user-level
- `ticket_update` — shared by kickoff and review-response. Fields: `type` (`mcp` / `cli`); comment channel is used for kickoff plan comments and review-response ticket replies (`comment_tool` when `type: mcp`, `comment_command` when `type: cli`); issue channel is optional for review-response child tickets (`issue_tool` / `issue_command`). CLI comment commands use `{id}` + `{body_file}` placeholders; issue commands use `{title_file}` + `{body_file}`. Orchestrators write temp files and substitute file paths — never interpolate raw user-authored body/title text into shell commands.

**PR target:**
- `pr_base.default` — base branch name (e.g. `main`)
- `pr_host.owner`, `pr_host.repo`, `pr_host.remote` — auto-derived from `origin` if absent; explicit override when fork or non-`origin` remote

**PR reviews:**
- `pr_review_source` — fields: `type` (`cli` / `paste`); for `type: cli`, `summary_command` is required and `threads_command` is optional. Placeholders: `{owner}`, `{repo}`, `{number}`, `{url}`. Missing `threads_command` means review-response can read PR-level comments but may miss inline review threads.
- `pr_review_update` — fields: `type` (`cli` / `manual`); for `type: cli`, `reply_command` is required and `rerequest_command` is optional. Commands receive a temp JSON payload via `{json_file}`. Placeholders: `{owner}`, `{repo}`, `{number}`, `{json_file}`. MCP PR review providers are intentionally deferred.

**Scopes and gates:**
- `scopes` — list of scope objects, each with `name`, `paths` (glob list), `cwd`, `gates` (list of gate objects; see **Gate object shape** below)
- `split_policy` — single string; `exclusive` is the only recognized value
- `gates` (top-level) — single gate list when `scopes` is not configured; same gate object shape as a scope's gates

**Lifecycle actions:**
- `lifecycle_actions` — event-keyed side effects. P0 executable events are `events.kickoff_start.actions[]`, `events.spec_approved.actions[]`, and `events.blueprint_approved.actions[]`. `kickoff_start` supports `type: cli`; spec/design approval events support `type: artifact` only. Every action has `name` and `type`. CLI actions use `command` and require `approval` (`auto` / `prompt`). Artifact actions may use optional `approval` (defaults to `prompt`) plus optional `path` file templates and placeholders `{feature}`, `{kind}`, and `{ticket_id}`. Actions run in order.

**Kickoff overrides:**
- `explore` — fields: `skill` (Beislið skill name), `mode` (`replace` or `enhance`; default `enhance`). Put this block under a `## Kickoff` or `## Skill-specific overrides` section. Used by kickoff Step 2 before implementation design.

**Triggered skills:**
- `translation_sync.skill`, `translation_sync.trigger_paths`
- `browser_compat.skill`, `browser_compat.trigger_paths`
- `pr_description.formatter_skill`, `pr_description.formatter_args` (optional map)

**Paired (Phase 4d of ready-for-review):**
- `domain_expert.agent` — subagent name (paired with `knowledge_store.path`)
- `knowledge_store.path` — repo-relative path (paired with `domain_expert.agent`)

**Walkthrough thresholds:**
- `guided_walkthrough.threshold_files`, `guided_walkthrough.threshold_lines`

**Cache:**
- `probe_cache` — fields: `ttl_hours` (integer; defaults to 24 when absent)

Capabilities not in this list are unknown — doctor reports them with a `💭` inline note and continues.

## Gate object shape

Gate lists are backward-compatible. Existing flat gates remain valid:

```yaml
- name: test
  command: npm test
  autofix: npm run lint -- --fix # optional
  parallel_safe: true          # optional fast-path hint for independent read-only gates
```

A flat gate is shorthand for a staged sensor with these defaults: `stage: pre-pr`, `kind: sensor`, `execution: computational`, `mutates: false`, no selector, no output parser, and no retry policy beyond the orchestrator's normal user-directed failure handling.

Rich gates may add harness metadata. `name` is always required. `command` is required for executable command gates, including every P0-runnable gate; non-command declarations must be explicitly represented through `kind` or `execution` metadata and are reported rather than executed by P0 orchestrators:

```yaml
- name: full-tests
  stage: pre-pr
  kind: sensor
  execution: computational
  command: '.venv/bin/python -m pytest'
  timeout_seconds: 600
  cost: expensive
  mutates: false
  accepts_files: false
  required_tools: ['python']
  changed_file_selector:
    include: ['memento/**/*.py', 'hooks/**/*.py', 'tests/**/*.py']
  output:
    parser: pytest
    agent_summary: true
  failure:
    retryable: true
    max_fix_iterations: 2
    stop_if_patterns:
      - 'No module named'
    hint: 'Fix failing tests. If this is an environment issue, stop and report it.'
```

Supported stage values are `preflight`, `per-edit`, `pre-commit`, `pre-pr`, `post-pr`, `continuous`, and `human-interrupt`. P0 `ready-for-review` and `review-response` execute legacy gates and computational `stage: pre-pr` sensor gates only; other stages are valid metadata for Rondo/future orchestrators and must be reported, not silently executed at the wrong lifecycle point.

`kind` currently recognizes `sensor` for gates that observe readiness. Future guide/feedforward artifacts are tracked separately from gate lists. P0 command execution runs only gates where `kind` is absent or `sensor`; other `kind` values are metadata declarations that are reported as non-sensor and not executed. `execution` may be `computational`, `inferential`, or `human`; P0 command execution supports `computational` gates directly and reports `inferential`/`human` entries as non-command metadata declarations unless a future orchestrator owns them.

`cost` is free-form but recommended values are `cheap`, `medium`, and `expensive`. `required_tools` is a list of additional CLI binaries the gate depends on beyond the command's first word; doctor and gate-running orchestrators probe each with `command -v` before treating the gate as runnable. `mutates: true` means the gate may edit files or external state and must not be auto-batched as read-only. `parallel_safe: true` remains the fast-path batching flag and is only honored when the gate has no `autofix` and `mutates` is not true.

Selectors may use `changed_file_selector.include` / `exclude` glob lists (or legacy draft `selector.paths`) to describe when the gate is relevant. P0 docs and doctor report selector metadata; full changed-file-aware selection is reserved for the dedicated selector work.

Output/parser metadata is declarative. `output.parser` may name parsers such as `generic-text` or `pytest`, but the full agent-readable result envelope is handled by the gate-result-envelope work. `failure` may declare `retryable`, `max_fix_iterations`, `stop_if_patterns`, and `hint`; P0 orchestrators surface this context in failure prompts but still require user direction before risky fixes or skips.

## Lifecycle actions shape

Lifecycle actions are optional side effects at named workflow events. They are not quality gates: gates prove branch readiness, while lifecycle actions mutate external systems or create user-approved records.

P0 executes ordered CLI actions for `kickoff_start`, immediately after kickoff fetches ticket context:

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
      - name: move-in-progress
        type: cli
        command: 'example-tracker transition {ticket_id} in-progress --branch {branch}'
        approval: auto
```
````

For CLI actions, `approval` is required. `approval: auto` runs once configured and asks only on failure. `approval: prompt` asks before running. Orchestrators must pass placeholder values through argv construction when available or shell-quote them before execution; raw branch/ticket text must not be spliced into a shell.

P0 also executes artifact actions for approved planning outputs:

````markdown
## Lifecycle actions

```beislid:lifecycle_actions
events:
  spec_approved:
    actions:
      - name: write-spec-artifact
        type: artifact
        approval: prompt
        # optional; default is plans/{feature}-spec.md
        path: 'plans/{feature}-spec.md'
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        # optional; default is plans/{feature}-design.md
        path: 'plans/{feature}-design.md'
```
````

`spec` owns the `spec_approved` event; `blueprint` owns the `blueprint_approved` event. Kickoff only passes context in and records returned artifact status/path. Under these events, P0 supports `type: artifact` only; CLI, MCP, and other providers are reserved and skipped. Artifact actions write the approved spec/design Markdown to a repo file. `approval: prompt` asks before writing; `approval: auto` creates a missing target without another prompt; omitted approval defaults to `prompt`. Existing targets always prompt for overwrite / choose another path / skip. Skip and write failures do not block routing to downstream skills.

Artifact `path` is a file path template. If omitted, defaults are `plans/{feature}-spec.md` for specs and `plans/{feature}-design.md` for designs. Supported placeholders are `{feature}` (slug from approved title, then ticket title, then branch, else ask), `{kind}` (`spec` or `design`), and `{ticket_id}` when ticket context is known. If `{ticket_id}` is used and no ticket id is available, runtime asks for another path or skip; it must not write `unknown` or silently drop the placeholder. Paths must be relative, stay inside the repo root, contain no `..` segments, and end in `.md`. Parent directories may be created as part of an approved or auto write.

Future events such as `pr_opened`, broader action providers for planning events, tracker posting, and ship-time artifact handling are reserved for later Beislið versions.

## Explore skill shape

Use a custom skill to replace or enhance kickoff's default codebase exploration. Put it under a recognized Kickoff/Skill-specific overrides section:

````markdown
## Kickoff

```beislid:explore
skill: guide
mode: enhance
```
````

`replace` means the skill must provide the Step 2 context packet instead of default exploration. If it fails, kickoff prompts to retry, fall back to default exploration for this session, or abort. `enhance` runs default exploration first, then merges skill findings when available.

## PR reviews worked shape

```markdown
## PR reviews

​```beislid:pr_review_source
type: cli
summary_command: 'gh pr view --json url,number,reviewDecision,reviews,comments'
threads_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments'
​```

​```beislid:pr_review_update
type: cli
reply_command: 'gh api repos/{owner}/{repo}/pulls/{number}/comments --method POST --input {json_file}'
rerequest_command: 'gh api repos/{owner}/{repo}/pulls/{number}/requested_reviewers --method POST --input {json_file}'
​```
```

For `pr_review_update`, review-response writes JSON payload files instead of interpolating comment bodies into shell strings. Reply payloads use `{ "body": "...", "in_reply_to": 123 }`; re-request payloads use `{ "reviewers": ["octocat"] }`.

Manual PR review source is explicit:

````markdown
```beislid:pr_review_source
type: paste
```
````

Manual PR review updates are explicit:

````markdown
```beislid:pr_review_update
type: manual
```
````

## Disabled-state convention

To disable a capability for a project, write a section whose prose explicitly says "Disabled for this project" (or similar) and omit the fenced block. Doctor records the capability as `disabled` — semantically distinct from `missing` (probe failed) and from absent-from-the-file (treated as `not configured`).

Disabled is a deliberate user choice. Missing is a probe result. Not-configured is silence.

## Skill-specific subsections

H3 subsections under a skill name hold capabilities only one orchestrator uses. Naming pattern: H3 named after the skill in title case. Capabilities still use the same `beislid:<key>` info-string convention.

```
### Ready-for-review overrides

​```beislid:guided_walkthrough.threshold_files
8
​```
```

## Duplicate keys

When the same `beislid:<key>` appears in multiple fenced blocks, the **first occurrence wins**. Doctor warns about subsequent duplicates in prose, naming the line of each. This is lenient by design — duplicates usually come from copy-paste or merge conflicts; the audit surfaces them so the user can clean up.

## Worked example

```markdown
<!-- beislid-workflow: v1 -->

# Beislið workflow config — example-project

## Issue tracker

GitHub Issues on `acme/example-project`, accessed via the `gh` CLI.

​```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body,labels'
id_pattern: '^#?\d+$'
​```

​```beislid:branch_pattern
^(\d+)-
​```

## Scopes

Frontend (Next.js) and backend (Hono) get different gates.

​```beislid:scopes
- name: frontend
  paths: ['apps/web/**']
  cwd: apps/web
  gates:
    - { name: lint, command: 'pnpm lint' }
    - name: typecheck
      stage: pre-pr
      kind: sensor
      execution: computational
      command: 'pnpm typecheck'
      timeout_seconds: 120
      cost: medium
      mutates: false
      output:
        parser: generic-text
      failure:
        retryable: true
        max_fix_iterations: 1
- name: backend
  paths: ['apps/api/**']
  cwd: apps/api
  gates:
    - { name: lint, command: 'bun run lint' }
​```

​```beislid:split_policy
exclusive
​```

## Translation sync

Disabled for this project.

## Browser compat

Disabled — no shared frontend components.

## Domain capture

​```beislid:domain_expert.agent
researcher
​```

​```beislid:knowledge_store.path
knowledge-base/
​```

## Probe cache

​```beislid:probe_cache
ttl_hours: 24
​```
```
