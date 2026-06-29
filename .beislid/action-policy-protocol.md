# Beislið action policy protocol v1

Shared integration rules for repo-aware orchestrators. This file is intentionally short; the deterministic policy table, registry, and validation live in `beislid action-policy` / `scripts/action_policy.py`.

## When to evaluate

Evaluate immediately before any covered side effect, after the command/action is known but before it runs. Covered v1 boundaries:

- configured lifecycle actions and tracker/ticket/PR writes
- workspace writes owned by an orchestrator, dependency installs, and autofix commands
- local git mutations such as merge, rebase, commit, or branch update
- remote git or PR writes such as push, PR create/ready, review replies, re-review requests
- any configured gate/final-check/lifecycle command declared or known to mutate state

Read-only inspection can be `read` / `network-read`; if an action is not classified, pass no classes and let unknown/unclassified fallback decide.

## Evaluator call

Use the configured run mode when known; otherwise default human-in-the-loop orchestrator runs to `supervised-auto`. Use `unattended-auto` only for explicitly unattended/fast-path rails.

Call shape:

```bash
beislid action-policy evaluate \
  --mode <supervised-auto|unattended-auto> \
  --action <stable-action-id> \
  --class <class> [--class <class> ...] \
  --sandbox-baseline <none|non-default-branch|separate-worktree|host-sandbox> \
  [--default-branch] [--uncommitted-changes]
```

Stable action ids should be specific enough for summaries, e.g. `git.merge`, `git.commit`, `git.push`, `gh.pr.create`, `ticket.comment`, `ticket.update`, `pr.review.reply`, `gate.autofix`, `dependency.install`, or `lifecycle.<event>.<name>`.

## Decision handling

- `allow`: proceed and record the envelope.
- `ask`: stop at a visible approval boundary. Show action, classes, reason, sandbox status, and remediation. If approved, record the original envelope plus `human_outcome: approved`; if declined, record `human_outcome: declined` and stop or skip only that action when the protocol allows skipping.
- `deny`: do not run the action. Stop with the evaluator reason and remediation unless the phase has a safe non-side-effect fallback such as printing a manual update.

A prior blanket approval does not satisfy an `ask` decision. Ask once per policy boundary; do not duplicate the approval question in status/progress prose and final output.

## Recording

Run summaries and durable ledger events should preserve the evaluator envelope fields: `decision`, `mode`, `action`, `classes`, `matched_rules`, `sandbox_status`, `requires_human`, `log_level`, `reason`, and `remediation`. Add separate fields for `human_outcome`, `side_effect_status`, and artifact/log paths. Never include secrets, auth headers, hidden reasoning, or raw unredacted command output.

## Sandbox status

At minimum, pass:

- `baseline`: `none`, `non-default-branch`, `separate-worktree`, or `host-sandbox`
- `default_branch`: true when on the default/base branch
- `uncommitted_changes`: true when pre-existing user changes are present

If the host cannot detect a stronger sandbox, use the conservative lower baseline. Unknown sandbox state should not be inflated.
