# walk-the-diff-wrap agent smoke scenario

This scenario verifies the full lifecycle path for `walk-the-diff`.

It creates the same style of feature branch as the default pacing scenario, then asks the host agent to use smoke-only scripted reviewer decisions to move through all chunks, load Phase 4, save a feedback doc under `BEISLID_STATE_DIR`, and stop. The verifier fails if the feedback doc is missing, appears inside the repo, or the fixture repo is modified.

Run:

```bash
python3 tests/agent-smoke/run.py gate walk-the-diff-wrap --hosts claude,codex --timeout 900
```
