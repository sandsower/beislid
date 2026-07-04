# Lifecycle artifact templates v1

Canonical Beislið lifecycle artifacts are terse, evidence-focused records. They may be files, ticket comments, PR bodies, or chat/report output, but they use the same section shapes so a fresh reader can inspect what happened without replaying the conversation.

## Defaults: local vs posted

| Artifact | Canonical default | Ticket/PR default | Why |
|---|---|---|---|
| Spec | local planning artifact when `spec_approved` lifecycle action is configured; otherwise chat record | post/link only a short scope + acceptance summary when useful | specs can contain exploratory product context; downstream skills need a stable local seed |
| Blueprint | local design artifact when `blueprint_approved` lifecycle action is configured; otherwise chat record | post/link only selected approach, risk, and verification summary | implementation details are reviewable but usually too noisy for tickets |
| Implementation plan | local checkpoint when `implementation_plan_created` lifecycle action is configured; otherwise visible task list | do not post by default; summarize current plan in workpad/ticket if needed | plans are operational and may churn during execution |
| Verification report | local/chat command evidence; ledger/gate logs when available | post only command names + pass/fail summary unless a reviewer asks for logs | raw logs are bulky; decisions need concise proof |
| Review report | local/chat side-effect-free findings | do not post by default; orchestrators choose approved comments or PR body notes | draft findings may include false positives or accepted risks |
| Fresh-eyes report | local/chat final whole-diff findings | do not post by default; PR body may mention final-check status | final pass is a handoff input, not public review commentary |
| Ship summary | PR body or ticket handoff summary | post by default at PR creation/update | reviewers need what/why/proof/risks in one place |
| Feedback response log | local/chat log plus replies through configured channels | post replies only to the source thread/comment; ticket workpad may summarize | feedback is source-specific and should not be duplicated blindly |

Full artifacts may be posted or attached only when workflow config, a ticket-authored test plan, or explicit user instruction says so. Prefer links to local/repo artifacts over pasting long bodies. Never include hidden chain-of-thought, secrets, credentials, private model routing, or unrelated session provenance.

## Common rules

Every artifact should make these fields explicit or clearly discoverable in its template-specific sections:

- **Source**: ticket/PR/spec/design/gate that caused it.
- **Scope**: what is covered and what is explicitly not covered.
- **Evidence**: commands, diffs, reviews, screenshots, or linked logs that support claims.
- **Decision state**: draft, approved, passing, blocked, accepted risk, or superseded.
- **Next owner/action**: who/what consumes the artifact next.

Keep sections short. Use bullets over narrative. If evidence is missing, write `Missing:` with the exact command, artifact, or human decision needed.

## Spec artifact

Use for approved product/requirements records.

````md
# <feature or ticket>

## Kind
work-contract-v1 or lightweight-spec-v1

## Status
approved | draft | needs-human-decision | superseded

## Source
- Ticket/issue/link:
- Author/session:

## Problem
<what is broken or missing, and who feels it>

## Desired Outcome
<observable end state>

## Constraints
- <technical/product/process constraint>

## Acceptance Outcomes
- <user-observable or mechanically checkable outcome>

## Unknowns / Human Decisions
- None, or <decision needed before routing>

## Risk Classification
- Scope: atomic | single_pr | multi_slice | project | unknown
- Confidence: low | medium | high
- Rationale:

## Extension Slots
```yaml
scope_classification:
  kind:
  confidence:
  rationale:
  recommended_route:
  requires_human_approval:
  requires_split:
  split_reason:
proof_requirements: []
slice_plan: null
children: []
```

## Ownership Boundary
<what Beislið owns vs external runner/team responsibility>
````

## Blueprint artifact

Use for approved implementation design.

```md
# <feature> design

## Status
approved | draft | superseded

## Source Requirements
- Spec/Work Contract/ticket:
- Selected phase/slice, if any:

## Recommended Approach
<chosen approach and why>

## Alternatives Considered
- <option>: <tradeoff/reason rejected>

## Files / Modules
- `<path or module>` — <expected change>

## Data / Control Flow
<short flow, sequence, or boundary description>

## Edge Cases and Risks
- <risk> — <mitigation or accepted risk>

## Verification Plan
- <command/review/manual proof and expected pass condition>

## Open Questions
- None, or <question that blocks implementation>
```

