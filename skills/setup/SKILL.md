---
name: setup
description: Configure Beislið project config (`.beislid/workflow.md`) interactively, or update an installed Beislið distribution. Use when the user says "setup", "/setup", "setup update", "/setup update", "update beislid", "configure beislid", "set up workflow", "add scopes", "change ticket source", "reconfigure beislid", or any intent to add, change, or remove a workflow.md section. Walks through sections conversationally; shows a diff before any destructive write.
---

# Setup

Initialize or update Beislið's per-project config at `<repo>/.beislid/workflow.md`, or run the Beislið distribution updater when invoked as `setup update` / `/setup update`. Setup is the canonical config interface — direct file editing still works as an escape hatch but isn't surfaced in user-facing prose.

**First run** (no workflow.md): run a minimal-required interview (ticket source, branch pattern, default PR base, probe cache), write the file, insert a `## Agent skills` block in `AGENTS.md`, then offer the same menu shown on re-run for adding optional sections.

**Re-run** (workflow.md exists): show a menu — add a section, change a configured section, remove a configured section, reset and regenerate, or cancel. Never silently overwrites; every destructive write shows a diff and asks for confirmation.

Format reference: `workflow-md-format.md` (symlink to the master). Probe semantics for capability discovery: `probe-semantics.md` (symlink to the master).

## 0. Update mode

If the invocation includes update intent (`setup update`, `/setup update`, `update beislid`, or equivalent), do not enter project-config setup and do not read or write `<repo>/.beislid/workflow.md`.

Run this distribution-update flow instead:

1. Resolve the install manifest path: `${BEISLID_STATE_DIR:-$HOME/.local/state/beislid}/install.json`.
2. Read the manifest. If missing, hard-fail with:

   ```
   🛑 No Beislið install manifest found at `<manifest>`. Run `install.sh --update`
   from your Beislið checkout, or reinstall Beislið with `<beislid-repo>/install.sh`.
   ```

3. Read `repo` from the manifest. If empty, missing, or not a directory, hard-fail with:

   ```
   🛑 Beislið install manifest does not point at a valid repo: `<repo>`.
   Run `install.sh --update` from your Beislið checkout, or reinstall Beislið.
   ```

4. Check `<repo>/install.sh` exists and is executable. If not, hard-fail with the same recovery guidance.
5. Show the planned action and ask for confirmation:

   ```
   📋 Update Beislið from `<repo>`?

   This will run:
   `<repo>/install.sh --update`

   The installer will abort if the Beislið checkout has uncommitted changes,
   preserve prior install targets and opt-ins from the manifest, fast-forward
   with `git pull --ff-only`, then relink skills/hooks as needed.

   Proceed? [Y/n]
   ```

6. On `n`, exit cleanly without running anything. On `Y`, run `<repo>/install.sh --update` and stream output. Report success or failure with the command's exit code.

Tripwires:

- Update mode never modifies project-owned `.beislid/workflow.md`.
- Do not infer the install repo from skill symlinks; the manifest `repo` field is authoritative.
- Do not add `--force` unless the user explicitly asks for it in the same update request.

## 1. Precheck git repo

Run `git rev-parse --show-toplevel`. If it errors or returns non-zero, hard-fail with prose:

```
🛑 Setup needs a git repo with at least one commit. Run `git init` and make
the first commit, then re-run /setup.
```

Also check `git rev-list --max-parents=0 HEAD` exits 0 (at least one commit). Same hard-fail otherwise.

## 2. Detect mode

Check `<git-toplevel>/.beislid/workflow.md`:

- **Missing** → first-run flow (sections 3–10 below).
- **Exists** → menu mode (section 11).

## 3. First-run: targeted inspection

Run cheap-signal commands once at the top, before asking anything:

```bash
git remote get-url origin                              # → host + owner/repo
gh auth status 2>&1                                    # → is gh CLI logged in?
git log -50 --pretty=%s                                # → grep for ID patterns
git for-each-ref refs/heads --format='%(refname:short)' --sort=-committerdate \
  | head -20                                           # → branch_pattern candidates
```

Parse `git remote` for host (`github.com` / `gitlab.com` / etc.) and `owner/repo`. Parse `gh auth status` for the auth state on github hosts. Grep commit subjects for `[A-Z]{2,4}-\d+` (Linear/Jira shape) and `^#?\d+` (GitHub/Azure numeric shape). Hold these results in memory for the interview prompts.

