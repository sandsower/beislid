---
name: babysit
description: "Use when the user asks to babysit a PR, run /babysit, keep a PR green, monitor review/CI until ready, or optionally close out a PR through configured merge/capture/retro automation. Can run directly; host goal/persistence support is optional."
---

# Babysit

Babysit the current pull request until configured live evidence says it is green, then perform the configured closeout path when policy allows it.

This is an outer-loop workflow. It does not replace `review-response`; it repeatedly uses `review-response` for feedback handling, configured gates for proof before push, and optional host persistence for wait/recheck cycles.

## Persistence model

`babysit` can run directly in any host. Goal/persistence support is optional, not a hard requirement.

- In Claude Code, users may manually wrap babysit in `/goal` for cross-wait persistence.
- In Pi, bundled `/babysit` starts a Beislið-owned babysit runtime with loop state and completion tools. It does not depend on `pi-goal` or invoke slash commands from another extension.
- Without persistence, perform the current audit/feedback/gate step. If the PR is not terminal green or blocked by turn end, stop with evidence and the next recheck/action.

## Inputs

Use, in order:

- invocation args such as `stop when green`, `merge`, `don't merge`, `skip memento`, or `skip retro`
- `.beislid/workflow.md`
- current branch PR metadata from configured PR host tooling when available
- configured `pr_review_source` and `pr_review_update`
- configured gates, scopes, or gate sets
- configured `babysit` closeout policy
- optional `review_policy` AgenticReviewer risk/opt-in policy

## Configuration

Optional workflow block:

```beislid:babysit
goal:
  token_budget: 50k
loop:
  use_review_response: true
  run_configured_gates_before_push: true
  wait_interval_seconds: 60
  timeout_minutes: 60
closeout:
  merge:
    mode: ask # off | ask | auto
    method: squash # squash | merge | rebase | repo-default
    delete_branch: true
  memento:
    mode: ask # off | ask | auto
  retro:
    mode: ask # off | ask | auto
    apply_findings: ask # off | ask | auto
```

Defaults when absent: no goal budget, use `review-response`, run configured gates before pushes, merge/memento/retro off. Invocation args override config for this run.

## Workflow

1. **Load project config** — read `.beislid/workflow.md`; hard-fail if missing or wrong version, matching other repo-aware orchestrators.
2. **Detect persistence mode** — note direct, manually host-goal-wrapped, or Pi Beislið runtime. Do not stop solely because persistence is absent.
3. **Find the PR** — use configured PR host data or `gh pr view` when available. If no current PR is found, stop and ask for the PR URL/number.
4. **Read live state** — collect checks, mergeability/conflict state, review decision, PR-level comments, and inline review threads.
5. **Detect feedback and review-policy state** — use `pr_review_source`; never trust a green review-bot status alone. Treat AgenticReviewer provider comments containing `Review skipped`, `Review limit reached`, `rate limited`, or `draft detected` as `not reviewed` / `deferred review`, even if the check is green. If `review_policy.agentic_reviewer.mode: opt_in_final_review` is configured, classify current PR risk with ready-for-review's path/size rules and require a real AgenticReviewer review when `risk > max_auto_closeout_risk`. If required review is missing and the configured opt-in label is absent, add it when action policy allows; if label add fails, stop/ask before using `description_keyword`. Unresolved review comments or requested changes route to `review-response` when enabled.
6. **Feedback handling** — if `loop.use_review_response` is true, invoke `review-response`; it owns categorization, fixes, replies, commits, pushes, and child-ticket handling. If false, do not fix/reply/commit/push automatically; stop with the feedback summary and ask how to proceed.
7. **Gate before push** — before any babysit-owned push or merge preparation, run the configured applicable gates. Use existing scope/gate-set selection rules where available. Do not invent hardcoded gates.
8. **Wait and recheck** — after pushes or pending checks, wait using bounded polling or host monitor facilities. Do not busy-loop. Re-read live PR state after each transition.
9. **Green audit** — green means required checks successful, mergeable/no conflicts, acceptable review state, no unaddressed actionable feedback, and any risk-required AgenticReviewer review is real. Green status plus deferred-review evidence is not acceptable.
10. **Closeout** — perform configured merge, memento capture, and retro only when green audit passes and action policy allows. Policy-check closeout side effects: `gh.pr.merge`/`pr.merge` as `git-remote`, `memento.capture` as `workspace-write`, `retro.run` as `read` plus `workspace-write` when it may write artifacts, and `retro.apply`/setup edits as `workspace-write`. Stop for approval when mode is `ask`; proceed only when mode is `auto` and policy allows.
11. **Complete persistence loop when present** — call completion only after final audit and configured closeout, or the stop-when-green endpoint. In Pi runtime, call `update_beislid_babysit({status:"complete", summary:"..."})`; if blocked, call `update_beislid_babysit({status:"blocked", summary:"..."})`.

## Safety stops

Stop and ask when any occur:

- no PR can be identified
- red or pending required checks at a merge boundary
- conflicts or unsafe merge resolution
- review feedback requiring architectural, product, scope, or policy judgment
- user-approved pushback is needed
- required credentials or external services are unavailable
- action policy returns `ask` and no approval has been given
- action policy returns `deny`
- every closeout step is disabled, in which case stop green and report
- retro findings would require editing workflow/config and `apply_findings` is not `auto`

Never force-push or amend published commits. Never merge to bypass a failing/pending required check. Never interpolate review reply bodies into shell commands; use temp JSON payload files.

## Closeout semantics

- `merge.mode: off` — stop once green and report.
- `merge.mode: ask` — show final audit and merge command/method; wait for approval.
- `merge.mode: auto` — merge after green audit only if action policy allows. If policy asks, ask; if policy denies, stop.
- `memento.mode` controls durable knowledge capture after merge/green endpoint.
- `retro.mode` controls running retro after closeout.
- `retro.apply_findings` controls whether accepted retro/setup findings may be applied automatically. `auto` still respects action policy; ambiguous/destructive edits stop.

## Output

When stopping, report: PR URL/branch, final state, checks/review/mergeability evidence including deferred-review comments, feedback handled, gates run, closeout side effects, and remaining blockers or human decisions.

## Common mistakes

- Treating CI green as enough when review threads are unresolved.
- Treating green AgenticReviewer status as reviewed when comments say skipped, rate-limited, or draft-detected.
- Hardcoding provider labels, gates, or risk thresholds instead of reading workflow config.
- Assuming `/goal` is required; direct runs are allowed but must stop with next steps when no persistence mechanism is active and the PR is not terminal.
- Posting replies or merging without policy and approval handling.
- Mentioning private provenance in public tracker/PR updates; keep public updates focused on the current repo and PR only.
