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

   This creates or updates `<repo>/.beislid/workflow.md` and can add an agent-instructions block to `AGENTS.md`. If you are introducing Beislið to a team, follow the [team rollout guide](./team-rollout.md) for the minimum viable config, strictness layers, and PR checklist.

   To update the installed Beislið distribution later, run:

   ```text
   /setup update
   ```

   Or run `beislid update` / `~/Projects/beislid/install.sh --update` from a shell. Use `brew upgrade beislid` instead if you installed via Homebrew; `beislid update` is for source-checkout installs and fast-forwards the checkout, aborts on local changes, preserves prior install targets and opt-ins, and relinks skills.

### Bootstrap a repo

Fresh sessions should read `.beislid/workflow.md` first, then route by repo state:

```markdown
## Agent skills

This repo uses [Beislið](https://github.com/sandsower/beislid) for orchestrator skills.

- Read `.beislid/workflow.md` first.
- Existing ticket or branch → `kickoff`
- Clear requirements, implementation still undecided → `blueprint`
- Work is done but not yet proven → `verify`
- Branch is ready for PR → `ready-for-review`
- Use direct skill invocation when the right entry point is already obvious.
- Run `/setup` when the repo workflow config is missing or needs updating.

- Project config: `.beislid/workflow.md`
- Audit setup: `/doctor`
- Configure: `/setup`
```

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
   | An open PR needs babysitting through CI/review | `babysit` |

Basic planning, debugging, verification, and review skills work after install. For isolated agent work, see [Worktree isolation](./worktree-isolation.md). Repo-aware orchestrators such as `kickoff`, `ready-for-review`, `review-response`, and `babysit` need project setup when they must read tickets, run configured gates, or interact with PR review sources. Lifecycle artifact templates for specs, designs, plans, verification, review, ship summaries, and feedback logs live in [`.beislid/artifact-templates.md`](../.beislid/artifact-templates.md); local/chat records are the default, with terse ticket/PR summaries unless configured otherwise. `babysit` also requires `/goal`: Claude includes it; Pi users need the `pi-goal` package enabled. For compact Work Contract examples and copyable setup templates, see [Work Contract examples](./work-contract-examples.md) and [Setup templates](./setup-templates.md).

## Invocation

Invocation syntax depends on the host.

- Use the short skill name when your host supports direct invocation: `spec`, `blueprint`, `ready-for-review`.
- Use slash syntax when your host exposes skills that way: `/spec`, `/blueprint`, `/ready-for-review`.
- Use namespaced syntax when your host requires it: `/skill:spec`, `/skill:blueprint`.
- Natural-language triggers work in some agents, but direct invocation is safest when a gate matters.

The installed names are short and unprefixed: `spec`, `blueprint`, `verify`, `ready-for-review`, and so on.

### Pi managed commands

When Beislið is installed as a Pi package, it includes a Pi extension with managed command wrappers for the Beislið skill surface. Commands such as `/kickoff`, `/implement`, and `/verify` route to the portable skills while letting Pi handle host-specific behavior. For `show-me`, the command names are split when both extensions are enabled: `/show-me` stays with the deck-builder extension and `/show-me-skill` routes to the portable skill wrapper.

For boundary workflows, the Pi extension can automatically start a fresh session from a readable checkpoint pointer and auto-continue with a pointer-only prompt. Configure repo intent with `beislid:pi_handoff` in `.beislid/workflow.md`; project-local `.pi/beislid.json` settings override user-global `~/.pi/agent/beislid.json` settings as the final override. Claude and other hosts keep the existing manual checkpoint guidance.

## CLI

The CLI wraps user-level install, project install, status, and update:

```bash
beislid install user [--strict]
beislid install project [path] [--copy] [--strict]
beislid status
beislid status project [path]
beislid plugin enable lavish [--command COMMAND] [--artifact-root PATH]
beislid plugin disable lavish
beislid plugin status lavish [--check]
beislid workflow-signal status
beislid workflow-signal emit waiting --skill ready-for-review
beislid visual-feedback normalize [feedback-file]
beislid update
beislid help
```

`install.sh --project [path]` is compatibility sugar for `beislid install project [path]`; add `--copy` there too for copied project skills. Add `--strict` when you want installs to exit nonzero on skipped or conflicted expected artifacts. Project install creates `.agents/skills`, `.claude/skills`, and `.codex/skills` under the target project. Symlink mode is the default. Copy mode writes `.beislid-owner.json` markers inside copied skill dirs and records copy ownership in `.beislid/project-install.json`, so reruns refresh only Beislið-owned copies. `beislid status project [path]` reports missing skills per host and exits non-zero when any supported host is incomplete. Project installs print a suggested managed `.gitignore` block by default; add `--write-gitignore` to create or replace it. It warns if `.beislid/workflow.md` is missing but does not create it; use `setup` for project workflow config.

