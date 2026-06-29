# review-response no-source agent smoke scenario

This regression verifies the source boundary for PR review feedback.

The fixture creates a branch with an existing mocked PR. The workflow has no `pr_review_source`. Expected behavior:

- `gh pr view --json url,number,baseRefName,headRefName` may run for PR identity detection.
- No `gh api`, `gh pr view --comments`, `gh pr view --json comments,reviews`, or other review-fetch command may run.
- The agent stops in Phase 1 and asks for strict pasted PR review feedback.
- Phase 2/3 are not loaded; no files are edited, committed, pushed, or replied to.

```bash
python3 tests/agent-smoke/run.py review-response-no-source --host codex
python3 tests/agent-smoke/run.py gate review-response-no-source --hosts codex --timeout 900
```
