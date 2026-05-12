# walk-the-diff agent smoke scenario

This scenario verifies the default interactive pacing path for `walk-the-diff`.

It creates a feature branch with a source chunk plus later tests/docs chunk. The host agent must load Phase 1-3 aux files, gather context, plan a source-first tour, present only the first chunk with a fenced diff, show the gate options, and stop. The verifier fails if Phase 4 loads, later chunk diff-specific lines leak, or the fixture repo is modified.

Run:

```bash
python3 tests/agent-smoke/run.py gate walk-the-diff --hosts claude,codex --timeout 900
```