## 4. First-run: ticket_source interview

Use the inspection results to suggest a default. One suggestion at a time, single Y/n confirmation; never silent fill.

**If host is github.com + gh authed + numeric IDs detected in commits:**

```
🔍 Detected GitHub Issues with `gh` CLI (numeric IDs in recent commits).
Use `type: cli, command: 'gh issue view {id} --json title,body,labels'`?
[Y/n/different]
```

On `Y`: capture `id_pattern: '^#?\d+$'` and `link_template: 'https://github.com/<owner>/<repo>/issues/{id}'` (deterministic from `git remote`).

**If Linear-shaped IDs detected (`[A-Z]+-\d+`):**

Try MCP discovery via `probe-semantics.md` (search for tools matching `*linear*` or `*issue*`). On match:

```
🔍 Linear-shaped IDs in recent commits + Linear MCP tool detected
(`<tool-name>`). Use this for ticket fetching? [Y/n/different]
```

On `Y`: capture `type: mcp, tool: <tool-name>, id_pattern: '^[A-Z]+-\d+$'`. Ask once for the workspace name to populate `link_template: 'https://linear.app/<workspace>/issue/{id}'`.

If MCP discovery returns no Linear-shaped tools: do NOT ask the user to type an MCP tool name. Pivot:

```
💭 Linear-shaped IDs detected but no Linear MCP tool is available in this
host. Pick an alternative:
  (a) cli — give me the command for fetching tickets
  (b) paste — I'll ask for the title at every PR handoff
```

**If no detectable signal:** ask `(mcp / cli / file / paste)` directly. For `mcp`: list available MCP tools via `probe-semantics.md` and ask to pick one. For `cli`: ask for the command (must contain `{id}` placeholder). For `file`: ask for the file glob. For `paste`: no further input.

In every branch, capture `id_pattern` (auto-derived from the dominant grep pattern) and `link_template` for known hosts (deterministic). Never ask the user to type an MCP tool name.

## 5. First-run: branch_pattern interview

Test these 8 candidate regexes against the last 20 branches. Sort by coverage (number of branches that match).

```
1. ^[a-z]+/([a-z]+-\d+)       — case-mismatched (normalize via id_pattern)
2. ^[a-z]+/([A-Z]+-\d+)       — Jira with type prefix
3. ^([A-Z]+-\d+)              — Jira/Linear direct uppercase
4. ^([a-z]+-\d+)              — direct lowercase
5. ^(\d+)-                    — github/azure numbered with description
6. ^[a-z]+/(\d+)              — feature/123 (Azure DevOps, GitHub)
7. ^[a-z]+/[a-z]+/(\d+)       — Azure DevOps users/<name>/12345
8. ^[a-z]+-(\d+)              — gh-123 style
```

Suggest the highest-coverage candidate with stats:

```
🔍 Branch pattern `^[a-z]+/([a-z]+-\d+)` matches 18 of 20 recent branches.
Use it? [Y/n/skip]
```

If best coverage <60%: don't suggest a pattern. Ask:

```
💭 No regex covers most recent branches. Skip branch_pattern? Ready-for-review will
ask for the ticket ID at every run. [Y/n]
```

On `n`: ask for the regex directly. On `Y` (skip): capture nothing for branch_pattern.

## 6. First-run: pr_base interview

Probe order:

1. If host is github.com + gh authed: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.
2. Else: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'`.
3. Else: `main`.

If the result is `main`: silent default — don't ask. If the result is anything else, confirm:

```
🔍 Default branch detected: `<branch>`. Use as pr_base? [Y/n]
```

On `n`: ask the user for the branch name.

## 7. First-run: compose minimum workflow.md

Compose in memory:

- Version stamp `<!-- beislid-workflow: v1 -->` (line 1).
- Project name comment from `basename $(git rev-parse --show-toplevel)`.
- `## Issue tracker` section with the captured `ticket_source` and (if present) `branch_pattern` blocks.
- `## PR target` section with `pr_base.default` (only if non-`main`).
- `## Probe cache` section with `ttl_hours: 24`.

No commented-out templates. Only sections the user filled in.

## 8. Show preview

Print the composed workflow.md to the user. Wait for explicit approval:

