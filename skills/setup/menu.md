# setup menu v1

In verbose mode, emit `✓ setup/menu v1 loaded` immediately after reading this file.

## 11. Menu mode

When `.beislid/workflow.md` already exists, parse it (using the grammar in `workflow-md-format.md`).
If parsing fails, jump to [parse-error recovery](parse-recovery.md).
Otherwise present:

```text
📋 Found .beislid/workflow.md. What would you like to do?

  (1) Add a section
  (2) Change a configured section
  (3) Remove a configured section
  (4) Reset and regenerate from scratch
  (5) I'm done
```

**On (1) Add a section:** present a sub-menu of optional sections that aren't yet configured.
Each item shows a one-line "when this fires" hint (plain English, not phase-numbered):

- **Scopes & quality gates** - *Run lint/test commands across the repo, scopes, or changed-file-aware gate sets.
  Simple gates need only name+command; rich gates may add stage, cost, timeout, selectors, output parser, and failure policy.*
- **Explore skill** - *Let kickoff Step 2 run a project skill as an exploration enhancer or replacement before design.*
- **Model routing** - *Declare preferred or required host model candidates per Beislið skill, with fallback/blocking disclosure.*
- **Agent isolation** - *Configure top-level workspace transition, mutating-delegate placement, durable manual roots, preparation, and atomic runtime profiles.*
- **Translation sync** - *Run a translation-sync skill during quality gates whenever paths under your trigger globs are touched.*
- **Browser compatibility** - *Run an advisory browser compatibility skill during quality gates whenever paths under your trigger globs are touched.
  Doesn't block PR handoff.*
- **Domain capture** - *After kickoff or PR handoff, ask a domain expert to record findings into a knowledge store.
  Kickoff can use a subagent or, when the host has no subagent mechanism, an installed skill with the same name.
  Both the expert name and the store path are required.*
- **PR description formatter** - *Pass drafted PR descriptions through a formatter skill before showing them for approval.*
- **Guided walkthrough thresholds** - *Offer an interactive walkthrough before review when the diff exceeds N files or N lines.
  Defaults are 5 files / 200 lines.*
- **Clean evaluator** - *Run PR-readiness gates in a clean worktree or container, or skip that path by policy; artifacts and logs stay with the run.*
- **Visual surfaces** - *Configure optional Lavish visual-surface routing; repo config is required before workflows proactively suggest, prompt, or auto-open surfaces.*
- **Workflow signals** - *Configure optional local workflow-state signals, starting with tmux-glance tab markers for semantically instrumented skills.*
- **Babysit** - *Configure `/babysit` goal budget, review-response/gate loop behavior, and optional merge/memento/retro/cleanup closeout automation.*
- **Fresh-eyes final review** - *Keep the built-in final whole-diff pass, replace it with a command, or explicitly disable it by project policy.*
- **Ticket updates** - *Post kickoff plans and review-response QA replies back to the ticket tracker; optionally create child tickets for out-of-scope feedback.*
- **Planning artifacts** - *Write approved structure/spec/design Markdown files through lifecycle actions, with prompt or safe auto-create behavior.*
- **Ship-time artifacts** - *Choose how ready-for-review narrates approved planning artifacts during PR handoff.*
- **Checkpoint artifacts** - *Configure reserved checkpoint artifact metadata for future execution and reporting flows.*
- **Lifecycle actions** - *Run configured side effects at Beislið workflow events, such as assigning or moving a ticket when kickoff starts.*
- **Lifecycle hooks** - *Run configured hook actions at Beislið phase boundaries under the normal action policy.*
- **PR review source / replies** - *Let review-response read PR review comments and either post clear-fix replies or print manual reply instructions.*
- **Review feedback profiles** - *Attach agent-ready prompt formats to matching review or QA feedback sources.*
- **PR host override** - *Override owner/repo/remote only when git remote derivation is wrong, such as forks or non-origin upstreams.*

Walk the chosen section's sub-interview (asking one Y/N or value at a time).
Compose the section block in memory.
Insert at the canonical position in the file (canonical order is the order in `workflow-md-format.md` § Section grammar).
Show diff (`git diff --no-index <old> <new>` formatted prose).
Ask `Write? [Y/n]`.
On `Y`: write atomically (whole-file rewrite via Read → mutate → Write), then print the next-steps report from [write and report](write-and-report.md).

**On (2) Change a configured section:** show currently filled sections only.
Walk that section's sub-interview pre-filled with current values; user accepts or overrides each value.
Show diff; confirm; write, then print the next-steps report from [write and report](write-and-report.md).

**On (3) Remove a configured section:** show currently filled sections only.
On selection, check section-dependency rules and prompt for auto-clean:

- Removing `scopes` while `split_policy` is set → "Removing scopes will also remove `split_policy` (it has no meaning without scopes).
  Proceed? [Y/n]"
- Removing `domain_expert.agent` while `knowledge_store.path` is set → "Also remove `knowledge_store.path`? [Y/n]" (default Y; if n, leaves the half-pair)
- Removing `knowledge_store.path` while `domain_expert.agent` is set → mirror
- Removing `pr_review_source` while `pr_review_update` is set → warn that update can only be used after pasted PR feedback; ask whether to remove update too (default Y)
- Removing `pr_review_update` while `pr_review_source` is set → allowed; review-response will print PR reply/re-request instructions manually

Show diff; confirm; write, then print the next-steps report from [write and report](write-and-report.md).

**On (4) Reset and regenerate from scratch:**

1. Copy current file to `<git-toplevel>/.beislid/workflow.md.bak`.
  Print: `📝 Saved current config to .beislid/workflow.md.bak`.
2. Run the full first-run interview ([first run](first-run.md)) in memory.
3. Show full diff of the regenerated file vs the original.
4. Ask `Write? [Y/n]`.
5. On `Y`: write atomically, then print the next-steps report from [write and report](write-and-report.md).

**On (5) I'm done:** exit cleanly with no writes.

## Just-in-time section routes

After the user selects or directly requests a section, load only its protocol:

- [Scopes and quality gates](sections/scopes-quality-gates.md)
- [Explore](sections/explore.md)
- [Model routing](sections/model-routing.md)
- [Visual surfaces](sections/visual-surfaces.md)
- [Workflow signals](sections/workflow-signals.md)
- [Babysit](sections/babysit.md)
- [Agent isolation](sections/agent-isolation.md)
- [Translation sync](sections/translation-sync.md)
- [Browser compatibility](sections/browser-compatibility.md)
- [Domain capture](sections/domain-capture.md)
- [PR description formatter](sections/pr-description-formatter.md)
- [Guided walkthrough](sections/guided-walkthrough.md)
- [Clean evaluator](sections/clean-evaluator.md)
- [Fresh-eyes](sections/fresh-eyes.md)
- [Ship-time artifacts](sections/ship-time-artifacts.md)
- [Ticket updates](sections/ticket-updates.md)
- [Planning artifacts](sections/planning-artifacts.md)
- [Checkpoint artifacts](sections/checkpoint-artifacts.md)
- [Lifecycle actions](sections/lifecycle-actions.md)
- [Lifecycle hooks](sections/lifecycle-hooks.md)
- [PR review source and replies](sections/pr-review.md)
- [Review feedback profiles](sections/review-feedback-profiles.md)
- [PR host override](sections/pr-host.md)

Do not preload unselected section protocols.
Return to this menu after a completed section write when the user wants another change.
