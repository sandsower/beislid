<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/beislid/beislid-mark-dark.svg">
    <img src="docs/assets/beislid/beislid-mark.svg" alt="Beislið mark" width="128" height="128">
  </picture>
</p>

<h1 align="center">Beislið</h1>

<p align="center">
  <a href="https://github.com/sandsower/beislid/actions/workflows/validate.yml"><img alt="validate" src="https://img.shields.io/github/actions/workflow/status/sandsower/beislid/validate.yml?branch=main&label=validate"></a>
  <a href="./LICENSE"><img alt="license" src="https://img.shields.io/github/license/sandsower/beislid"></a>
  <img alt="skills" src="https://img.shields.io/badge/skills-23-22d3ee">
  <img alt="hosts" src="https://img.shields.io/badge/hosts-Claude%20%7C%20Pi%20%7C%20Codex-a78bfa">
  <img alt="status" src="https://img.shields.io/badge/status-v0.2.0-f59e0b">
</p>

<p align="center">
  <b>A human-centric, extensible framework for collaborating with coding agents.</b><br>
  Make agents follow the same ticket, verification, review, and PR handoff process your team expects.
</p>

<p align="center">
  <a href="#install">Install</a>
  · <a href="./docs/how-to-use.md">How to use</a>
  · <a href="./docs/faq.md">FAQ</a>
  · <a href="#philosophy">Philosophy</a>
</p>

---

## v0.2 migration for existing installs

Beislið v0.2 starts from a clean repository history. If you installed v0.1.x, do a one-time migration from a fresh v0.2 checkout instead of `git pull`:

```bash
mv ~/Projects/beislid ~/Projects/beislid-pre-v0.2-archive
git clone git@github.com:sandsower/beislid.git ~/Projects/beislid
~/Projects/beislid/install.sh --migrate-v0.2
```

The migration reads the previous install manifest, removes only old Beislið symlinks that point into the previous checkout, preserves install targets and opt-ins, and reinstalls from the new checkout. It never deletes the old checkout or clobbers regular files.

New installs can skip this and use the normal install below.

## What this is

Beislið (/ˈpeislɪð/, "BASE-tlith", Icelandic for "the harness") is a workflow harness for coding agents.

It installs portable Markdown skills, but the skills act only as the interface. The product is the lifecycle: shared gates, repo-local config, verification evidence, review loops, and human-in-the-loop checkpoints.

```text
spec → blueprint → implement → verify → review → ready-for-review
```

Project workflow lives in `.beislid/workflow.md`, so a repo can declare its own ticket sources, branch patterns, quality gates, PR review sources, and PR handoff rules.

## Who it is for

Beislið is for developers and teams who want agent-assisted work to be disciplined and reviewable:

- Senior developers who want a repeatable personal workflow instead of one-off prompting.
- Tech leads and staff engineers who want agents in a repo to follow shared team process.
- Teams that need explicit gates before code, claims, review risk, pushes, comments, or PR creation.

It is not a fully autonomous coding mode, a replacement for CI, or a replacement for human review.

## Why it feels different

| Step                    | What it prevents                                               |
| ----------------------- | -------------------------------------------------------------- |
| `spec` / `kickoff`      | building the wrong thing from vague requirements               |
| `blueprint`             | coding before the approach is named and approved               |
| `implement`             | wandering through a large change without a file-level plan     |
| `verify`                | claiming done before fresh evidence exists                     |
| `review` / `fresh-eyes` | handing off with obvious local findings, drift, or stale docs     |
| `ready-for-review`               | opening a PR before gates, review, and release notes are ready |

## 60-second start

Install Beislið:

```bash
git clone git@github.com:sandsower/beislid.git ~/Projects/beislid
~/Projects/beislid/install.sh
```

The installer also links the `beislid` CLI into `${BEISLID_BIN_DIR:-~/.local/bin}`. If that directory is not on `PATH`, add it or run the checkout's `bin/beislid` directly.

Then open a project repo and pick the right entry point:

| Situation                                 | Start with   |
| ----------------------------------------- | ------------ |
| Vague idea or unclear product behavior    | `spec`       |
| Existing ticket or branch                 | `kickoff`    |
| Clear requirement, unknown implementation | `blueprint`  |
| Bug, failing test, or unexpected behavior | `debug`      |
| Work is done but not proven               | `verify`     |
| Branch is ready for PR                    | `ready-for-review`    |
| PR review or QA feedback came back        | `review-response` |
| Open PR needs babysitting through CI/review | `babysit` |