```
📋 Preview of `.beislid/workflow.md`:

<composed contents>

Write this to `<git-toplevel>/.beislid/workflow.md`? [Y/n]
```

On `n`: cancel without writing. On `Y`: continue to step 9.

## 9. Write workflow.md and insert AGENTS.md block

Run `mkdir -p <git-toplevel>/.beislid/` then write the file. Print:

```
📝 Wrote .beislid/workflow.md
```

Then run the AGENTS.md block insertion (section 12 below).

After writing the minimum, offer the menu mode (section 11 — same UI as re-run) for adding optional sections.

## 10. First-run wrap-up

Print one nudge to run `/doctor`:

```
💭 Next: run /doctor to verify the config and warm the probe cache.
```

## 11. Menu mode

When `.beislid/workflow.md` already exists, parse it (using the grammar in `workflow-md-format.md`). If parsing fails, jump to **section 13: parse-error recovery**. Otherwise present:

```
📋 Found .beislid/workflow.md. What would you like to do?

  (1) Add a section
  (2) Change a configured section
  (3) Remove a configured section
  (4) Reset and regenerate from scratch
  (5) I'm done
```

**On (1) Add a section:** present a sub-menu of optional sections that aren't yet configured. Each item shows a one-line "when this fires" hint (plain English, not phase-numbered):

- **Scopes & quality gates** — *Run lint/test commands across the repo, scopes, or changed-file-aware gate sets. Simple gates need only name+command; rich gates may add stage, cost, timeout, selectors, output parser, and failure policy.*
- **Explore skill** — *Let kickoff Step 2 run a project skill as an exploration enhancer or replacement before design.*
- **Model routing** — *Declare preferred or required host model candidates per Beislið skill, with fallback/blocking disclosure.*
- **Translation sync** — *Run a translation-sync skill during quality gates whenever paths under your trigger globs are touched.*
- **Browser compatibility** — *Run an advisory browser compatibility skill during quality gates whenever paths under your trigger globs are touched. Doesn't block PR handoff.*
- **Domain capture** — *After kickoff or PR handoff, ask a domain expert to record findings into a knowledge store. Kickoff can use a subagent or, when the host has no subagent mechanism, an installed skill with the same name. Both the expert name and the store path are required.*
- **PR description formatter** — *Pass drafted PR descriptions through a formatter skill before showing them for approval.*
- **Guided walkthrough thresholds** — *Offer an interactive walkthrough before review when the diff exceeds N files or N lines. Defaults are 5 files / 200 lines.*
- **Clean evaluator** — *Run PR-readiness gates in a clean worktree or container, or skip that path by policy; artifacts and logs stay with the run.*
- **Visual surfaces** — *Configure optional Lavish visual-surface routing; repo config is required before workflows proactively suggest, prompt, or auto-open surfaces.*
- **Workflow signals** — *Configure optional local workflow-state signals, starting with tmux-glance tab markers for semantically instrumented skills.*
- **Babysit** — *Configure `/babysit` goal budget, review-response/gate loop behavior, and optional merge/memento/retro closeout automation.*
- **Fresh-eyes final review** — *Keep the built-in final whole-diff pass, replace it with a command, or explicitly disable it by project policy.*
- **Ticket updates** — *Post kickoff plans and review-response QA replies back to the ticket tracker; optionally create child tickets for out-of-scope feedback.*
- **Planning artifacts** — *Write approved structure/spec/design Markdown files through lifecycle actions, with prompt or safe auto-create behavior.*
- **Lifecycle actions** — *Run configured side effects at Beislið workflow events, such as assigning or moving a ticket when kickoff starts.*
- **PR review source / replies** — *Let review-response read PR review comments and either post clear-fix replies or print manual reply instructions.*
- **PR host override** — *Override owner/repo/remote only when git remote derivation is wrong, such as forks or non-origin upstreams.*

Walk the chosen section's sub-interview (asking one Y/N or value at a time). Compose the section block in memory. Insert at the canonical position in the file (canonical order is the order in `workflow-md-format.md` § Section grammar). Show diff (`git diff --no-index <old> <new>` formatted prose). Ask `Write? [Y/n]`. On `Y`: write atomically (whole-file rewrite via Read → mutate → Write).

**On (2) Change a configured section:** show currently filled sections only. Walk that section's sub-interview pre-filled with current values; user accepts or overrides each value. Show diff; confirm; write.

