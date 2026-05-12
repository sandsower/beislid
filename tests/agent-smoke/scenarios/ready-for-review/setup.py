#!/usr/bin/env python3
"""Create a local no-network fixture for host-agent ready-for-review smoke runs."""

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
    gh_log = run_dir / "gh.log"
    origin = run_dir / "origin.git"
    repo = run_dir / "repo"

    mock_src = SCENARIO_DIR / "mock-bin" / "gh"
    mock_bin.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mock_src, mock_bin / "gh")
    os.chmod(mock_bin / "gh", 0o755)

    run(["git", "init", "--bare", str(origin)])
    run(["git", "clone", str(origin), str(repo)])
    run(["git", "config", "user.email", "agent-smoke@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Beislid Agent Smoke"], cwd=repo)

    write(repo / ".beislid" / "workflow.md", """<!-- beislid-workflow: v1 -->

# Agent smoke workflow

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json number,title,body,state,labels'
id_pattern: '^#?\\d+$'
```

```beislid:gates
- name: validate-fixture
  command: 'python3 scripts/validate_fixture.py'
  parallel_safe: true
```

```beislid:probe_cache
ttl_hours: 1
```
""")
    write(repo / "scripts" / "validate_fixture.py", """#!/usr/bin/env python3
from pathlib import Path
assert Path('docs/smoke.md').exists(), 'docs/smoke.md missing'
print('ok: fixture validated')
""")
    os.chmod(repo / "scripts" / "validate_fixture.py", 0o755)
    write(repo / "docs" / "smoke.md", "# Smoke fixture\n\nInitial text.\n")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "Initial smoke fixture"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "push", "-u", "origin", "main"], cwd=repo)

    branch = "agent-smoke/no-ticket-verbose"
    run(["git", "checkout", "-b", branch], cwd=repo)
    write(repo / "docs" / "smoke.md", "# Smoke fixture\n\nInitial text.\n\nVerbose no-ticket ready-for-review smoke change.\n")
    run(["git", "add", "docs/smoke.md"], cwd=repo)
    run(["git", "commit", "-m", "Update smoke fixture docs"], cwd=repo)

    evidence_helper = SCENARIO_DIR / "evidence_helper.py"
    metadata: dict[str, object] = {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "gh_log": str(gh_log),
        "origin": str(origin),
        "branch": branch,
        "base": "main",
        "evidence_helper": str(evidence_helper),
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_MEMENTO_CAPTURE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
            "READY_FOR_REVIEW_SMOKE_EVIDENCE_HELPER": str(evidence_helper),
            "GH_MOCK_LOG": str(gh_log),
            "GH_MOCK_PR_URL": "https://example.invalid/beislid-smoke/pull/1",
            "GH_MOCK_EXPECT_HEAD": branch,
        },
        "path_prepend": [str(mock_bin)],
    }
    write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", help="Run directory created by the generic harness")
    args = parser.parse_args()

    if args.run_dir:
        run_dir = Path(args.run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-ready-for-review-smoke-{stamp}-"))
    metadata = create_fixture(run_dir)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
