---
name: rinse
description: "Use when the user asks to 'rinse', 'run a review/fix loop', 'iterate on review findings', 'review and fix until clean', or harden a branch before PR handoff. Orchestrates side-effect-free review, user-approved fixes, verification, reruns, and redesign stop conditions."
---

# Rinse

## Project guidance preflight

If `.beislid/workflow.md` has `beislid:skill_guidance`, load `all` and `rinse` guidance before proceeding; stop on missing/empty `must-read`; report loaded/missing.

Run an iterative review/fix/verify loop around the side-effect-free `review` primitive. `rinse` is an orchestrator: it may edit files, run verification, and repeat review passes, but only within user-approved boundaries.

The boundary is strict:
- `review` finds issues and returns the review contract.
- `rinse` decides, with the user, which findings to fix.
- `rinse` applies fixes, runs verification, and reruns review.

Use this for:
- Hardening a local branch before `ready-for-review`
- Working through multiple review findings in a controlled loop
- Running a local review/fix cycle for routine PRs
- Coordinating optional external reviewers when the host provides an agent-neutral way to call them

Do not use this for:
- A single side-effect-free review — use `review`
- A final whole-diff pass — use `fresh-eyes`
- Inbound PR comment posting — use `pr-patrol`
- Post-submission feedback on your own PR — use `review-response`
- Open-ended redesign when repeated iterations show the approach is wrong — stop and route to `blueprint`

## Checklist

Complete these phases in order:

1. Establish the diff, requirements, and allowed fix boundary
2. Run `review` using the shared review contract
3. Triage findings with the user
4. Apply approved fixes only
5. Run applicable verification
6. Rerun `review`
7. Stop, continue, or escalate to redesign

## Phase 1: Establish scope

Determine the review input:

```bash
git status --short
gh pr view --json baseRefName,headRefName 2>/dev/null
git merge-base HEAD main  # or master / PR base when applicable
git diff <base-sha>...HEAD --stat
```

Load requirements/context from the caller, plans, specs, ticket summaries, or commit messages. If no requirements are available, say so and review against general production readiness.

Ask the user for the fix boundary before making any changes:

```text
What may rinse change?
(a) Only fixes for Critical findings
(b) Critical + Important findings
(c) All findings including Minor cleanup
(d) A custom file/path boundary
```

Record the answer and obey it for the whole loop unless the user changes it explicitly.

## Phase 2: Run review

Invoke `review` with:
- Diff/range
- Requirements/context
- Verification already run
- User-approved focus areas, if any

If the host supports subagents or external model orchestration, optional additional reviewers may be called here, but they must use the same review contract. External reviewers must not edit files or post comments.

For security-sensitive PRs — auth, permissions, token handling, crypto, secrets, privacy, or data export — offer multi-reviewer mode if available. For routine PRs, local review is enough.

## Phase 3: Triage findings

Present the findings grouped by severity and propose an action for each:

- **Fix now** — inside the approved boundary and likely valid
- **Needs investigation** — read more code before deciding
- **Push back / accept risk** — likely false positive or intentional trade-off
- **Out of boundary** — valid issue but outside the user's approved fix scope

Ask for user approval before editing. Do not silently expand scope.

## Phase 4: Apply approved fixes

For each approved finding:

1. Read the affected code and enough surrounding context to understand the issue.
2. Make the smallest fix that addresses the root cause.
3. Avoid unrelated refactors.
4. Track which finding IDs were addressed.

If a finding is wrong, document the evidence and keep it in the loop summary as accepted/pushed back rather than pretending it was fixed.

## Phase 5: Verify

Run verification appropriate to the files changed. Prefer configured project gates if the caller supplied them. Otherwise infer minimal checks from the repo:

- Unit tests for touched code
- Typecheck/build when applicable
- Lint when applicable
- Targeted regression tests for bug fixes

If verification fails, investigate the failure before changing code. Do not assume the test is wrong.

## Phase 6: Rerun review

Invoke `review` again with:
- Updated diff/range
- Findings addressed in the previous iteration
- Verification command output summary
- Any risks the user accepted

Compare new findings with previous findings.

## Phase 7: Stop conditions

Stop successfully when:
- No Critical or Important findings remain, or
- The user explicitly accepts the remaining Critical/Important risk, and
- Verification has passed or the user explicitly accepts skipped/failed verification risk

Stop and escalate when:
- The same subsystem has blocking findings for two consecutive iterations
- A fix introduces new blocking findings in a different subsystem
- The review keeps finding symptoms of a larger design flaw
- Verification failures point to unclear requirements or conflicting architecture

Escalation message:

```text
Rinse is no longer reducing risk. The same subsystem is still producing blocking findings after repeated iterations. Stop patching and route this through blueprint/redesign before continuing.
```

## Optional final pass

After the iterative loop converges, offer `fresh-eyes`:

```text
The iterative findings are resolved. Want a final fresh-eyes whole-diff pass before ready-for-review?
```

For security-sensitive or large PRs, recommend yes.

## Output summary

End with:

```md
### Rinse Summary
- Input/base/head: ...
- Iterations run: N
- Findings fixed: ...
- Findings accepted/pushed back: ...
- Verification run: ...
- Fresh-eyes run: yes/no
- Remaining risk: ...
- Suggested next action: ready-for-review / fresh-eyes / blueprint / manual follow-up
```

## Common mistakes

- **Letting review edit code** — `review` is a primitive. `rinse` owns changes.
- **Skipping user approval** — every fix boundary needs approval before editing.
- **Expanding scope silently** — do not turn Minor findings into opportunistic refactors.
- **Looping forever** — repeated blocking findings in the same subsystem mean redesign, not more patching.
- **Ignoring verification** — review without tests is only half the loop.
- **Accepting bad findings performatively** — push back with evidence when the review is wrong.