**On (3) Remove a configured section:** show currently filled sections only. On selection, check section-dependency rules and prompt for auto-clean:

- Removing `scopes` while `split_policy` is set → "Removing scopes will also remove `split_policy` (it has no meaning without scopes). Proceed? [Y/n]"
- Removing `domain_expert.agent` while `knowledge_store.path` is set → "Also remove `knowledge_store.path`? [Y/n]" (default Y; if n, leaves the half-pair)
- Removing `knowledge_store.path` while `domain_expert.agent` is set → mirror
- Removing `pr_review_source` while `pr_review_update` is set → warn that update can only be used after pasted PR feedback; ask whether to remove update too (default Y)
- Removing `pr_review_update` while `pr_review_source` is set → allowed; review-response will print PR reply/re-request instructions manually

Show diff; confirm; write.

**On (4) Reset and regenerate from scratch:**

1. Copy current file to `<git-toplevel>/.beislid/workflow.md.bak`. Print: `📝 Saved current config to .beislid/workflow.md.bak`.
2. Run the full first-run interview (sections 3–8) in memory.
3. Show full diff of the regenerated file vs the original.
4. Ask `Write? [Y/n]`.
5. On `Y`: write atomically.

**On (5) I'm done:** exit cleanly with no writes.

## 11a. Optional-section interviews added in Phase 3

### Scopes & quality gates

Configure one gate model: changed-file-aware `gate_sets`, scoped `scopes`, or top-level `gates`. Prefer `gate_sets` when the user wants reusable named checks, selector explanations, staged/rich gates by changed path, or multiple touched areas that union checks deterministically. Keep `scopes` and top-level `gates` backward-compatible.

For each simple gate ask: gate name, command, optional autofix command, and whether it is independent/read-only enough for `parallel_safe: true`. Explain that flat gates remain valid and default to `stage: pre-pr`, `kind: sensor`, `execution: computational`, and `mutates: false`.

If the user chooses rich metadata, collect only fields they can answer confidently:

- `stage`: one of `preflight`, `per-edit`, `pre-commit`, `pre-pr`, `post-pr`, `continuous`, `human-interrupt`; default `pre-pr`
- `kind`: default `sensor`
- `execution`: `computational`, `inferential`, or `human`; default `computational`
- `timeout_seconds`, `cost`, `mutates`, `accepts_files`, `required_tools`
- changed-file selector globs under `changed_file_selector.include` / `exclude`
- `output.parser` and `output.agent_summary`
- `failure.retryable`, `failure.max_fix_iterations`, `failure.stop_if_patterns`, and `failure.hint`

For `gate_sets`, collect named sets first (set name, optional cwd, gates), then ordered selectors (selector name, path globs, optional exclude globs, referenced set names). Explain that multiple matching selectors union gate sets deterministically and orchestrators should report selected/skipped reasons.

Warn that P0 `ready-for-review` and `review-response` run legacy/pre-pr command gates. Other stages are valid metadata for Rondo/future orchestrators and should not be presented as active blockers in today's PR handoff flows.

Example rich gate:

```beislid:gates
- name: full-tests
  stage: pre-pr
  kind: sensor
  execution: computational
  command: '.venv/bin/python -m pytest'
  timeout_seconds: 600
  cost: expensive
  mutates: false
  output:
    parser: pytest
  failure:
    retryable: true
    max_fix_iterations: 1
```

### Explore skill

Configure the canonical `explore` block under the `Kickoff` / skill-specific overrides section.

Ask:

```
Configure kickoff explore skill? (enhance / replace / skip)
```

For `enhance` or `replace`, ask for the skill name. Explain that `enhance` keeps default codebase exploration and merges skill findings; `replace` uses the skill instead and falls back to default exploration only after a runtime prompt if the skill fails.

```beislid:explore
skill: <skill-name>
mode: enhance
```

### Model routing

Configure the canonical `model_routing` block under `Model routing` or `Skill-specific overrides`. Explain that this is a host-adapter hint/enforcement contract: hosts honor it only when model selection is supported, report the routing status, and block only for `mode: require` when no candidate can be honored.

Ask for an optional default route, then ordered skill overrides. For each route collect:

- skills list (overrides only), using Beislið skill names such as `spec`, `blueprint`, `implement`, `review`, `fresh-eyes`, `ready-for-review`, and `review-response`
- model candidates as an ordered list; `model` may be written only as shorthand for a single candidate, otherwise write `models`
- mode: `prefer` or `require`, default `prefer`

