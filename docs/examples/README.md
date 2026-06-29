# Example team workflow configurations

These are complete, self-documenting `.beislid/workflow.md` files you can drop
into a real repo and adapt. Each example includes the version stamp, prose
explaining the team context, intended policy, and expected ticket-to-PR flow.

Run `/doctor` after adapting an example to audit your config against installed
Beislið capabilities.

| Example | Audience | Tracker | Review surface | Notable features |
|---|---|---|---|---|
| [01 — Small OSS library](./01-small-oss-library.md) | Solo maintainer, small team | GitHub Issues (`gh` CLI) | GitHub PRs (`gh` CLI) | Minimal gates, manual closeout |
| [02 — Frontend app](./02-frontend-app.md) | Frontend team (Next.js) | Linear (MCP) | GitHub PRs (`gh` CLI) | TypeScript, build gate, babysit |
| [03 — Backend service](./03-backend-service.md) | Backend team (Go API) | Linear (MCP) | GitHub PRs (`gh` CLI) | Integration tests, migration checks |
| [04 — Monorepo](./04-monorepo.md) | Multi-package team | Linear (MCP) | GitHub PRs (`gh` CLI) | Gate sets per scope, cross-package gates |
| [05 — Linear + GitHub team](./05-linear-github-team.md) | Established product team | Linear (MCP) | GitHub PRs (`gh` CLI) | Model routing, clean eval, lifecycle actions, auto memento/retro |
| [06 — Jira + GitLab team](./06-jira-gitlab-team.md) | Enterprise team | Jira (MCP) | GitLab MRs (`glab` CLI) | `develop` base branch, Jira transitions |
| [07 — Manual / no-tracker](./07-manual-no-tracker.md) | Solo developer, prototyping | Paste (manual) | GitHub PRs or manual | Paste-based tickets, minimal gates |

## How to use these examples

1. **Pick the closest match** from the table above.
2. **Copy** the file to `<your-repo>/.beislid/workflow.md`.
3. **Adapt** the config: replace team prefixes, tool commands, and URLs with
   your project's actual values. Each file ends with a "Turn this into your
   own config" section listing specific changes you'll need.
4. **Audit** with `/doctor` to verify the config and probe capabilities.
5. **Extend** with `/setup` to add sections not covered by the example.