#!/usr/bin/env python3
"""Create a local envelope smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent
BEISLID_ROOT = SCENARIO_DIR.parents[3]

sys.path.insert(0, str(SCENARIO_DIR.parents[1]))

from harness.fixtures import commit_and_push, init_fixture_repo, setup_main, write, write_workflow


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"

    origin, repo = init_fixture_repo(run_dir, name="Beislid Envelope Smoke", email="envelope-smoke@example.invalid")

    write_workflow(repo, """<!-- beislid-workflow: v1 -->

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
    write(repo / "plans" / "widget-report-structure.md", """# Widget Report — Implementation Structure

Approved structure (smoke fixture). Source: smoke ticket WID-8.

## Durable Decisions
- Report builder lives in `src/widget_report.py` (new file); stdlib only.
- Input contract: the CSV produced by WID-7's `export_widgets(items, path)` in `src/widget_export.py`.

## Phase 1: Summary report from the exported CSV (AFK)
Cuts through: CSV read, aggregation, tests.
Delivers: `summarize_export(csv_path)` returning counts per status; covered by `tests/test_widget_report.py`.
Depends on: WID-7 Phase 1 — `export_widgets` CSV output is this slice's input.
""")
    write(repo / "src" / "widget_export.py", """def widgets():
    return [{"name": "alpha", "status": "open"}]
""")
    write(repo / "tests" / "test_widget_export.py", """from src.widget_export import widgets


def test_widgets_have_status():
    assert widgets()[0]["status"] == "open"
""")
    write(repo / "README.md", "# Envelope smoke fixture\n\nWidget code lives in `src/widget_export.py`.\n")
    commit_and_push(repo, "Initial envelope smoke fixture")

    metadata: dict[str, object] = {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "origin": str(origin),
        "bundle_id": "wid-7-wid-8-widget-suite",
        "beislid_root": str(BEISLID_ROOT),
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
        },
        "path_prepend": [str(BEISLID_ROOT / "bin")],
    }
    return metadata


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-envelope-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