## Implementation plan artifact

Use before code changes for a file-level execution plan/checkpoint.

```md
# <feature> implementation plan

## Status
planned | in-progress | superseded

## Source
- Design/spec/ticket:

## Goal
<one sentence>

## Architecture
<2-3 sentences describing how pieces fit>

## Files Touched
- `<path>` — <planned change>

## Tasks
- [ ] <task id>: <test/implementation step, expected outcome>

## Batches / Dependencies
- Batch 1: <parallel/serial tasks>
- Batch 2: <depends on ...>

## TDD Exceptions
- None, or <task>: <why tests do not apply>

## Verification Plan
- `<command>` — <expected pass condition>

## Evidence
- Planned proof only until commands are run; link the later Verification report when available.

## Next Step
<next task/batch/owner>

## Open Risks / Questions
- None, or <risk/question>
```

## Verification report

Use before claiming done/fixed/passing.

```md
# Verification report

## Scope
<feature/fix/diff being verified>

## Commands Run
| Command | Result | Evidence |
|---|---|---|
| `<command>` | pass/fail/skipped | <exit code, key output, log path> |

## Manual / Visual Checks
- None, or <check + evidence path>

## Required Proof Mapping
- <proof requirement> → <evidence or Missing: ...>

## Regressions / Gaps
- None, or <remaining gap>

## Verdict
passing | failing | blocked | partial
```

## Review report

Use for first-pass side-effect-free diff review.

```md
# Review report

## Review Metadata
- Input:
- Base:
- Head:
- Requirements:
- Independent reviewer: yes/no
- Fresh-eyes posture: <omit for normal review; include for fresh-eyes>

## Strengths
- <what is sound>

## Findings
### Critical
None, or:
#### <ID>: <short title>
- File: <path:line or unavailable>
- Confidence: high | medium | low
- Source pass: main | spec-compliance | code-quality | fresh-eyes | <other>
- Issue: <what is wrong>
- Evidence: <diff/code/requirement evidence>
- Why it matters: <impact>
- Suggested fix: <specific change>
- Verification: <proof command/check>

### Important
None, or the same finding shape.

### Minor
None, or the same finding shape.

## Caller Handoff
- Blocking findings:
- Optional findings:
- Suggested next action:

## Verdict
Ready to merge: Yes | With fixes | No
Reason:
```

## Fresh-eyes report

Use the review report shape. In `Review Metadata`, include `Fresh-eyes posture: whole-diff final pass`. Finding IDs should use `FE1`, `FE2`, ... to distinguish them from first-pass review findings.

## Ship summary

Use for PR bodies, existing-PR updates, or final ticket handoff.

```md
# Ship summary

## Status
ready-for-review | updated-pr | shipped | blocked

## Source
- Ticket/PR:

## What changed
- <reviewable change>

## Why
- <ticket/spec outcome served>

## Proof
- `<command/review/check>` — pass/fail/pending, <log/path if useful>

## Reviewer notes
- <risk, accepted limitation, migration note, deferred bot review, or None>

## Artifacts
- Spec/design/plan/report links or `None`

## Follow-ups
- None, or <linked issue/ticket>

## Next owner/action
- <reviewer/maintainer/merge/recheck owner>
```

## Feedback response log

Use after PR review or QA feedback.

```md
# Feedback response log

## Source
- PR/ticket/comment/thread:

## Feedback Queue
| ID | Source | Classification | Decision | Reply status |
|---|---|---|---|---|
| F1 | <link/thread> | bug/request/question/out-of-scope | fix/pushback/follow-up | posted/printed/pending |

## Changes Made
- <commit/diff summary or None>

## Evidence
- `<command>` — <result/log>

## Replies
- F1: <terse reply body or link>

## Follow-ups / Out of Scope
- None, or <linked issue/ticket>
```