Prefer portable aliases (`opus`, `sonnet`, `haiku`, `default`, `host-default`), but allow namespaced provider strings as escape hatches. Do not collect `when:` conditions in v1; say conditional routing is reserved for later workflow support and should not be written as active config.

```beislid:model_routing
defaults:
  models: [sonnet]
  mode: prefer
overrides:
  - skills: [spec, blueprint, poke-holes]
    models: [opus, openai:gpt-5.5]
    mode: require
```

If the repo also ships a `WORKFLOW.md` Rondo profile, keep its `step_hints` adapter in sync with the same tier table: kickoff initial spawn should route stronger than the broad default, ideally `heavy`/`frontier`; ordinary implementation should stay on `standard`; ready-for-review gate execution can stay `light` or `standard`; and review/fresh-eyes synthesis should escalate to `heavy`. `when:` remains reserved there as well.

Never create duplicate `beislid:model_routing` blocks; update or remove the existing one.

### Visual surfaces

Configure the canonical `beislid:visual_surfaces` block under `Visual surfaces`. Explain that repo config is required for proactive visual routing; user-level plugin enablement alone is not enough. The only v1 provider is `lavish-axi`, and doctor validates config shape without deep-invoking Lavish. Explain that `artifact_retention` affects supplemental `.lavish/` HTML only; `local` is the safe ignored default, `discard` removes wrappers after use, and `preserve-repo` requires explicit publication intent plus a gitignore exception.

Ask:

```text
Configure visual surfaces? (off / suggest / prompt / auto / skip)
```

For any mode except `skip`, ask whether to use the default Lavish command/artifact root/retention or override them. Defaults are `npx -y lavish-axi`, `.lavish`, and `local`. If retention is overridden, prompt explicitly for `local`, `discard`, or `preserve-repo`. Ask for optional per-workflow mode overrides only when the user wants them; valid override values are `off / suggest / prompt / auto`.

```beislid:visual_surfaces
provider: lavish-axi
mode: prompt
command: 'npx -y lavish-axi'
artifact_root: .lavish
artifact_retention: local
workflows:
  spec: prompt
  blueprint: suggest
```

Never create duplicate `beislid:visual_surfaces` blocks; update or remove the existing one.

### Workflow signals

Configure the canonical `beislid:workflow_signals` block under `Workflow signals`. Explain that this is local workflow-state fan-out, not tracker updates, host lifecycle hooks, or quality gates. The only v1 executable sink is `tmux-glance`; future sink types are reserved.

Ask:

```text
Configure workflow signals? (auto / off / skip)
```

For `auto`, write a `sinks` list with `type: tmux-glance`. Ask whether to enable the default semantically instrumented skills (`ready-for-review` and `poke-holes`) or customize per-skill overrides. Valid modes are `off / auto`.

```beislid:workflow_signals
mode: auto
sinks:
  - type: tmux-glance
skills:
  ready-for-review: auto
  poke-holes: auto
```

Explain that signal emission is best-effort: outside tmux, without `tmux-glance`, or when a sink fails, Beislið continues silently. Never create duplicate `beislid:workflow_signals` blocks; update or remove the existing one.

### Babysit

Configure the canonical `beislid:babysit` block under `Babysit` or `Skill-specific overrides`. Explain that `/babysit` requires `/goal`; this config only controls the goal budget, PR loop behavior, and closeout automation.

Ask whether to configure a goal token budget or leave it unlimited. Accept values such as `50k`, `100000`, or `1m`; omit the field when unlimited.

Ask for loop behavior:

```text
Use review-response for actionable feedback? (Y/n)
Run configured gates before babysit-owned pushes? (Y/n)
Wait interval seconds? [60]
Timeout minutes? [none]
```

Ask for closeout modes:

```text
Merge after green? (off / ask / auto)
Merge method? (repo-default / squash / merge / rebase)
Delete branch after merge? (y/N)
Run memento capture after closeout? (off / ask / auto)
Run retro after closeout? (off / ask / auto)
Apply accepted retro findings? (off / ask / auto)
```

Explain that `auto` removes routine babysit prompts only when action policy allows the side effect. If policy asks, the skill asks; if policy denies, it stops.

