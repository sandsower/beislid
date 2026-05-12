#!/usr/bin/env python3
"""Create a local kickoff smoke fixture."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
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
    skills_dir = run_dir / "skills"
    gh_log = run_dir / "gh.log"
    comment_log = run_dir / "ticket-comment.log"
    comment_body = run_dir / "ticket-comment-body.md"
    lifecycle_action_log = run_dir / "lifecycle-action.log"
    origin = run_dir / "origin.git"
    repo = run_dir / "repo"

    mock_bin.mkdir(parents=True, exist_ok=True)
    write(skills_dir / "kickoff-smoke-explorer" / "SKILL.md", """---
name: kickoff-smoke-explorer
description: Smoke-only kickoff explore enhancer.
---

# Kickoff smoke explorer

Return this exact context marker when used: skill-only-context-token-44.
Confirm the fixture remains a single PR.
""")
    for name in ["gh", "ticket-comment", "lifecycle-action"]:
        shutil.copy2(SCENARIO_DIR / "mock-bin" / name, mock_bin / name)
        os.chmod(mock_bin / name, 0o755)

    run(["git", "init", "--bare", str(origin)])
    run(["git", "clone", str(origin), str(repo)])
    run(["git", "config", "user.email", "kickoff-smoke@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Beislid Kickoff Smoke"], cwd=repo)

    write(repo / ".beislid" / "workflow.md", f"""<!-- beislid-workflow: v1 -->

# Kickoff smoke workflow

```beislid:ticket_source
type: cli
command: 'gh issue view {{id}} --json number,title,body,state,labels'
id_pattern: '^#?\\d+$'
```

```beislid:branch_pattern
^(\\d+)-
```

```beislid:ticket_update
type: cli
comment_command: 'ticket-comment {{id}} {{body_file}}'
```

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: smoke-start-work
        type: cli
        command: 'lifecycle-action {{ticket_id}} {{id}} {{branch}} {{event}}'
        approval: auto
```

```beislid:explore
skill: kickoff-smoke-explorer
mode: enhance
```

```beislid:probe_cache
ttl_hours: 1
```
""")
    write(repo / "src" / "summary.py", """def filter_items(items, status):
    if status == 'all':
        return items
    return [item for item in items if item['status'] == status]
""")
    write(repo / "tests" / "test_summary.py", """from src.summary import filter_items


def test_filter_items_open():
    items = [{'status': 'open'}, {'status': 'archived'}]
    assert filter_items(items, 'open') == [{'status': 'open'}]
""")
    write(repo / "README.md", "# Kickoff smoke fixture\n\nActivity summary code lives in `src/summary.py`.\n")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "Initial kickoff smoke fixture"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "push", "-u", "origin", "main"], cwd=repo)
    run(["git", "checkout", "-b", "123-kickoff-smoke"], cwd=repo)

    metadata: dict[str, object] = {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "gh_log": str(gh_log),
        "ticket_comment_log": str(comment_log),
        "ticket_comment_body": str(comment_body),
        "lifecycle_action_log": str(lifecycle_action_log),
        "origin": str(origin),
        "branch": "123-kickoff-smoke",
        "ticket_id": "123",
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
            "BEISLID_SKILLS_DIRS": str(skills_dir),
            "GH_MOCK_LOG": str(gh_log),
            "TICKET_COMMENT_LOG": str(comment_log),
            "TICKET_COMMENT_BODY_COPY": str(comment_body),
            "LIFECYCLE_ACTION_LOG": str(lifecycle_action_log),
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
        run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-kickoff-smoke-{stamp}-"))
    print(json.dumps(create_fixture(run_dir), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
