# Review workflows

Beislið has multiple review-oriented skills because "review" can mean different jobs.

## Pick the right review flow

| Situation                                                       | Use             | Why                                                                                                                                                   |
| --------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| You want the first automated pass over a local or supplied diff | `review`        | Produces severity-categorized findings and a readiness verdict. No side effects.                                                                      |
| You want one last whole-diff pass after normal review fixes     | `fresh-eyes`    | Looks for cross-file consistency, config drift, stale docs, limits, baseline compatibility, and issues hunk-by-hunk review can miss. No side effects. |
| You want to iterate through findings and fixes before PR handoff  | `rinse`         | Orchestrates `review`, user-approved fixes, verification, reruns, and redesign stop conditions.                                                       |
| You want to review someone else's PR                            | `pr-patrol`     | Fetches PR context/diff, runs the review contract, drafts comments, and posts only approved comments.                                                 |
| You want to explain your own diff to a human                    | `walk-the-diff` | Runs an interactive walkthrough and saves feedback notes.                                                                                             |
| Someone already left PR comments or QA feedback on your work    | `review-response`    | Fetches/categorizes feedback, helps fix or push back, verifies, then pushes/replies.                                                                  |
| An open PR needs goal-backed monitoring through review/CI        | `babysit`       | Requires `/goal`; loops through configured review-response/gates until green, then performs configured closeout automation when policy allows.          |
| A new branch is ready for review                                   | `ready-for-review`       | Runs quality gates, optional clean-eval gates, `review`, the configured final check, and PR creation. Existing-PR updates take the fast path.       |

## Review primitives

`review` is the first-pass primitive. `fresh-eyes` is the default final-pass primitive; `workflow.md` may replace or disable that final pass for `ready-for-review`.

Both may read files and inspect diffs. Neither may:

- edit files
- commit
- push
- post comments
- update tickets
- create PRs

This boundary is intentional. Findings should be safe to ask for even when you are not ready to change the branch.

## Review orchestrators

`rinse`, `pr-patrol`, `review-response`, `babysit`, and `ready-for-review` decide what to do with findings after user approval.

- `rinse` loops through review findings, approved fixes, verification, and reruns.
- `pr-patrol` reviews someone else's PR and posts only comments you approve.
- `review-response` handles feedback already left on your work.
- `babysit` requires goal mode and keeps rechecking an open PR, delegating feedback fixes/replies to `review-response`, running configured gates, and performing configured closeout steps when safe.
- `ready-for-review` runs the final PR handoff path for new PRs and the fast path for existing PR updates. It can also summarize configured ship-time planning artifacts and require a clean worktree/container evaluator before handoff when workflow policy says so. See [worktree isolation](./worktree-isolation.md) for isolated agent work and explicit cleanup expectations.

## AgenticReviewer deferred-review evidence

A green AgenticReviewer/provider check is not enough on its own. For example, if PR comments or review text from CodeRabbit contain any of these signals, classify the review as `not reviewed` / `deferred review` even when GitHub shows `SUCCESS`:

- `Review skipped`
- `Review limit reached`
- `rate limited`
- `draft detected`

Observed shapes from recent managed repos:

- `sandsower/rondo#92` — CodeRabbit comment said `Review limit reached`, but the check was green.
- `sandsower/memento-vault#128` — CodeRabbit said `Review skipped` because the PR was draft when it ran; a later `@coderabbitai review` still did not produce a fresh actionable review before the check stayed green.

Babysit and merge logic should treat provider-specific deferred-review signals as live evidence that the PR has not been fully reviewed yet. The path must wait/retry, ask for guidance, or create a follow-up issue per policy before merge.

## Prompt profiles for already-posted review comments

`review-response` can optionally use prompt profiles to extract an explicit `agent_prompt` from loaded PR review comments. That enrichment applies only to feedback that is already posted; it does not create a separate CodeRabbit backend or a new-review workflow.

Keep `pr_review_source` and `pr_review_update` as the source/update path. Use prompt profiles when the comment body already carries an agent-ready instruction, and leave CodeRabbit CLI / "review now" actions to the workflows that actually run a fresh review.

## Pre-PR hardening

Use this when you want a branch hardened before PR creation:

```text
verify → review → fix important findings → verify → fresh-eyes → ready-for-review
```

Or invoke the orchestrated loop:

```text
rinse → ready-for-review
```

Critical findings block progress. Important findings should be fixed unless you explicitly accept the risk with evidence.

## Existing PR updates

For an existing PR, `ready-for-review` uses the update fast path:

```text
quality gates → push → report PR URL
```

It skips local review by default because the branch is already under review. Run `review` or `fresh-eyes` manually first if the update needs another local pass. If AgenticReviewer deferred-review evidence is present, carry it into the handoff summary/body instead of treating the green check as sufficient.
## Responding to review or QA

Use `review-response` when feedback already exists.

```text
review-response → debug if needed → fix → verify → push or reply
```

`review-response` is for response work, not for opening a new PR or reviewing someone else's PR.

## Babysitting an open PR

Use `babysit` when a PR is already open and you want Beislið to keep monitoring CI/review state until it is green or blocked:

```text
babysit → review-response loop → configured gates → green PR or configured closeout
```

`babysit` requires `/goal` support. Claude includes `/goal`; Pi users need the `pi-goal` package enabled. Closeout actions such as merge, memento capture, and retro are opt-in/config-driven and still respect action policy.

## Reviewing someone else's PR

Use `pr-patrol`.

It fetches PR context and diff, runs the review contract, drafts comments, and posts only comments you explicitly approve. If posting is not configured, it prints manual comments.

## Walking your own diff

Use `walk-the-diff` when a human reviewer needs a guided tour of your local changes.

It is a walkthrough, not an automated review. Use `review` when you want findings. Use `walk-the-diff` when you want explanation and feedback capture.
