#!/usr/bin/env python3
"""Create a local envelope smoke fixture."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent
BEISLID_ROOT = SCENARIO_DIR.parents[3]


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
    origin = run_dir / "origin.git"
    repo = run_dir / "repo"

    run(["git", "init", "--bare", str(origin)])
    run(["git", "clone", str(origin), str(repo)])
    run(["git", "config", "user.email", "envelope-smoke@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Beislid Envelope Smoke"], cwd=repo)

    write(repo / ".beislid" / "workflow.md", """<!-- beislid-workflow: v1 -->

# Envelope smoke workflow

## Quality gates

```beislid:gates
- name: widget-tests
  command: 'python3 -m pytest tests/'
  parallel_safe: true
  mutates: false
  cost: cheap
```

## Action policy

```beislid:action_policy
modes:
  supervised-auto:
    actions:
      export.bundle.write: allow
      checkpoint.envelope_exported: allow
      git.commit: allow
```

## Probe cache

```beislid:probe_cache
ttl_hours: 1
```
""")

    write(repo / "plans" / "widget-export-structure.md", """# Widget Export — Implementation Structure

Approved structure (smoke fixture). Source: smoke ticket WID-7.

## Durable Decisions
- CSV writer lives in `src/widget_export.py`; stdlib `csv` only.

## Phase 1: CSV export of widgets (AFK)
Cuts through: data access, CSV writer, tests.
Delivers: `export_widgets(items, path)` writing name/status rows; covered by `tests/test_widget_export.py`.
Validates: the widget data shape supports flat export.

## Phase 2: Widget export audit log (AFK)
Cuts through: audit hook in `src/widget_export.py`.
Delivers: each export appends an audit line; verified by running `frobnicate --check` against the audit output.
Validates: exports leave a verifiable audit trail.
""")
    write(repo / "src" / "widget_export.py", """def widgets():
    return [{"name": "alpha", "status": "open"}]
""")
    write(repo / "tests" / "test_widget_export.py", """from src.widget_export import widgets


def test_widgets_have_status():
    assert widgets()[0]["status"] == "open"
""")
    write(repo / "README.md", "# Envelope smoke fixture\n\nWidget code lives in `src/widget_export.py`.\n")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "Initial envelope smoke fixture"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "push", "-u", "origin", "main"], cwd=repo)

    metadata: dict[str, object] = {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "origin": str(origin),
        "bundle_id": "wid-7-widget-export",
        "beislid_root": str(BEISLID_ROOT),
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
        },
        "path_prepend": [str(BEISLID_ROOT / "bin")],
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
        run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-envelope-smoke-{stamp}-"))
    print(json.dumps(create_fixture(run_dir), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
