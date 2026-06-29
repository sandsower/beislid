---
name: review
description: "Review a local diff or supplied patch against requirements. Produces severity-categorized findings and a readiness verdict. Side-effect-free primitive used by ready-for-review, future rinse-style loops, PR patrol workflows, and ad-hoc review requests."
---

# Review

Review a diff against requirements and return findings. This is a primitive, not a workflow.

`review` may read files, inspect diffs, and classify findings. It must not edit files, commit, push, post comments, update tickets, create PRs, or run a fix loop. Callers decide what to do with the findings.

Use this for:
- Pre-PR local diff review from `ready-for-review`
- Ad-hoc "review my changes" requests
- Reviewing a supplied patch/diff
- A reusable review contract for `fresh-eyes`, `rinse`, and `pr-patrol` workflows

If the repo declares custom lifecycle hooks, read `../lifecycle-hooks.md` and honor any phase-boundary hooks before and after review.

Do not use this for:
- A final whole-diff pass after iterative fixes — use `fresh-eyes`
- Interactive walkthroughs of your own diff — use `walk-the-diff`
- Reviewing someone else's GitHub PR and posting comments — use `pr-patrol`
- Security-only audits — use a security audit workflow if available
- Fixing findings — return findings to the caller

If the reviewer explicitly wants a durable visual artifact for the diff, evidence, or explanation, suggest `show-me` and wait for the user to ask. Do not auto-run `show-me` from `review` in v1.

## Process

### 1. Establish the input

Accept one of:
- Caller-supplied diff/range/context
- Local git diff against a base branch
- Pasted patch/diff

If reviewing local changes and the caller did not supply a range:

```bash
git status --short
gh pr view --json baseRefName,headRefName 2>/dev/null
git merge-base HEAD main  # or master / PR base when applicable
git diff <base-sha>...HEAD --stat
git diff <base-sha>...HEAD
```

If the base is unclear, ask once.

### 2. Load requirements/context

Prefer context supplied by the caller. Otherwise look lightly for:
- `plans/*-design.md`
- `plans/*-spec.md`
- `plans/*-structure.md`
- matching `break_spec_approved`, `spec_approved`, or `blueprint_approved` latest pointer entries when the ticket uses custom artifact locations
- Ticket/issue summary if available in the conversation
- Commit messages in the review range

If no requirements are available, say so and review against general production readiness.

### 3. Use fresh eyes when available

If the host supports subagents/delegation, dispatch the smallest reviewer set that will add signal. Prefer one reviewer for narrow diffs; for broader diffs, split into role-specific passes:
- spec compliance — checks requirements fit, scope, edge cases, and acceptance behavior
- code quality — checks correctness, tests, maintainability, and regressions

Do not pass session history. Pass only:
- What was implemented
- Requirements/plan/context
- Diff/range
- Verification already run, if known
- Optional focus areas from the caller

If no subagent mechanism is available, review in the main agent and disclose that no independent reviewer was available.

When multiple reviewer passes are used, reconcile them into one review contract before the checklist/output step: dedupe overlapping findings, preserve which pass found each issue, and mark disagreements or incomplete evidence as needs-investigation rather than silently collapsing them.

### 4. Review checklist

Check:
- Correctness and likely bugs
- Requirements fit and scope creep
- Edge cases and error handling
- Test coverage and test quality
- Maintainability and architecture
- Security, privacy, and data integrity risks
- Migration/backward compatibility risks when relevant

If the caller gives focus areas, emphasize them without ignoring obvious correctness issues.

### 5. Output findings and stop

Use the output contract below. Do not fix findings. Return control to the caller.

## Review Modes

The review contract is intentionally reusable across workflows, but the primitive stays side-effect-free in every mode:

- **Standard local review** — inspect the current diff against requirements and identify correctness, test, security, maintainability, and compatibility issues.
- **Fresh-eyes reuse** — a caller may ask for a whole-diff final pass focused on cross-file consistency, config drift, stale docs, pagination/limits, unused code, baseline compatibility, and issues iterative fixes may have missed. Prefer the dedicated `fresh-eyes` skill for this posture.
- **Rinse reuse** — `rinse` may call `review`, apply user-approved fixes itself, verify, and rerun `review`. `review` never participates in the fix loop.
- **PR patrol reuse** — `pr-patrol` may fetch remote PR diffs, call this contract, ask which findings to post, and post only after approval. `review` never posts comments.
- **External reviewer reuse** — external reviewers may use the prompt template below, but must return the same contract and must not edit code or perform side effects.

## Review Contract

This is the Review report shape from `artifact-templates.md`; keep it terse and evidence-focused.

Severity semantics:
- **Critical** — must fix before PR handoff. Security, data loss, broken core behavior, or high-confidence production breakage.
- **Important** — should fix before PR handoff unless the user explicitly accepts the risk.
- **Minor** — optional improvement, polish, or low-risk test/documentation gap.

Each finding must include:
- Stable ID (`R1`, `R2`, ...)
- File/line when available
- Confidence (`high`, `medium`, `low`)
- Issue
- Evidence
- Why it matters
- Suggested fix
- Verification suggestion

Output exactly these sections:

```md
### Review Metadata
- Input: local diff / supplied diff / pasted patch
- Base: <sha/branch if known>
- Head: <sha/branch if known>
- Requirements: <source or "not available">
- Independent reviewer: yes/no

### Strengths
- ...

### Findings

#### Critical
##### R1: <short title>
- File: <path:line or unavailable>
- Confidence: high/medium/low
- Issue: ...
- Evidence: ...
- Why it matters: ...
- Suggested fix: ...
- Verification: ...

#### Important
...

#### Minor
...

### Caller Handoff
- Blocking findings: <IDs or none>
- Optional findings: <IDs or none>
- Suggested next action: ...

### Verdict
Ready to merge: Yes / With fixes / No
Reason: ...
```

If a severity bucket has no findings, write `None.` under that heading.

## Reusable Reviewer Prompt Template

Callers that orchestrate external reviewers (for example a future `rinse` using Codex/Gemini, or a PR patrol workflow reviewing remote PRs) can reuse this prompt contract:

```md
You are an independent reviewer using the review contract.

Review the supplied diff against the supplied requirements/context. Return only Beislið review output format:
- Review Metadata
- Strengths
- Findings grouped by Critical / Important / Minor
- Caller Handoff
- Verdict

Rules:
- Do not edit code.
- Do not post comments.
- Do not invent requirements.
- Prefer concrete findings with file/line evidence.
- Do not mark style-only nits as Critical or Important.
- If requirements are missing, say so and review against production readiness.

Context:
<requirements, implementation summary, verification, focus areas>

Diff:
<diff or patch>
```

## Composition rules

- `ready-for-review` may block PR creation on Critical/Important findings and may run `fresh-eyes` after the normal review loop.
- `fresh-eyes` may reuse the contract for a side-effect-free whole-diff final pass.
- `rinse` may call multiple reviewers using this contract, consolidate findings, fix, verify, and rerun.
- `pr-patrol` may fetch a PR, call this contract, ask the user which findings to post, and handle inline comments.
- `review` itself never owns those side effects.
