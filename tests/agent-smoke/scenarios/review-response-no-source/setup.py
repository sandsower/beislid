#!/usr/bin/env python3
"""Create a review-response fixture with PR detection but no pr_review_source."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_and_push, init_fixture_repo, run, setup_main, write, write_gh_mock, write_workflow


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    gh_log = run_dir / "gh.log"

    write_gh_mock(mock_bin / "gh", routes=[
        {
            "match": "pr view",
            "contains": "--json url,number,baseRefName,headRefName",
            "response": (
                '{"url":"https://example.invalid/sandsower/review-response-no-source/pull/9",'
                '"number":9,"baseRefName":"main","headRefName":"123-review-response-no-source"}'
            ),
        },
    ])

    origin, repo = init_fixture_repo(run_dir, name="Beislid Review Response No Source Smoke", email="review-response-no-source@example.invalid")

    write_workflow(repo, """<!-- beislid-workflow: v1 -->

# Review-response no-source smoke workflow

## PR target

```beislid:pr_base.default
main
```

```beislid:pr_host.owner
sandsower
```

```beislid:pr_host.repo
review-response-no-source
```

```beislid:branch_pattern
^(\\d+)-
```

## Probe cache

```beislid:probe_cache
ttl_hours: 1
```
""")
    write(repo / "README.md", "# Review-response no-source smoke fixture\n\nPR detection is available, but PR review feedback source is not configured.\n")
    commit_and_push(repo, "Initial review-response no-source smoke fixture")
    run(["git", "checkout", "-b", "123-review-response-no-source"], cwd=repo)
    run(["git", "push", "-u", "origin", "123-review-response-no-source"], cwd=repo)
    expected_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "gh_log": str(gh_log),
        "origin": str(origin),
        "branch": "123-review-response-no-source",
        "base": "main",
        "pr_number": 9,
        "expected_head": expected_head,
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
            "GH_MOCK_LOG": str(gh_log),
        },
        "path_prepend": [str(mock_bin)],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-review-response-no-source-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
