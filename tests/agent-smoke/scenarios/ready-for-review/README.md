# ready-for-review agent smoke scenario

This scenario verifies verbose no-ticket fast-path behavior against a local fixture repo.

It is normally launched through the generic harness:

```bash
python3 tests/agent-smoke/run.py ready-for-review --host codex
# Claude support is temporarily unavailable for this gate.
```

The harness creates a temp fixture, points the selected host's Beislið skill symlinks at the worktree under test, opens a terminal, and prints the prompt for the child agent.

## What this checks

- `BEISLID_VERBOSE=1` and `BEISLID_MEMENTO_CAPTURE=1` are set.
- `READY_FOR_REVIEW_SMOKE_EVIDENCE_HELPER` points at `evidence_helper.py`, a scenario-local helper for transcript and memory-marker evidence. It is smoke-only, not part of the portable `ready-for-review` runtime contract.
- The fixture uses a local bare `origin`, not GitHub.
- `gh` is a mock placed first in `PATH`.
- `gh pr create` must be run through the mock on `PATH`; simulating PR creation or inventing a `smoke://` URL fails verification. It also fails unless exact `--head <branch>` is supplied.
- Any issue lookup/list command fails; no-ticket flow must not guess an issue.
- The small fixture should take the fast path: preload all ready-for-review aux files, batch safe gates when possible, and use the configured `fresh_eyes` command replacement for combined review/final-check evidence.
- If a smoke failure is clearly a verifier issue, fix it once and then record whether reduced coverage should be accepted rather than looping indefinitely.
- The verifier checks mock `gh` calls, exact `--head`, repo cwd, local-origin push, transcript/stamp evidence, `evidence.json`, fake PR URL, fast-path evidence, gate evidence, configured `fresh_eyes` command invocation, no issue guessing, no duplicate visible PR approval prompts, and exactly one structured memory marker with key fields (`kind: ready-for-review-session-memory-v1`, branch, base, ticket `none`, PR URL, transcript, and loaded aux files).

This is not a network sandbox: an agent could still run unrelated tools such as `curl` or an absolute-path `gh`. It is a no-network fixture for expected ready-for-review commands, not a security boundary.

This smoke does not replace real dogfood. It catches protocol drift before real PR flows.