For repo-aware ticket, PR, and quality-gate workflows, configure the project first:

```text
setup → doctor → kickoff or ready-for-review
```

Basic skills work after install. Repo-aware orchestrators such as `kickoff`, `ready-for-review`, `review-response`, and `babysit` need `.beislid/workflow.md` when they must read tickets, run configured gates, or interact with PR review sources. `babysit` also requires host goal support: Claude includes `/goal`; Pi users need the `pi-goal` package enabled.

See [How to use](./docs/how-to-use.md) for more information.

## Repo-local workflow

Beislið keeps project policy in the repo:

```text
<repo>/.beislid/workflow.md
```

Use `setup` to create or update it. Use `doctor` to audit it and probe configured capabilities.

A workflow can define:

- issue tracker source and branch pattern
- PR target and review source
- ticket or PR update commands
- scopes and quality gates
- PR babysitting and optional closeout automation
- triggered checks such as translation sync or browser compatibility
- guided walkthrough thresholds

See [Configuration](./docs/configuration.md) for details and [workflow.md format](./.beislid/workflow-md-format.md) for the full grammar.

## Core workflows

- **Shape work:** `spec`, `break-spec`, `blueprint`, `poke-holes`
- **Execute safely:** `implement`, `debug`, `handoff`
- **Check evidence:** `verify`, `review`, `fresh-eyes`, `rinse`, `show-me`
- **Deliver work:** `ready-for-review`, `review-response`, `babysit`, `pr-patrol`, `walk-the-diff`
- **Manage config:** `setup`, `doctor`, `retro`

See [Skills](./docs/skills.md) for the full catalog and [Workflows](./docs/workflows.md) for lifecycle diagrams.

## Install

```bash
git clone git@github.com:sandsower/beislid.git ~/Projects/beislid
~/Projects/beislid/install.sh
```

Symlinks land in:

- `~/.agents/skills/<name>`
- `~/.claude/skills/<name>`
- `~/.codex/skills/<name>`
- `${BEISLID_BIN_DIR:-~/.local/bin}/beislid`

Edit the repo to edit the skills. When Beislið probes for a named project skill, repo-local `.beislid/skills/<name>` takes priority, then `$BEISLID_SKILLS_DIRS`, then the global host skill dirs above.

CLI commands available now:

```bash
beislid install user
beislid install project [path]
beislid status
beislid status project [path]
beislid workflow-signal status
beislid workflow-signal emit waiting --skill ready-for-review
beislid update
beislid migrate v0.2
beislid help
```

Project install defaults to symlink mode. Use `beislid install project [path] --copy` when the project needs portable local copies instead. With no path, `beislid install project` targets the git root when run inside a git repo; outside git it targets the current directory and warns. An explicit path is used exactly, even when it sits inside a larger repo. The installer creates all three project-local host dirs:

- `<project>/.agents/skills`
- `<project>/.claude/skills`
- `<project>/.codex/skills`

It writes `<project>/.beislid/project-install.json` and warns softly when `<project>/.beislid/workflow.md` is missing. Copy mode also writes `.beislid-owner.json` inside each copied skill dir so reruns can refresh only Beislið-owned copies. Unmarked project files or skill dirs are never clobbered, even with `--force`. Project installs print a suggested `.gitignore` block by default; pass `--write-gitignore` to create or replace the managed block idempotently. It does not create workflow config; run the `setup` skill when repo-aware workflows need it.

Update an existing install from an agent host:

```text
/setup update
```

Or from the Beislið checkout / CLI:

```bash
~/Projects/beislid/install.sh --update
beislid update
```

Update fast-forwards the checkout with `git pull --ff-only`, aborts if the checkout has uncommitted local changes, preserves prior manifest install targets and opt-ins such as security hooks, then relinks skills/hooks as needed.

For the v0.1.x → v0.2 history reset only, use the migration command from a fresh v0.2 checkout:

```bash
~/Projects/beislid/install.sh --migrate-v0.2
# or, once the v0.2 CLI is on PATH:
beislid migrate v0.2
```


Flags:

- `--with-security-hooks`: enable `credential_guard` for Claude Code
- `--update`: fast-forward the Beislið checkout and re-run install
- `--migrate-v0.2`: one-time migration from pre-v0.2 installs after cloning the clean v0.2 history
- `--status`: print installed commit and symlink status
- `--project [path]`: compatibility sugar for a project install via `install.sh`
- `--copy`: copy project-local skills instead of symlinking them
- `--write-gitignore`: create or replace the managed project `.gitignore` block
- `--force`: repoint/replace existing symlinks. Never clobbers unmarked regular files or directories.

