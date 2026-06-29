#!/usr/bin/env python3
"""Create a review-response fixture with PR detection but no pr_review_source."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    gh_log = run_dir / "gh.log"
    origin = run_dir / "origin.git"
    repo = run_dir / "repo"

    mock_bin.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCENARIO_DIR / "mock-bin" / "gh", mock_bin / "gh")
    os.chmod(mock_bin / "gh", 0o755)

    run(["git", "init", "--bare", str(origin)])
    run(["git", "clone", str(origin), str(repo)])
    run(["git", "config", "user.email", "review-response-no-source@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Beislid Review Response No Source Smoke"], cwd=repo)

    write(repo / ".beislid" / "workflow.md", """<!-- beislid-workflow: v1 -->

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
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "Initial review-response no-source smoke fixture"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "push", "-u", "origin", "main"], cwd=repo)
    run(["git", "checkout", "-b", "123-review-response-no-source"], cwd=repo)
    run(["git", "push", "-u", "origin", "123-review-response-no-source"], cwd=repo)
    expected_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

    metadata: dict[str, object] = {
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
    write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    if args.run_dir:
        run_dir = Path(args.run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-review-response-no-source-smoke-{stamp}-"))
    print(json.dumps(create_fixture(run_dir), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup failed: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
