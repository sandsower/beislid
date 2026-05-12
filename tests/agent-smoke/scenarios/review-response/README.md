# review-response agent smoke scenario

This scenario verifies verbose PR-review `review-response` behavior against a local fixture repo.

```bash
python3 tests/agent-smoke/run.py review-response --host codex
python3 tests/agent-smoke/run.py review-response --host claude
python3 tests/agent-smoke/run.py gate review-response --hosts claude,codex --timeout 900
```

The fixture creates a branch with an existing mocked PR. Expected external commands are provided by scenario-local mocks on `PATH`:

- `gh pr view` returns PR metadata.
- `pr-review-source summary|threads ...` returns one unresolved inline review comment.
- `pr-review-update reply {json_file}` copies the reply payload for verification.

The workflow config uses a top-level `validate-fixture` gate. The agent should treat the single comment as an approved clear fix, update `src/reply.py`, run the gate, commit, push, and post a PR reply via JSON file.

The verifier checks exact aux-load stamps after the host-output sentinel, mocked PR source/update calls, real JSON-file payload usage, source fix, commit/push, and evidence markers. The scenario is not a network sandbox; it only mocks expected external commands.
