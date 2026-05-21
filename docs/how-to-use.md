# How to use Beislið

Beislið is repo-local. It installs portable skills, but the skills are only the interface. The product is the workflow: shared gates, project config, verification evidence, review loops, and human approval points that travel with the repo.

## 60-second start

1. **Install Beislið**:

   ```bash
   git clone git@github.com:sandsower/beislid.git ~/Projects/beislid
   ~/Projects/beislid/install.sh
   ```

   This links skills into supported host directories and links the `beislid` CLI at `${BEISLID_BIN_DIR:-~/.local/bin}/beislid`. If the installer warns that the bin dir is not on `PATH`, add it to your shell profile or run `~/Projects/beislid/bin/beislid` directly.

2. **Open a project repo** where you want agents to follow a shared workflow.

3. **Configure repo-aware workflows** when you want ticket, PR, quality-gate, or team-specific behavior:

   ```text
   /setup
   ```

   This creates or updates `<repo>/.beislid/workflow.md` and can add an agent-instructions block to `AGENTS.md`.

   To update the installed Beislið distribution later, run:

   ```text
   /setup update
   ```

   Or run `beislid update` / `~/Projects/beislid/install.sh --update` from a shell. Update fast-forwards the Beislið checkout, aborts on local changes, preserves prior install targets and opt-ins, and relinks skills.

4. **Audit the setup** before relying on it:

   ```text
   /doctor
   ```

5. **Start from the right entry point:**

   | I have                                        | Start with   |
   | --------------------------------------------- | ------------ |
   | Vague idea or unclear product behavior        | `spec`       |
   | Existing ticket or branch                     | `kickoff`    |
   | Clear requirements but unknown implementation | `blueprint`  |
   | A bug, failing test, or unexpected behavior   | `debug`      |
   | A bunch of work done but not yet proven       | `verify`     |
   | A branch that is ready for PR                 | `ready-for-review`    |
   | PR review or QA feedback came back            | `review-response` |

Basic planning, debugging, verification, and review skills work after install. Repo-aware orchestrators such as `kickoff`, `ready-for-review`, and `review-response` need project setup when they must read tickets, run configured gates, or interact with PR review sources.

## Invocation

Invocation syntax depends on the host.

- Use the short skill name when your host supports direct invocation: `spec`, `blueprint`, `ready-for-review`.
- Use slash syntax when your host exposes skills that way: `/spec`, `/blueprint`, `/ready-for-review`.
- Use namespaced syntax when your host requires it: `/skill:spec`, `/skill:blueprint`.
- Natural-language triggers work in some agents, but direct invocation is safest when a gate matters.

The installed names are short and unprefixed: `spec`, `blueprint`, `verify`, `ready-for-review`, and so on.

## CLI

The CLI wraps user-level install, project install, status, and update:

```bash
beislid install user
beislid install project [path]
beislid install project [path] --copy
beislid status
beislid status project [path]
beislid update
beislid help
```

`install.sh --project [path]` is compatibility sugar for `beislid install project [path]`; add `--copy` there too for copied project skills. Project install creates `.agents/skills`, `.claude/skills`, and `.codex/skills` under the target project. Symlink mode is the default. Copy mode writes `.beislid-owner.json` markers inside copied skill dirs and records copy ownership in `.beislid/project-install.json`, so reruns refresh only Beislið-owned copies. Project installs print a suggested managed `.gitignore` block by default; add `--write-gitignore` to create or replace it. It warns if `.beislid/workflow.md` is missing but does not create it; use `setup` for project workflow config.

A draft Homebrew formula lives at `packaging/homebrew/beislid.rb` for packaging validation. It is not the published install path yet; full Homebrew support is tracked in #67. Packaged layouts should include the Beislið runtime subset and can set `BEISLID_HOME` if `bin/beislid` is separated from that runtime root.

## Common paths

### Vague idea to PR

```text
spec → poke-holes when broad/unfocused → blueprint → implement → verify → review → fresh-eyes → ready-for-review
```

Use this when the desired product behavior is not clear yet. `spec` shapes the work first. Use `poke-holes` when the spec is still broad, unfocused, or needs detail refinement before `blueprint` designs the implementation.

### Ticket to implementation plan

```text
kickoff → spec or break-spec or blueprint → implement
```

Use this when a branch or ticket already exists. `kickoff` reads `<repo>/.beislid/workflow.md`, fetches ticket context when configured, explores the repo using default or configured explore-skill behavior, then routes to the right next step.

### Bug fix

```text
debug → fix → verify → review or ready-for-review
```

Use `debug` before proposing fixes. Root cause first. Guessing is rejected.

### Ready for review

```text
verify → ready-for-review
```

Use `ready-for-review` when the branch is ready for review. New PRs run configured gates, local review, the configured final check, push, and PR creation. Small safe diffs may use fast-path: preloaded protocol files, parallel safe gates, and combined review/final-check. Existing PR updates take a faster path: gates, push, and report the PR URL.

### Feedback came back

```text
review-response → debug if needed → fix → verify → push or reply
```

Use `review-response` after someone reviews or QA-tests your work. It categorizes feedback, helps fix or push back with evidence, then follows the configured update path.

**Note:** These are only some of the recommended workflows, each skill is composable and orchestrator skills like `ready-for-review` enforce rules but you can also call the smaller skills individually as needed.

## What Beislið will and won't do

Beislið will:

- Ask for product clarity before implementation design.
- Require an approved approach before code for substantial changes.
- Push agents toward TDD and file-level implementation plans.
- Require fresh verification before done/fixed/passing claims.
- Separate side-effect-free review from flows that edit, push, post, or create PRs.
- Use repo-local config for ticket, gate, review, and PR handoff behavior.

Beislið won't:

- Replace CI, tests, maintainers, or human review.
- Make agents fully autonomous by default.
- Silently push, post comments, create PRs, or accept review risk without approval gates.
- Guess your team's workflow when `.beislid/workflow.md` is missing.
- Guarantee correctness without evidence.

## Where to go from here

- [Workflows](./workflows.md): detailed lifecycle diagrams and routing rules.
- [Skills](./skills.md): full skill catalog.
- [Configuration](./configuration.md): `setup`, `doctor`, `.beislid/workflow.md`, scopes, gates, and probe cache.
- [Review workflows](./review-workflows.md): `review`, `fresh-eyes`, `rinse`, `pr-patrol`, `walk-the-diff`, `review-response`, and `ready-for-review` review behavior.
- [FAQ](./faq.md): positioning, Superpowers/GSD comparisons, autonomy, team use, and workflow philosophy.
- [Show Me](./show-me.md): local HTML evidence and explanation decks.
- [Credential guard](./credential-guard.md): optional Claude Code hook for blocking secret-dumping commands.