```beislid:babysit
goal:
  token_budget: 50k
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 60
  timeout_minutes: 60
closeout:
  merge:
    mode: ask
    method: squash
    delete_branch: true
  memento:
    mode: ask
  retro:
    mode: ask
    apply_findings: ask
```

Never create duplicate `beislid:babysit` blocks; update or remove the existing one.

### Clean evaluator

Configure the canonical `clean_eval` block under `Ready-for-review` or `Skill-specific overrides`. Explain that `mode: require` runs configured pre-PR gates in a clean worktree/container and that `mode: off` keeps the normal working-tree gate path. The clean surface may be created locally or supplied by the host; artifacts and logs stay under the configured root or run-ledger clean-eval artifacts.

Ask:

```text
Configure clean evaluator? (off / require)
```

For `require`, ask for the preferred surface and artifact root:

```text
Preferred clean surface? (auto / worktree / container)
```

Default to `auto` and explain that it accepts either a received clean surface or a fresh one created for evaluation. Then ask for an optional artifact root, defaulting to `.beislid/clean-eval`. Write:

```beislid:clean_eval
mode: require
surface: auto
artifact_root: .beislid/clean-eval
```

For `off`, remove any existing `clean_eval` block.

Never create duplicate `beislid:clean_eval` blocks; update or remove the existing one.

### Fresh-eyes final review

Configure the canonical `fresh_eyes` block under `Ready-for-review` or `Skill-specific overrides`. Explain this affects only the final whole-diff `fresh-eyes` pass; the primary `review` pass still runs.

Ask:

```text
Configure final fresh-eyes behavior? (built-in / command / disable)
```

For `built-in`, remove any existing `fresh_eyes` block. For `command`, ask for the command; it must be a repo-root command whose exit status signals blocking findings. Write:

```beislid:fresh_eyes
type: command
command: '<user command>'
```

For `disable`, ask for a short reason and write:

```beislid:fresh_eyes
enabled: false
reason: '<reason>'
```

Never create duplicate `beislid:fresh_eyes` blocks; update or remove the existing one.

### Ticket updates

Configure the canonical `ticket_update` block. This is shared by kickoff and review-response: kickoff uses only the comment channel to post the approved implementation plan; review-response uses the comment channel for QA/ticket replies and the issue channel for out-of-scope child tickets.

Ask for one mode:

```
Configure ticket updates? (mcp / cli / skip)
```

For `mcp`, ask for `comment_tool` first and `issue_tool` second. The issue tool is optional; if omitted, review-response prints child-ticket drafts manually.

```beislid:ticket_update
type: mcp
comment_tool: mcp__linear__save_comment
issue_tool: mcp__linear__save_issue
```

For `cli`, ask for `comment_command` first and `issue_command` second. Commands must use temp-file placeholders so user-authored text is never interpolated into the shell: `{id}` and `{body_file}` for comments; `{title_file}` and `{body_file}` for issues. If the user proposes `{body}` or `{title}`, explain the injection/quoting risk and ask for a file-based command instead.

```beislid:ticket_update
type: cli
comment_command: '... {id} ... {body_file} ...'
issue_command: '... {title_file} ... {body_file} ...'
```

### Planning artifacts

Configure approved structure/spec/design files as `type: artifact` actions inside the canonical `lifecycle_actions` block. This is a preset over lifecycle actions, not a separate fenced key. Also mention that checkpoint artifacts use the same `lifecycle_actions` block but are configured separately for different workflow events such as `kickoff_context_ready` and `implementation_plan_created`.

Ask:

```text
Configure user-approved planning artifacts? (structure / spec / blueprint / any combination / skip)
```

Use `structure` for `break_spec_approved`.

For each selected event, ask whether to use the default path or customize it. Defaults are `plans/{feature}-structure.md` for `break_spec_approved`, `plans/{feature}-spec.md` for `spec_approved`, and `plans/{feature}-design.md` for `blueprint_approved`. Custom paths must be relative `.md` file templates, must not contain `..`, and may only use `{feature}`, `{kind}`, and `{ticket_id}`. Then ask:

```text
Ask each time, or auto-create when missing? (prompt / auto)
```

Default to `prompt`. Explain that `auto` creates a missing artifact without another prompt after approval, but never overwrites an existing file; existing targets still ask overwrite / choose another path / skip.