A Homebrew formula lives at `packaging/homebrew/beislid.rb` for Homebrew installs. It packages the runtime subset under `libexec`, including `.beislid/`, and exposes `beislid` on PATH. Use `brew upgrade beislid` to update a Homebrew install; use `beislid update` / `install.sh --update` for a source checkout. Maintainers update the formula here and publish the tap/release so `brew upgrade` picks up the new runtime.

### Optional Lavish visual surfaces

Lavish visual surfaces are optional and supplemental. Beislið's Markdown/chat spec, design, review, and approval artifacts remain canonical even when a local HTML surface is used.

Fresh-reader path:

1. Enable or inspect local plugin state:

   ```bash
   beislid plugin enable lavish
   beislid plugin status lavish
   ```

2. If your environment should avoid the default `npx -y lavish-axi` fetch path, pin a local command instead:

   ```bash
   beislid plugin enable lavish --command '/opt/tools/lavish-axi' --artifact-root .lavish
   ```

3. Add repo routing only when you want a workflow to suggest, prompt for, or auto-open supplemental surfaces. Configure `beislid:visual_surfaces` in `.beislid/workflow.md`; user-level plugin state alone does not activate routing. For planning workflows, `blueprint` and `poke-holes` use visual surfaces conservatively: only when a plan, comparison, diagram, decision tree, or typed input control materially improves understanding.

4. Run `/doctor` to validate the repo config shape. Doctor and normal `plugin status` do not deep-invoke Lavish. Use `beislid plugin status lavish --check` only when you deliberately want to run the configured command and accept possible npm/network/cache activity.

Fallbacks are safe by default: disabled plugin state, absent or disabled repo config, missing `npx` or another configured binary, failed deep checks, runtime failures, a declined visual prompt, unknown typed action, malformed payload, or freeform-only feedback all fall back to the normal Markdown/chat workflow gate. For `show-me`, Lavish routing happens only after the portable deck renders; `.lavish/show-me/` wrappers are supplemental, governed by `artifact_retention`, and ignored unless explicit workflow intent opts into publication with a gitignore exception. Typed `BEISLID_VISUAL_FEEDBACK_V1` gate feedback is separate from freeform annotations and must be copied into the canonical Markdown/chat record before it affects routing; visual choices require a `selected_option` and never bypass explicit spec/blueprint approval gates. See [Configuration: Visual surfaces](./configuration.md#visual-surfaces) for troubleshooting details and the Beislið/Lavish ownership boundary.

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

Use `ready-for-review` when the branch is ready for review. New PRs run configured gates, optional clean-eval gates, local review, the configured final check, push, and PR creation. Small safe diffs may use fast-path: preloaded protocol files, parallel safe gates, and combined review/final-check. Existing PR updates take a faster path: gates, push, and report the PR URL.

### Feedback came back

```text
review-response → debug if needed → fix → verify → push or reply
```

Use `review-response` after someone reviews or QA-tests your work. It categorizes feedback, helps fix or push back with evidence, then follows the configured update path.

### AFK execution with envelopes

```text
/envelope <ticket-or-spec> → intake → author → approve → export → rondo run-once --manifest <slice-manifest>
```

Use `kickoff` when you'll implement interactively in the same session. Use `/envelope` when approved slices should run away-from-keyboard later: it authors, approves, and exports `execution-envelope-v0` slices as a validated, repo-committed bundle under `.beislid/exports/` that an external runner executes in a fresh session. Invoke it explicitly in a strong-model session, e.g. `/envelope BEI-123`; `kickoff` may suggest it for AFK-suitable multi-slice work but never auto-routes into it. The export bundle contract is documented in [Configuration](./configuration.md) under "Export bundles (`.beislid/exports/`)".

### Babysit an open PR

```text
babysit → review-response loop → configured gates → green PR or configured closeout
```

Use `babysit` when an open PR needs a goal-backed loop that keeps checking CI, review comments, mergeability, and configured closeout policy. It requires `/goal`; Claude has `/goal` built in, while Pi needs the `pi-goal` package enabled.

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
- [Team rollout](./team-rollout.md): minimum viable repo config, strictness layers, and `AGENTS.md` rollout block.
- [Review workflows](./review-workflows.md): `review`, `fresh-eyes`, `rinse`, `pr-patrol`, `walk-the-diff`, `review-response`, `babysit`, and `ready-for-review` review behavior.
- [FAQ](./faq.md): positioning, Superpowers/GSD comparisons, autonomy, team use, and workflow philosophy.
- [Show Me](./show-me.md): local HTML evidence and explanation decks.
- [Credential guard](./credential-guard.md): optional Claude Code hook for blocking secret-dumping commands.
