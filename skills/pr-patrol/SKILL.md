---
name: pr-patrol
description: "Use when the user wants to review someone else's PR, says 'review this PR', 'look at this PR', 'check this PR', shares a PR URL with review intent, or asks to post PR review comments. Fetches the PR diff, runs the review contract, drafts safe comments, and posts only after approval."
---

# PR Patrol

## Project guidance preflight

If `.beislid/workflow.md` has `beislid:skill_guidance`, load `all` and `pr-patrol` guidance before proceeding; stop on missing/empty `must-read`; report loaded/missing.

Review someone else's pull request and optionally post approved review comments. This is an inbound review workflow built around the side-effect-free `review` contract.

Boundary:
- `review` inspects a diff and returns findings.
- `pr-patrol` fetches PR context, decides with the user which findings are worth posting, drafts comments, and performs posting side effects only after approval.

Use this for:
- Reviewing another person's GitHub/GitLab/etc. PR
- Turning review-contract findings into human-approved PR comments
- Running a fresh-eyes pass on a remote PR before posting comments
- Security-sensitive inbound reviews where multiple reviewers may be worth the cost

Do not use this for:
- Reviewing your own local diff before PR handoff — use `review`, `fresh-eyes`, or `ready-for-review`
- Addressing feedback on your own PR — use `review-response`
- Interactive walkthroughs of your own changes — use `walk-the-diff`
- Posting comments without explicit user approval

## Preflight

Before touching external systems, establish capabilities and print them to the user.

Resolve:
- PR URL or host/owner/repo/number. **If the user did not supply one, default to the PR for the current branch** — try `gh pr view --json number,url,author,headRefName,state` (or the host equivalent) before asking. Only prompt the user if no PR is associated with the current branch, or if the current branch's author is the user themselves (pr-patrol is for inbound review, not your own PRs).
- PR host tooling available in this session (`gh`, `glab`, MCP tool, API client, or paste-only)
- Whether inline comments are supported by the available tool
- Whether the user wants comment drafts only or actual posting

Example capability table:

```text
pr-patrol preflight
  pr:              <url>
  host:            github / gitlab / other / paste
  fetch_diff:      gh / glab / mcp / paste        ✓
  inline_comments: yes/no                         ✓
  post_comments:   yes/no                         ✓
```

If required tooling is missing, offer:

```text
(a) load/fix tooling and retry
(b) continue in draft-only mode
(c) abort
```

Do not post anything unless posting is explicitly available and the user approves the final drafts.

## Checklist

Complete these phases in order:

1. Fetch PR metadata and diff
2. Load requirements/context
3. Run the review contract
4. Select findings to post
5. Draft comments
6. Post approved comments, or print drafts
7. Summarize review outcome

## Phase 1: Fetch PR metadata and diff

Accept a PR URL or host-specific identifier. Prefer host tooling when available.

For GitHub with `gh` available:

```bash
gh pr view <url-or-number> --json title,body,author,baseRefName,headRefName,url,files
mkdir -p "${TMPDIR:-/tmp}/beislid-pr-patrol"
gh pr diff <url-or-number> > "${TMPDIR:-/tmp}/beislid-pr-patrol/pr.diff"
```

For other hosts, use the configured MCP/tooling or ask the user to paste:
- PR title
- PR description
- Base/head branches
- Diff or patch
- Any relevant ticket/spec context

If the PR is too large for one review pass, split by logical area and say how findings will be grouped. Do not silently ignore files.

## Phase 2: Load requirements/context

Use, in order:
- PR title and description
- Linked issue/ticket/spec in the PR body
- Caller-provided focus areas
- Commit messages if available
- General production readiness if requirements are missing

If requirements are unavailable, say so in the review metadata.

## Phase 3: Run review

Invoke the `review` contract with:
- PR metadata
- Requirements/context
- Full diff or scoped diff chunk
- Focus areas from the user

For large PRs, run one overall pass plus scoped passes by subsystem when possible.

For security-sensitive PRs — auth, permissions, token handling, crypto, secrets, privacy, or data export — offer multi-reviewer mode if the host can call additional independent reviewers. All reviewers must return the same review contract and must not post comments.

Optional: run `fresh-eyes` after the normal review for whole-diff drift, especially on large PRs.

## Phase 4: Select findings to post

Show findings grouped by severity. Recommend posting:
- Critical findings
- Important findings with concrete evidence and a clear requested change
- Minor findings only when they are actionable and worth reviewer attention

Ask the user which findings to post:

```text
Which findings should I post?
(a) all Critical + Important
(b) only selected IDs: <IDs>
(c) draft comments only; do not post
(d) none; summarize locally
```

Do not post style-only nits unless the user explicitly selects them.

## Phase 5: Draft comments

Convert selected findings into concise PR comments. Each comment should include:
- The issue
- The evidence
- Why it matters
- A concrete suggested fix

Tone:
- Direct, specific, and kind
- No performative hedging
- No accusations
- No generic AI phrasing

When inline comments are supported, map each finding to a file/path/line. If line mapping is unavailable, use a general PR review comment with file references.

### Safe comment body handling

Use temporary files for comment bodies. Do not inline large comment text in shell commands. This avoids shell quoting bugs and credential-guard false positives.

Example pattern:

```bash
comment_file="$(mktemp "${TMPDIR:-/tmp}/beislid-pr-comment.XXXXXX.md")"
$EDITOR "$comment_file"  # or write the approved body through the host agent's file tool
# Pass the file as a body field if the host tool supports file-backed fields.
# Otherwise build a JSON payload file and pass that file to the API client.
rm -f "$comment_file"
```

If the host/API requires a JSON payload, write JSON to a temp file and pass the payload file path to the tool instead of embedding the body in the command string. Do not pass a raw Markdown body file to an API option that expects JSON.

## Phase 6: Approval gate and posting

Present all drafts before posting:

```md
### Comment Drafts
#### P1 -> <path:line or general>
<body>
...
```

Ask for explicit approval:

```text
Post these comments? yes/no/edit
```

- On **yes**: post only the approved comments.
- On **edit**: update drafts, then ask again.
- On **no**: do not post; print the drafts for manual use if requested.

For GitHub, prefer host-supported review APIs. If the exact inline position cannot be resolved safely, fall back to a general PR review comment rather than guessing an inline location.

## Phase 7: Summarize

End with:

```md
### PR Patrol Summary
- PR: <url>
- Requirements: <source or not available>
- Reviewers used: local / external names if any
- Findings found: Critical N, Important N, Minor N
- Comments posted: N
- Draft-only comments: N
- Not posted: <IDs and reason>
- Suggested review verdict: approve / comment / request changes
```

## Common mistakes

- **Posting without approval** — every comment needs explicit user approval.
- **Letting review post comments** — `review` is side-effect-free. `pr-patrol` owns posting.
- **Shell-inlining comment bodies** — use temp files for comment bodies and JSON payloads.
- **Guessing inline positions** — fall back to general comments when mapping is uncertain.
- **Overposting minor nits** — inbound review should be high signal.
- **Hardcoding one tenant or repo host** — prefer host-agnostic wording; use `gh` examples only as examples.