If a `lifecycle_actions` block already exists, merge these events/actions into that block; never create a duplicate `beislid:lifecycle_actions` block. Preserve existing events/actions. If an artifact action already exists under `break_spec_approved`, `spec_approved`, or `blueprint_approved`, offer keep / replace / add another, default keep. Show the diff before writing.

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
  blueprint_approved:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        path: 'plans/{feature}-design.md'
```

### Checkpoint artifacts

When the user asks for clear-context, Rondo-style, or checkpoint workflow support, configure checkpoint artifact actions inside the canonical `lifecycle_actions` block. Explain that this is a lightweight workflow option, not the durable run ledger: skills write human-readable Markdown checkpoints and update `.beislid/checkpoints/latest.json` for rediscovery, but do not create run IDs, event history, gate logs, or automatic resume state.

P0 executable checkpoint events are `kickoff_context_ready` and `implementation_plan_created`. Reserved events `review_feedback_loaded` and `ready_for_review_pre_submit` may be kept as workflow intent but no P0 skill executes them yet. For each selected executable event, ask whether to use the default path or customize it. Defaults are `checkpoints/{event}-{ticket_id}.md` when ticket context is known, otherwise `checkpoints/{event}-{feature}.md`. Custom paths must be relative `.md` file templates, must not contain `..`, and may only use `{event}`, `{feature}`, `{kind}`, and `{ticket_id}`. Then ask:

```text
Ask each time, or auto-create when missing? (prompt / auto)
```

Default to `prompt`. Explain that `auto` creates a missing checkpoint without another prompt, but never overwrites an existing file; existing targets still ask overwrite / choose another path / skip. If a `lifecycle_actions` block already exists, merge checkpoint events into that block and preserve existing events/actions. Never create duplicate `beislid:lifecycle_actions` blocks.

```beislid:lifecycle_actions
events:
  kickoff_context_ready:
    actions:
      - name: write-kickoff-context-checkpoint
        type: artifact
        approval: prompt
        path: 'checkpoints/{event}-{ticket_id}.md'
  implementation_plan_created:
    actions:
      - name: write-implementation-plan-checkpoint
        type: artifact
        approval: prompt
        path: 'checkpoints/{event}-{ticket_id}.md'
```

### Lifecycle actions

Configure the canonical `lifecycle_actions` block. Explain that lifecycle actions are side effects at workflow events, not quality gates. P0 setup supports ordered CLI actions for `kickoff_start`, artifact actions for `break_spec_approved`, `spec_approved`, and `blueprint_approved` through the Planning artifacts preset, and checkpoint artifact actions through the Checkpoint artifacts preset. This interview configures kickoff CLI actions; use the presets for planning/checkpoint artifacts.

Ask:

```text
Configure kickoff_start lifecycle actions? (cli / skip)
```

For `cli`, collect one or more ordered actions. For each action ask: action name, command, and approval (`auto` / `prompt`). Commands may use `{ticket_id}`, `{id}`, `{branch}`, and `{event}` placeholders; explain that orchestrators argv-pass or shell-quote placeholder values before execution. Explain that `auto` runs once configured and prompts only on failure; `prompt` asks before running. If the command includes raw user-authored body/title placeholders, redirect the user to `ticket_update` or a future file-based lifecycle action instead.

If a `lifecycle_actions` block already exists, merge kickoff actions into the existing block and preserve all existing events/actions, including planning and checkpoint artifact actions. Never create duplicate `beislid:lifecycle_actions` blocks.

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: assign-ticket
        type: cli
        command: 'gh issue edit {id} --add-assignee @me'
        approval: auto
```

### PR review source / replies

If `git remote get-url origin` parses as GitHub and `gh auth status` passes, suggest GitHub CLI defaults:

```
Use GitHub CLI to read PR reviews and post clear-fix replies? (Y / manual replies / n)
```

On `Y`, write both blocks:

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

On `manual replies`, write the same `pr_review_source` and this update block:

```beislid:pr_review_update
type: manual
```

On `n`, or when the repo is not GitHub/authed, ask for source mode: `cli / paste / skip`.

For source `cli`, ask for `summary_command` first. It may use `{owner}`, `{repo}`, `{number}`, and `{url}` placeholders; if it uses any of those, setup should remind the user that review-response will derive or ask for the values at runtime. Then ask for optional `threads_command` for inline review comments. Write:

```beislid:pr_review_source
type: cli
summary_command: '<user command>'
# Include threads_command only when the user supplies one.
threads_command: '<user command>'
```

For source `paste`, write an explicit manual source:

```beislid:pr_review_source
type: paste
```

If a source is configured, ask for update mode: `cli / manual / skip`.

For update `cli`, ask for `reply_command` first and require a `{json_file}` placeholder. The command may also use `{owner}`, `{repo}`, and `{number}`. Then ask for optional `rerequest_command`; if supplied, it must also use `{json_file}`. Write:

```beislid:pr_review_update
type: cli
reply_command: '<user command with {json_file}>'
# Include rerequest_command only when the user supplies one.
rerequest_command: '<user command with {json_file}>'
```

For update `manual`, write `type: manual`; `skip` leaves update absent and review-response prints manual instructions.

### PR host override

Configure `pr_host.*` only when the derived remote is wrong. Ask for owner and repo; ask for remote only if it is not `origin`.

```beislid:pr_host.owner
my-org
```

```beislid:pr_host.repo
my-repo
```

```beislid:pr_host.remote
upstream
```

`pr_host` is pure address/config data. Setup does not probe it.

## 12. AGENTS.md block insertion

The block content is fixed:

```markdown
## Agent skills

This repo uses [Beislið](https://github.com/sandsower/beislid) for orchestrator skills.

- Project config: `.beislid/workflow.md`
- Audit setup: `/doctor`
- Configure: `/setup`
```

Insertion logic:

- If `<git-toplevel>/AGENTS.md` exists:
  - Look for an existing `## Agent skills` heading. If found, replace the content between that heading and the next `##` (or EOF) — keep the heading position where it is.
  - If no existing heading, append the block at end of file.
- If `AGENTS.md` does not exist:
  - Create it with just the block.
  - Even if `CLAUDE.md` exists, do NOT modify it.

Print:

```
📝 <added|updated> ## Agent skills section in <AGENTS.md path>
```

## 13. Parse-error recovery in menu mode

If `.beislid/workflow.md` exists but doesn't parse cleanly per `workflow-md-format.md` grammar, run the same line-numbered diagnosis doctor uses:

```bash
grep -n '^```beislid:' <repo>/.beislid/workflow.md
```

Compute the line number of the failing block, surface it in prose:

```
🛑 Workflow.md has a parse error.

⚠️ The `beislid:<key>` block at line <N> doesn't parse: <yaml error>.

✓ The other configured sections (<list>) parsed cleanly.

What now?
  (a) Reset and regenerate from scratch — saves current file to
      `.beislid/workflow.md.bak` first.
  (b) Cancel — exit setup, fix workflow.md by hand or run /doctor for more
      detail.
```

On `(a)`: run section 11 option (4) (Reset). On `(b)`: exit cleanly.

Don't offer Add / Change / Remove on a partially parseable file — they're unsafe without a clean parse of every section.

## Common mistakes

- **Asking the user to type an MCP tool name** — never. Use `probe-semantics.md` MCP discovery; if discovery returns nothing, pivot to `cli`/`paste`.
- **Suggesting a branch_pattern below the 60% coverage threshold** — never. Below threshold, ask whether to skip.
- **Writing without showing a diff first** — every destructive write shows a diff and asks for `[Y/n]`.
- **Modifying CLAUDE.md** — never. AGENTS.md is the always-preferred target.
- **Refusing to run when workflow.md exists** — superseded; menu mode handles re-runs (Q17 amended in Phase 2).
- **Writing commented-out template sections** — superseded; the file contains only filled-in sections. Discovery happens via the menu, not via reading commented prose.
- **Touching the probe cache** — setup never reads or writes the cache. That's doctor's responsibility (and orchestrators write back individual entries on re-probe). Setup only writes workflow.md and AGENTS.md.

## Key principles

- **Setup is the canonical config interface.** Every workflow.md change goes through it (or through direct edit, which is a quiet escape hatch).
- **Never silently overwrites.** Every destructive write shows a diff and waits for explicit `[Y/n]` confirmation.
- **Atomic whole-section writes.** Setup never partially mutates a fenced block; it rewrites the whole section.
- **Targeted detection, never silent fill.** Every auto-suggested value is presented for explicit Y/n/different confirmation.
- **One question at a time.** Don't batch prompts; the user answers in order.
