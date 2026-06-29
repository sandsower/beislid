# Contributing to Beislið

## Scope

Opinionated repo. The skills enforce discipline:

- Hard gates before risky operations
- Evidence-based claims
- Root-cause investigation over guesswork

PRs that soften enforcement will be closed. If you want different philosophy, fork.

## What to send

Welcome:

- Bug fixes, typos, clarifications
- Documentation improvements
- CI validation improvements

Open an issue first:

- New skills
- Changes to an existing skill's behavior
- Changes to install.sh

Don't bother:

- Removing hard gates
- Adding "skip" or "auto-continue" modes to gated skills
- Large refactors without prior discussion

## Skill proposal rubric

When proposing a new skill, answer:

1. What gate or discipline does this enforce? If it doesn't enforce anything, it probably doesn't belong here.
2. Why don't the existing skills cover this?
3. Is it generic, or does it embed project-specific details?
4. Which other skills does it compose with?

## No SLA

I maintain this when I have time. Issues may sit. PRs may sit. That's expected.

## Testing

Run the validation action locally before submitting:

```
./scripts/validate.sh  # checks frontmatter, resolves skill references, markdown lint
```

Behavioral testing is manual. See `docs/testing.md`.

## Auxiliary file convention (Pocock-style symlinks)

Some skills consume shared format-reference docs (probe semantics, workflow.md grammar, output templates). Masters live at `.beislid/<doc>.md` in this repo. Each consuming skill folder has a same-named symlink pointing at the master.

Eight master files today:

- `.beislid/workflow-md-format.md` — workflow.md grammar (consumed by `setup`, `doctor`, `ready-for-review`, `kickoff`, `review-response`)
- `.beislid/probe-semantics.md` — probe semantics for capability discovery (consumed by `setup`, `doctor`, `ready-for-review`, `kickoff`, `review-response`)
- `.beislid/output-templates.md` — shared output primitives: 12-emoji palette, three-clause failure shape, char-budget shape, verbose-stamps layout, inline-note placement (consumed by `doctor`, `ready-for-review`, `kickoff`, `review-response`)
- `.beislid/action-policy-protocol.md` — action-policy evaluation protocol: mode/class semantics, per-action overrides, sandbox baselines, secret-bearing heuristics, envelope shape (consumed by `kickoff`, `ready-for-review`, `review-response`, `babysit`, `implement`, `retro`)
- `.beislid/doctor-templates.md` — doctor-specific copy: audit success/failure templates, cache schema, doctor's verbose stamps (consumed by `doctor`)
- `.beislid/ready-for-review-templates.md` — ready-for-review-specific copy: orientation, per-phase one-liners, probe-failure prompt phrasings, PR success prose (consumed by `ready-for-review`)
- `.beislid/kickoff-templates.md` — kickoff-specific copy: orientation, step one-liners, strict paste fallback, ticket-update prompts, domain-pair notes (consumed by `kickoff`)
- `.beislid/review-response-templates.md` — review-response-specific copy: orientation, phase one-liners, feedback-mode prompts, PR review source/update notes, fast-path authorization, probe prompts (consumed by `review-response`)

Example symlinks:

```
skills/doctor/probe-semantics.md → ../../.beislid/probe-semantics.md
skills/doctor/workflow-md-format.md → ../../.beislid/workflow-md-format.md
skills/doctor/output-templates.md → ../../.beislid/output-templates.md
skills/doctor/doctor-templates.md → ../../.beislid/doctor-templates.md
skills/ready-for-review/ready-for-review-templates.md → ../../.beislid/ready-for-review-templates.md
skills/kickoff/kickoff-templates.md → ../../.beislid/kickoff-templates.md
skills/review-response/review-response-templates.md → ../../.beislid/review-response-templates.md
```

Editing the symlinked file in a skill folder transparently edits the master — that's the intended behavior. **Do not replace symlinks with regular files.** Some IDEs and `cp`/`mv` commands break symlinks silently; CI catches this in `validate.yml`, but a careful `git status` or `git ls-files -s` after edits is the surest local check (mode `120000` indicates a symlink, `100644` indicates a regular file).

If you legitimately need to add a new shared format doc, add it under `.beislid/`, symlink it into each consuming skill folder, and extend the symlink integrity check in `.github/workflows/validate.yml` to cover it. For guidance on writing your own skills that follow these conventions, see [Skill authoring guide](./docs/skill-authoring.md).

## Skill auxiliary protocol files

Skill-specific auxiliary protocol files are different from the shared docs above: they are regular files, not symlinks. `ready-for-review` uses `skills/ready-for-review/phase-*.md`, `kickoff` uses `skills/kickoff/step-*.md`, and `review-response` uses `skills/review-response/phase-*.md`. Entry `SKILL.md` files load them just in time at phase/step entry, so keep them focused and within the hard caps enforced by `scripts/check_skill_size_budgets.py`.
