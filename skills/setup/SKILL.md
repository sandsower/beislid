---
name: setup
description: Configure Beislið project config (`.beislid/workflow.md`) interactively, or update an installed Beislið distribution. Use when the user says "setup", "/setup", "setup update", "/setup update", "update beislid", "configure beislid", "set up workflow", "add scopes", "change ticket source", "reconfigure beislid", or any intent to add, change, or remove a workflow.md section. Walks through sections conversationally; shows a diff before any destructive write.
---

# Setup

In verbose mode, emit `✓ setup/router v1 loaded` immediately after reading this file.

Initialize or update Beislið's per-project config at `<repo>/.beislid/workflow.md`, or run the distribution updater for update intent.
Setup is the canonical config interface.
Direct file editing remains a quiet escape hatch.

## Resource resolution

Resolve canonical resources only when the selected route needs them.
When the Beislið CLI is available, run `beislid resource resolve workflow-md-format` for workflow grammar and `beislid resource resolve probe-semantics` for capability discovery, then read the returned absolute file.
If the command is unavailable or fails, read the exact sibling resource `workflow-md-format.md` or `probe-semantics.md` shipped with this skill and disclose the fallback.
Never search the repository, home directory, `.agents`, `.claude`, `.codex`, or another skill root for a replacement.

## Route

1. For `setup update`, `/setup update`, `update beislid`, or equivalent update intent, load [update](update.md) only.
Do not inspect or modify project config in that route.
2. Otherwise apply the repository precheck and mode detection below.
3. If `.beislid/workflow.md` is absent, load [first run](first-run.md).
Before preview or write, load [write and report](write-and-report.md).
After a confirmed first-run write, load [AGENTS integration](agents-integration.md), then offer [menu mode](menu.md).
4. If `.beislid/workflow.md` exists and parses cleanly, load [menu mode](menu.md).
Load [write and report](write-and-report.md) only when a preview or write boundary is reached.
5. If existing config does not parse cleanly, load [parse recovery](parse-recovery.md) and do not load menu section protocols.

Do not preload update, first-run, menu, write, AGENTS, parse-recovery, or optional-section resources before their route is selected.

## 1. Precheck git repo

Run `git rev-parse --show-toplevel`.
If it errors or returns non-zero, hard-fail with prose:

```
🛑 Setup needs a git repo with at least one commit. Run `git init` and make
the first commit, then re-run /setup.
```

Also check `git rev-list --max-parents=0 HEAD` exits 0 (at least one commit).
Same hard-fail otherwise.

## 2. Detect mode

Check `<git-toplevel>/.beislid/workflow.md`:

- **Missing** -> load [first run](first-run.md), then [write and report](write-and-report.md) at its preview boundary.
- **Exists** -> load [menu mode](menu.md).

## Common mistakes

- **Asking the user to type an MCP tool name** - never.
  Use `probe-semantics.md` MCP discovery; if discovery returns nothing, pivot to `cli`/`paste`.
- **Suggesting a branch_pattern below the 60% coverage threshold** - never.
  Below threshold, ask whether to skip.
- **Writing without showing a diff first** - every destructive write shows a diff and asks for `[Y/n]`.
- **Modifying CLAUDE.md** - never.
  AGENTS.md is the always-preferred target.
- **Refusing to run when workflow.md exists** - superseded; menu mode handles re-runs (Q17 amended in Phase 2).
- **Writing commented-out template sections** - superseded; the file contains only filled-in sections.
  Discovery happens via the menu, not via reading commented prose.
- **Touching the probe cache** - setup never reads or writes the cache.
  That's doctor's responsibility (and orchestrators write back individual entries on re-probe).
  Setup only writes workflow.md and AGENTS.md.

## Key principles

- **Setup is the canonical config interface.** Every workflow.md change goes through it (or through direct edit, which is a quiet escape hatch).
- **Never silently overwrites.** Every destructive write shows a diff and waits for explicit `[Y/n]` confirmation.
- **Atomic whole-section writes.** Setup never partially mutates a fenced block; it rewrites the whole section.
- **Targeted detection, never silent fill.** Every auto-suggested value is presented for explicit Y/n/different confirmation.
- **One question at a time.** Don't batch prompts; the user answers in order.
