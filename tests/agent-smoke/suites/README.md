# Agent smoke suites

Suites group related smoke scenarios under one gate command.

Example:

```bash
python3 tests/agent-smoke/run.py gate --suite walk-the-diff-suite --hosts codex
```

Current suite coverage:

- `review-response-suite`: runs `review-response` followed by `review-response-no-source`
- `walk-the-diff-suite`: runs `walk-the-diff` followed by `walk-the-diff-wrap`
