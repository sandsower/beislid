#!/usr/bin/env python3
"""Create a local bootstrap-route smoke fixture."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path



def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_fixture(run_dir: Path) -> dict[str, object]:
    repo = run_dir / "repo"
    state_dir = run_dir / "state"

    run(["git", "init", str(repo)])
    run(["git", "config", "user.email", "bootstrap-route-smoke@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Beislid Bootstrap Route Smoke"], cwd=repo)

    write(repo / "AGENTS.md", """# Beislið bootstrap guidance

## Agent skills

This repo uses [Beislið](https://github.com/sandsower/beislid) for orchestrator skills.

- Read `.beislid/workflow.md` first.
- Existing ticket or branch → `kickoff`
- Clear requirements, implementation still undecided → `blueprint`
- Work is done but not yet proven → `verify`
- Branch is ready for PR → `ready-for-review`
- Use direct skill invocation when the right entry point is already obvious.
- Run `/setup` when the repo workflow config is missing or needs updating.

- Project config: `.beislid/workflow.md`
- Audit setup: `/doctor`
- Configure: `/setup`
""")
    write(repo / ".beislid" / "workflow.md", """<!-- beislid-workflow: v1 -->

# Bootstrap route smoke workflow

## Issue tracker

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json title,body'
id_pattern: '^#?\\d+$'
```

```beislid:branch_pattern
^(\\d+)-
```

## PR target

```beislid:pr_base.default
main
```

## Probe cache

```beislid:probe_cache
ttl_hours: 1
```
""")
    write(repo / "README.md", "# Bootstrap route smoke fixture\n\nAGENTS.md points fresh sessions at the right Beislið entry point.\n")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "Initial bootstrap route smoke fixture"], cwd=repo)
    run(["git", "checkout", "-b", "123-bootstrap-route"], cwd=repo)

    metadata: dict[str, object] = {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "branch": "123-bootstrap-route",
        "expected_step": "kickoff",
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
        },
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
        run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-bootstrap-route-{stamp}-"))
    print(json.dumps(create_fixture(run_dir), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