Machine state for user installs lives at `${BEISLID_STATE_DIR:-~/.local/state/beislid}/install.json` and records the CLI path when the CLI link is installed or already correct. Durable run-ledger state lives under `${BEISLID_STATE_DIR:-~/.local/state/beislid}/runs/<flow>/<repo_hash>/<run_id>/` and can be managed with `beislid run-ledger ...` for Rondo-style runs, gate logs, interruptions, and final reports. Project install state lives at `<project>/.beislid/project-install.json`. Re-running is safe: dangling symlinks are auto-repaired; symlinks pointing at another live target are left alone unless you pass `--force`. Regular files are never clobbered. Update never touches project-owned `.beislid/workflow.md` files.

### Homebrew packaging draft

This repo includes a draft formula at `packaging/homebrew/beislid.rb`. It is for packaging validation and future tap work, not the published install path yet. Full Homebrew support, including publishing and upgrade policy, is tracked separately in the Homebrew packaging work.

The CLI is package-layout friendly: it resolves its runtime from the real `bin/beislid` path, or from `BEISLID_HOME` when a packaged wrapper points at a separate runtime root. If the runtime subset is incomplete, it prints a layout error instead of failing with a shell source error.

## Invocation

Invocation syntax depends on the host.

- Use the short skill name when your host supports direct invocation: `spec`, `blueprint`, `ready-for-review`.
- Use slash syntax when your host exposes skills that way: `/spec`, `/blueprint`, `/ready-for-review`.
- Use namespaced syntax when your host requires it: `/skill:spec`, `/skill:blueprint`.
- Natural-language triggers work in some agents, but direct invocation is safest when a gate matters.

When installed as a Pi package, Beislið includes a Pi extension that registers managed slash-command wrappers for the skill surface. Boundary workflows can automatically start a fresh Pi session from a readable checkpoint pointer and continue with a pointer-only prompt. Repo intent is configured with `beislid:pi_handoff`; local Pi settings are the final override. Claude and other hosts keep the existing manual checkpoint guidance.

## Docs

- [How to use](./docs/how-to-use.md): first-run guide and common paths.
- [Workflows](./docs/workflows.md): lifecycle diagrams and routing rules.
- [Skills](./docs/skills.md): full skill catalog.
- [Configuration](./docs/configuration.md): `setup`, `doctor`, `.beislid/workflow.md`, scopes, gates, and probe cache.
- [Review workflows](./docs/review-workflows.md): review primitives and review/PR handoff/feedback flows.
- [FAQ](./docs/faq.md): positioning, comparisons, autonomy, team use, and philosophy.
- [Show Me](./docs/show-me.md): local HTML evidence and explanation decks.
- [Credential guard](./docs/credential-guard.md): optional Claude Code hook for blocking secret-dumping commands.

## Optional integrations

- `credential_guard` hook: blocks bash commands that dump secrets. Claude Code-specific; the skills themselves are portable markdown.
- Beislið Pi extension: managed slash-command wrappers for Beislið skills plus automatic fresh-session handoff from checkpoint pointers when configured.
- `workflow_signals`: optional local workflow-state fan-out; v1 can drive `tmux-glance` tab markers through `beislid workflow-signal` when configured.

## Philosophy

1. Shape unclear product work before implementation design.
2. Design before code. No implementation until the approach is named and approved.
3. Evidence before claims. No "should work" or "probably fixes". Run it, verify, then submit it for review.
4. Root cause before fix. Guessing is rejected. Understand the bug before proposing a patch.
5. Keep the human in the loop. Agents can do the work, but people own product direction, risk, review, and release.

## Credits

Several Beislið skills draw from Matt Pocock's [`mattpocock/skills`](https://github.com/mattpocock/skills), especially:

- `poke-holes`, based on Matt's `grill-me` (renamed to disambiguate from elicitation; in Beislið it pressure-tests an existing plan or design rather than extracting requirements from scratch).
- `spec` / `break-spec`, which overlap with Matt's `to-prd` and `to-issues`.
- `implement`, which shares the test-first / vertical-slice philosophy of Matt's `tdd`.

Beislið diverges by keeping skills agent-agnostic, installing under short unprefixed names, using a local installer/manifest, and organizing the workflow around repo-local project configuration.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT
