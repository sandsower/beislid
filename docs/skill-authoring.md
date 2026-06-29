# Skill authoring guide

Beislið skills are portable Markdown files that encode agent discipline. Each skill enforces a specific gate: no design without approval, no fix without root cause, no done claim without fresh evidence.

This guide covers how to write a custom team skill that follows Beislið conventions. For the catalog of existing skills, see [Skills](./skills.md).

## Skill anatomy

A skill is a directory with at least a `SKILL.md` file:

```text
skills/<name>/
  SKILL.md          # required: the skill's instructions
```

Complex skills may add auxiliary protocol files:

```text
skills/<name>/
  SKILL.md          # entry point
  step-1-foo.md     # aux protocol loaded JIT at step entry
  step-2-bar.md
  templates.md      # output templates loaded by SKILL.md
```

The installed name is the directory name. Keep it short, unprefixed, and descriptive: `spec`, `verify`, `review`, `ready-for-review`.

## SKILL.md format

### Frontmatter

Every skill's `SKILL.md` starts with YAML frontmatter between `---` fences:

```yaml
---
name: my-skill-name
description: "When to use this skill. Be specific about triggers and boundaries."
---
```

**`name`**: the directory-name identifier. Must match the directory.

**`description`**: a one-line trigger and boundary statement. This is how agents and users discover when to use the skill. Be precise:

| Good | Bad |
|---|---|
| "Use when encountering any bug, test failure, or unexpected behavior. Requires root cause investigation before proposing fixes." | "Helps with debugging." |
| "Use before claiming work is complete, fixed, or passing. Requires running verification commands and reading output before making any success claims." | "Verification tool." |
| "Use when you have an approved design or requirements for a multi-step task, before writing code. Creates a file-level implementation plan with TDD as the default rhythm." | "Implementation helper." |

### Body

After frontmatter, the body is agent-readable Markdown. Every Beislið skill should include:

1. **A hard gate**: non-negotiable rule that the agent must follow.
2. **Phased or structured instructions**: clear steps, not open-ended prose.
3. **Exit conditions**: when the skill considers its work complete.

### Hard gates

Use the `<HARD-GATE>` element for non-negotiable constraints:

```markdown
<HARD-GATE>
Do NOT propose or implement a fix until you have identified the root cause with evidence. "It's probably X" is not a root cause.
</HARD-GATE>
```

Hard gates are what make Beislið skills different from generic prompting. They block the most common agent failure modes:

| Failure mode | Hard gate |
|---|---|
| Guessing fixes without understanding | "No fix without root cause" |
| Claiming done without testing | "Evidence before assertions" |
| Coding before design | "No implementation until approach is named and approved" |
| Auto-accepting review feedback | "Treat every actionable comment as blocking until fixed or explicitly pushed back" |

Write hard gates in direct, imperative language. Avoid hedging ("try to", "consider", "if possible"). The gate is not a suggestion.

### Structured instructions

Prefer phases or steps over unstructured prose:

```markdown
## Phases

### 1. Reproduce
- Read the error message carefully
- Reproduce the failure consistently

### 2. Investigate
- Check recent changes
- Trace the data flow

### 3. Hypothesize
- Form a single hypothesis
- Test it minimally
```

This is easier for agents to follow than paragraphs of advice. Numbered steps create a natural checkpoint rhythm.

### Exit conditions

Be clear about when the skill is done:

```markdown
## Exit
- Root cause identified with evidence → hand off to fix
- Cannot reproduce after three attempts → report and stop
```

## Side-effect boundaries

Beislið separates skills into two categories:

### Primitives (side-effect-free)

Primitives read files and produce findings. They never edit, commit, push, post, or create PRs.

```markdown
<HARD-GATE>
Do NOT edit, commit, push, post comments, or create PRs. This is a read-only skill. Report findings and let the caller decide what to do.
</HARD-GATE>
```

