---
name: fresh-eyes
description: "Use when the user asks for 'fresh eyes', 'one last review', 'final review pass', 'whole diff review', or a post-fix pre-PR review. Runs a side-effect-free final whole-diff pass for cross-file consistency, config drift, stale docs, limits, baseline compatibility, and issues iterative review can miss."
---

# Fresh Eyes

Run a final whole-diff review pass with no session-history bias. This is a side-effect-free review primitive that uses the same output contract as `review`, but with a different posture: look across the entire change set after the obvious iterative fixes are done.

`fresh-eyes` may read files, inspect diffs, and classify findings. It must not edit files, commit, push, post comments, update tickets, create PRs, or run a fix loop. Callers decide what to do with the findings.

Use this for:
- Final pre-PR review from `ready-for-review` after the normal `review` loop
- A last-pass review after `rinse` has applied iterative fixes
- Checking a supplied patch for cross-file consistency and drift
- Catching baseline issues that hunk-by-hunk review missed

If the repo declares custom lifecycle hooks, read `../lifecycle-hooks.md` and honor any phase-boundary hooks before and after fresh-eyes.

Do not use this for:
- The first local diff review — use `review`
- Interactive walkthroughs — use `walk-the-diff`
- Fixing review findings — return findings to the caller
- Posting PR comments — use `pr-patrol`

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

### 2. Load compact context only

Prefer context supplied by the caller:
- What changed and why
- Ticket/spec/design summary
- Verification already run
- Previous review findings that were fixed or accepted
- matching `break_spec_approved`, `spec_approved`, or `blueprint_approved` latest pointer entries when the ticket uses custom artifact locations

Do not rely on long conversation history. If context is missing, say so and review against general production readiness.

### 3. Review the whole change set

Read the diff as a completed unit, not as a sequence of local fixes. Look for mismatches across files and lifecycle gaps introduced by incremental work.

Check especially:
- Cross-file naming, data-shape, API, and behavior consistency
- Environment variable, feature flag, config, and documentation drift
- Pagination, limits, ordering, retries, timeouts, and default values
- Backward compatibility, migrations, rollbacks, and baseline behavior
- Error handling consistency across all call sites
- Security, permission, token, privacy, and data-integrity boundary drift
- Stale README, docs, comments, examples, screenshots, and release notes
- Unused imports, dead helpers, orphaned tests, and leftover debug code
- Test blind spots created by repeated small fixes
- Interactions between generated files, lockfiles, schema files, and runtime code

If the caller gives focus areas, emphasize them without ignoring obvious correctness issues.

### 4. Prefer high-signal findings

Because this is a final pass, avoid style-only churn unless it hides a real bug or maintainability risk. Prefer issues that would surprise a maintainer or reviewer looking at the whole PR.

### 5. Output findings and stop

Use the same Review Contract as `review`. Do not fix findings. Return control to the caller.

## Review Contract

This is the Fresh-eyes report shape from `artifact-templates.md`; keep it terse and evidence-focused.

Severity semantics:
- **Critical** — must fix before PR handoff. Security, data loss, broken core behavior, or high-confidence production breakage.
- **Important** — should fix before PR handoff unless the user explicitly accepts the risk.
- **Minor** — optional improvement, polish, or low-risk test/documentation gap.

Each finding must include:
- Stable ID (`FE1`, `FE2`, ...)
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
- Fresh-eyes posture: whole-diff final pass

### Strengths
- ...

### Findings

#### Critical
##### FE1: <short title>
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

## Composition rules

- `ready-for-review` may run `review` first, fix/accept blocking findings, then run `fresh-eyes` as the final whole-diff gate.
- `rinse` may run `fresh-eyes` after iterative review/fix/verify loops converge.
- `pr-patrol` may reuse the fresh-eyes checklist for large or security-sensitive inbound PRs.
- `fresh-eyes` itself never owns side effects.
