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
| A new branch is ready for review                                   | `ready-for-review`       | Runs quality gates, invokes `review` then the configured final check, and handles PR creation. Existing-PR updates take the fast path.                 |

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

`rinse`, `pr-patrol`, `review-response`, and `ready-for-review` decide what to do with findings after user approval.

- `rinse` loops through review findings, approved fixes, verification, and reruns.
- `pr-patrol` reviews someone else's PR and posts only comments you approve.
- `review-response` handles feedback already left on your work.
- `ready-for-review` runs the final PR handoff path for new PRs and the fast path for existing PR updates.

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

It skips local review by default because the branch is already under review. Run `review` or `fresh-eyes` manually first if the update needs another local pass.

## Responding to review or QA

Use `review-response` when feedback already exists.

```text
review-response → debug if needed → fix → verify → push or reply
```

`review-response` is for response work, not for opening a new PR or reviewing someone else's PR.

## Reviewing someone else's PR

Use `pr-patrol`.

It fetches PR context and diff, runs the review contract, drafts comments, and posts only comments you explicitly approve. If posting is not configured, it prints manual comments.

## Walking your own diff

Use `walk-the-diff` when a human reviewer needs a guided tour of your local changes.

It is a walkthrough, not an automated review. Use `review` when you want findings. Use `walk-the-diff` when you want explanation and feedback capture.