Examples: `review`, `fresh-eyes`, `verify` (verify runs commands but doesn't modify code).

### Orchestrators (controlled side effects)

Orchestrators may edit, push, or post — but only with approval gates and action-policy enforcement.

```markdown
<HARD-GATE>
- Run review findings through user approval before any code change.
- Post PR comments only after explicit per-comment approval.
- Never push, open a PR, merge, or approve without the configured action-policy result.
</HARD-GATE>
```

Examples: `ready-for-review`, `review-response`, `babysit`, `implement`.

When authoring a skill, decide which category it belongs to and enforce it with hard gates.

## Trigger clarity

The `description` field in frontmatter is the primary trigger. But skills should also include trigger rules in the body:

```markdown
## When to use this skill

Use when:
- A bug, failing test, or unexpected behavior appears
- You need to understand *why* before proposing a fix

Do NOT use when:
- You already know the fix and just need to apply it (use implement directly)
- The error is a known issue with a documented workaround
```

Clear trigger rules prevent the agent from reaching for the wrong skill.

## Verification expectations

Every skill that produces output should define how to verify it:

```markdown
## Verification

Before claiming this skill has done its work:

1. Run the test suite for the changed area
2. Confirm the fix addresses the root cause, not just the symptom
3. Verify no regression in related functionality
```

Skills that gate handoff points (`ready-for-review`, `verify`) should run verification commands themselves. Skills that produce artifacts (`spec`, `blueprint`) should define what "approved" means.

## Host portability

Beislið skills work across Claude, Codex, and Pi. To keep skills portable:

### Use markup, not platform features

```markdown
<!-- Good: generic markup -->
<HARD-GATE>
Do not edit files in this phase.
</HARD-GATE>

<!-- Bad: platform-specific -->
<claude:thinking>Don't edit files here</claude:thinking>
```

### Avoid host-specific commands

Use the skill name, not slash syntax. The installer handles host-specific invocation:

```markdown
<!-- Good -->
Run `spec` to shape requirements first.

<!-- Acceptable in docs -->
Use `/spec` (Claude/Codex) or `/skill:spec` (namespaced hosts).
```

### Use relative paths

Skills resolve paths relative to the repo root. Don't assume a specific checkout location:

```markdown
# Good
Read `<repo>/.beislid/workflow.md`

# Bad
Read `~/Projects/my-repo/.beislid/workflow.md`
```

### Probe capabilities lazily

Don't assume tools are available. Beislið skills use lazy capability probing: test for a tool only when it's about to be used, not in a preflight table.

### Shared format docs via symlinks

Skills that consume shared format-reference docs (probe semantics, output templates, lifecycle artifact templates, workflow.md grammar) use symlinks to `.beislid/<doc>.md` masters:

```text
skills/my-skill/workflow-md-format.md → ../../.beislid/workflow-md-format.md
skills/my-skill/artifact-templates.md → ../../.beislid/artifact-templates.md
```

Editing the symlinked file edits the master. Never replace symlinks with regular files — CI catches this in validation. Use `git ls-files -s` to verify: mode `120000` is a symlink, `100644` is a regular file.

Auxiliary protocol files that are skill-specific (e.g., `step-1-ticket.md`, `phase-2-review.md`) are regular files, not symlinks.

## Examples

### Minimal skill (standalone primitive)

`skills/check-migrations/SKILL.md`:

```markdown
---
name: check-migrations
description: "Use before merging database migration PRs. Verifies migrations are reversible and don't conflict."
---

# Check migrations

Verify database migrations before merge.

<HARD-GATE>
Do NOT approve or merge a migration PR until reversibility and conflict checks pass. Report findings; do not edit migration files.
</HARD-GATE>

## Steps

### 1. List pending migrations
Read all files matching `migrations/**/*.sql`. Identify the ones changed in this branch.

### 2. Check reversibility
For each migration, verify a corresponding down migration exists. If `up.sql` exists but `down.sql` does not, flag it.

### 3. Check conflicts
Scan for schema changes that conflict with other pending migrations on the target branch.

### 4. Report
Output findings as a severity-categorized list:
- **Blockers**: missing down migrations, schema conflicts
- **Warnings**: migrations without tests, large data changes

## Exit
Report complete. Do not edit files or approve PRs. Let the reviewer decide.
```

### Orchestrator skill (with aux files)

`skills/deploy-check/SKILL.md`:

```markdown
---
name: deploy-check
description: "Use before deploying to production. Checks deploy readiness, runs pre-deploy gates, and confirms rollback plan."
---

# Deploy readiness check

Verify the branch is safe to deploy.

<HARD-GATE>
- Do NOT trigger a deploy. This skill checks readiness only.
- Run pre-deploy gates before reporting readiness.
- If any blocker is found, stop and report. Do not suggest workarounds that skip gates.
</HARD-GATE>

## Phases

### 1. Pre-deploy gates
Load `pre-deploy-gates.md` and run each configured gate. Record results.

### 2. Diff review
Load `diff-review.md` and review the changes for deploy risk.

### 3. Rollback plan
Load `rollback-plan.md` and verify a rollback path exists.

## Exit
Report readiness verdict: ready / not ready / needs-human-decision.
```

`skills/deploy-check/pre-deploy-gates.md` (aux protocol, regular file):

```markdown
# Pre-deploy gate protocol

Load only when running the pre-deploy phase.

1. Run the test suite for the deploy target environment
2. Check monitoring dashboard for current incident status
3. Verify deploy window is open (not in a freeze period)
4. Confirm the target branch is the expected SHA
```

## Common mistakes

### Too vague triggers

```yaml
# Bad: agent won't know when to use this
description: "A useful skill for development tasks."

# Good: specific trigger and boundary
description: "Use before creating a PR that touches database migrations. Verifies reversibility and conflict-freedom."
```

### Gates that can be skipped

```markdown
# Bad: hedging language
<HARD-GATE>
Try not to edit files without approval. It's usually better to ask first.
</HARD-GATE>

# Good: imperative, non-negotiable
<HARD-GATE>
Do NOT edit files until the design is approved and the file-level plan is written.
</HARD-GATE>
```

### Mixing side effects into primitives

```markdown
# Bad: review skill that also fixes things
## Steps
1. Review the diff
2. Fix any issues found  ← side effect in a primitive!

# Good: review reports, caller decides
## Steps
1. Review the diff
2. Report findings with severity
3. Exit without editing files
```

### Platform assumptions

```markdown
# Bad: assumes Claude
Run `claude -p "review this PR"` to get a second opinion.

# Good: portable
Run the `review` skill to get findings. If your host doesn't support skill invocation, run `pr-patrol` instead.
```

### Too much in one skill

```markdown
# Bad: Swiss Army knife
This skill can review code, fix bugs, write tests, create PRs, and deploy.

# Good: single responsibility
This skill reviews code and produces findings. Use `implement` for fixes, `ready-for-review` for PRs.
```

## Testing your skill

### Manual verification

1. Install the skill by placing it in a host skill directory (or use `beislid install project` for repo-local skills).
2. Invoke it with the expected trigger phrase.
3. Verify the agent follows the hard gates and produces the expected output.
4. Test edge cases: what happens when the skill is invoked with no relevant changes? With conflicting context?

### Validation scripts

Beislið provides validation for installed skills:

```bash
python3 scripts/validate_skills.py
```

This checks frontmatter presence, `name`/`description` fields, SKILL.md existence, and symlink integrity. If your repo uses Beislið's own validation, add your custom skill paths to the appropriate gate set.

### Size budgets

Skills must stay within size limits so they fit in agent context:

```bash
python3 scripts/check_skill_size_budgets.py
```

Keep SKILL.md focused. Move reference material, examples, and detailed protocol steps into auxiliary files that load JIT.

## When to contribute upstream

The Beislið distribution welcomes contributions (see [CONTRIBUTING.md](../CONTRIBUTING.md)). Before proposing a new skill:

1. **What gate does it enforce?** If it doesn't enforce discipline, it probably doesn't belong.
2. **Is it generic?** Project-specific skills should live in your team's repo, not upstream.
3. **Does it compose?** Which existing skills does it work with?
4. **Open an issue first.** Don't send a PR without prior discussion for new skills or behavior changes.

Team-specific skills that embed project conventions, proprietary tooling, or internal workflow rules should live in your repo — that's exactly what Beislið's project-local install is for:

```bash
beislid install project
```
