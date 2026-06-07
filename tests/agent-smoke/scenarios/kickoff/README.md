# kickoff agent smoke scenario

This scenario verifies a verbose kickoff flow against a local fixture repo.

It configures mocked CLI capabilities:

- `gh issue view 123 ...` returns a fixed issue.
- `lifecycle-action 123 123 123-kickoff-smoke kickoff_start` records the `kickoff_start` lifecycle action and validates placeholder substitution.
- `ticket-comment 123 {body_file}` records the ticket update and fails unless the body is passed by file path.

The verifier checks ticket fetch, lifecycle-action execution, temp-file ticket update posting, step 1-8 evidence, codebase exploration, `scope_classification.kind: single_pr` with blueprint routing, and implement handoff evidence.
