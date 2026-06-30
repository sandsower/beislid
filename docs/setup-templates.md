# Setup templates

These are starter policy shapes for `.beislid/workflow.md`. They are meant to
help a repo pick a sensible first config or a common team posture. They do **not**
change Work Contract semantics and they do **not** imply automatic execution
before human approval.

For full examples you can copy, see [Example team workflow configurations](./examples/README.md).

## Template chooser

| Template | Use when | Start from |
|---|---|---|
| Minimal bootstrap | A repo needs the smallest useful Beislið config | `docs/team-rollout.md` |
| Linear + GitHub team | Tickets live in Linear and PRs live in GitHub | `docs/examples/05-linear-github-team.md` |
| Manual / no tracker | You want a lightweight fallback first | `docs/examples/07-manual-no-tracker.md` |
| Strict review loop | The team wants babysit, clean eval, and reply automation | `docs/examples/05-linear-github-team.md` |

## Minimal bootstrap

Use this when the repo is new and you only want the minimum shared workflow:

- version stamp
- ticket source
- branch pattern, if tickets are branch-embedded
- probe cache
- `AGENTS.md` bootstrap block

Starter intent:

- `kickoff` should find the ticket and create the first planning record.
- `doctor` should validate the config before anyone relies on it.
- nothing should assume PR automation yet.

## Linear + GitHub team

Use this when the team already uses Linear for tickets and GitHub for PRs:

- `ticket_source` via Linear MCP
- `ticket_update` for kickoff notes and review-response replies
- `pr_review_source` / `pr_review_update` for review comments
- optional `review_feedback_profiles` when review comments already include agent-ready prompts
- gates for lint/test/typecheck/build
- `action_policy` and `babysit` once the team trusts the loop

Starter intent:

- `kickoff` can record the workpad in the tracker.
- `review-response` can read and answer review comments.
- `babysit` can keep rechecking until the PR is green.

## Manual / no tracker

Use this when you want the shortest path to a usable repo-local workflow:

- `ticket_source: paste`
- one or two fast gates
- no tracker automation
- no babysit closeout

Starter intent:

- the agent asks for pasted ticket context instead of guessing.
- the repo stays useful even without auth or external services.
- you can upgrade to Linear or GitHub later without rewriting the whole file.

## Strict review loop

Use this when the team wants the workflow to keep a PR green with minimal drift:

- `pr_review_source` and `pr_review_update`
- optional `review_feedback_profiles` for prompt-profile enrichment on already-posted comments
- `clean_eval` for review handoff
- `babysit` with gates before push
- optional `memento` / `retro` closeout policy

Starter intent:

- review feedback gets handled through the configured update path.
- branch readiness is checked before push boundaries.
- merge, memento, and retro remain policy decisions, not defaults.

## Guardrails

- Keep these templates as starter policy only.
- Pair them with the Work Contract examples when you need scope examples.
- If a template would hide approval boundaries, simplify it.
- If a team wants more detail, link to the existing full examples instead of growing the starter into a full config.
