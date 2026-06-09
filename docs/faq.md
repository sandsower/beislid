# Beislið FAQ

## What is Beislið?

Beislið is a repo-local workflow harness for teams using coding agents.

It installs portable skills, but the skills are only the interface. The product is the lifecycle: shared gates, project config, verification evidence, review loops, and human approval points.

## Is Beislið a skill pack or a workflow harness?

Both mechanically, but the important answer is workflow harness.

The installed artifacts are skills. The reason to use Beislið is that those skills compose into a shared repo workflow: clarify scope, design before code, plan implementation, verify with evidence, review locally, handle feedback, and move through the project's configured PR handoff process.

Skills are only the interface, the product is your own workflow codified.

## Who is Beislið for?

Mostly two groups:

- Senior developers who want disciplined agent collaboration without inventing a new prompt ritual every session.
- Tech leads or staff engineers who want agents working in a repo to follow the same delivery process.

It can work for solo projects, but the sharper value appears when a team wants shared expectations around agent-assisted work.

## Why use Beislið instead of Superpowers by Obra?

Superpowers is a fantastic project that gives agents a strong general methodology. What you get from Beislið is the ability to give your team a repo-local workflow contract.

Use Beislið when you want coding agents to follow the same ticket, review, verification, and PR handoff process your team expects from humans. Beislið is built around `.beislid/workflow.md`, configured quality gates, PR/ticket integrations, review boundaries, and explicit human approval points.

This is differentiation, not a dunk. The projects overlap because they both follow similar philosophies: both reject loose prompting and unverifiable agent claims.

## Why use Beislið instead of GSD?

The main problem that GSD-style workflows solve is momentum: keep the agent moving, break work down, and get tasks done.

What we found is that once you move past a certain speed the main problem becomes the shared process: make the agent follow the repo's gates, ticket flow, review loop, and PR handoff rules. And make sure your whole team is on the same wavelength.

Beislið solves for that pain point.

## Can I use Beislið with another skill system?

Usually, yes, but you need to be careful to avoid conflicting gates.

If another system says "always start with its brainstorm flow" and Beislið says "start ticket work with kickoff," choose the workflow you want for that repo. Mixing methodologies works best when one system owns the lifecycle and the other provides supporting skills.

## Does Beislið make agents autonomous?

No. Beislið is human-centric by design.

It gives agents enough structure to do useful work, but it keeps approval gates around product direction, implementation design, risky fixes, review risk, posting comments, pushing, and PR creation.

## Do I need `.beislid/workflow.md`?

Not for every skill.

Basic skills such as `spec`, `blueprint`, `debug`, `verify`, and `review` can work after install.

You need `.beislid/workflow.md` when you want repo-aware orchestrators such as `kickoff`, `ready-for-review`, `review-response`, and `babysit` to use ticket sources, branch patterns, PR targets, quality gates, review sources, update commands, or babysit closeout policy.

## What does Beislið change in my repo?

Only what you ask it to change.

The normal project-owned file is:

```text
.beislid/workflow.md
```

`setup` may also add or update an agent-instructions block in `AGENTS.md` when you approve it.

Beislið does not silently commit generated artifacts, push branches, post comments, or create PRs. You own your process, not Beislið.

## Does Beislið replace CI or human review?

No.

Beislið helps agents run the checks your project expects and gather evidence before making claims. CI and human review remain authoritative.

## Which coding agents does Beislið support?

Right now there is official support for Claude Code, Codex and Pi but the skills and framework are agent agnostic. The installer links global skills into:

- `~/.agents/skills`
- `~/.claude/skills`
- `~/.codex/skills`

Project-specific skill probes prefer repo-local `.beislid/skills/<name>` before `$BEISLID_SKILLS_DIRS` and those global host directories. The skills are portable Markdown. Coding agent behavior still varies, especially around invocation syntax, natural-language triggers, tool names, and optional extensions.

## Why so many gates?

Because agent failures often happen at phase boundaries:

- building the wrong thing
- coding before the approach is understood
- claiming done without fresh evidence
- fixing symptoms instead of root causes
- handing off with local review findings still visible
- posting or pushing before the human has approved the risk

The gates exist to make those failures harder.

## What if my team's workflow is different?

Beislið was built with this in mind, what it gives you is structure. Repo-aware flows read `.beislid/workflow.md` so the project can define branch patterns, ticket sources, quality gates, lifecycle actions, scopes, PR review sources, and update paths.

Future work is tracking more explicit workflow packs, broader lifecycle-action events, policy levels, and team rollout templates. For now, use `setup`, edit `workflow.md`, and run `doctor` to audit what the repo declares.

## Is Beislið only for teams?

No.

A solo developer can use it as a disciplined personal workflow. The team value is stronger because repo-local config makes expectations visible to every agent and developer working in the codebase.

## Is Beislið trying to be a full project-management tool?

No.

It can read from and write to configured ticket or PR systems, but it is not a tracker. It is the harness between agent sessions and the development workflow your project already uses.

## How do I pronounce Beislið?

B as in bat but softer.
ei as in a in case.
sl is quirky, sounds like s-t-l
i as in bit.
ð as in that is hard to pronounce.
