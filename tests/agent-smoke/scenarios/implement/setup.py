#!/usr/bin/env python3
"""Create a local implement smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_and_push, init_fixture_repo, run, setup_main, write, write_workflow

TICKET_ID = "WID-9"
BRANCH = "wid-9-implement-smoke"
EVENT = "implementation_plan_created"
CHECKPOINT_PATH = f"checkpoints/{EVENT}-{TICKET_ID}.md"


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"

    origin, repo = init_fixture_repo(run_dir, name="Beislid Implement Smoke", email="implement-smoke@example.invalid")

    write_workflow(repo, f"""<!-- beislid-workflow: v1 -->

# Implement smoke workflow

```beislid:lifecycle_actions
events:
  {EVENT}:
    actions:
      - name: write-implementation-plan-checkpoint
        type: artifact
        approval: auto
        path: '{CHECKPOINT_PATH}'
```

```beislid:probe_cache
ttl_hours: 1
```
""")
    write(repo / "plans" / "widget-tax-design.md", """# Widget export tax design

## Status
approved

## Source Requirements
- Ticket: WID-9 - add tax to widget export CSV rows

## Recommended Approach
Add an optional `tax_rate` parameter to `export_widgets`; when given, append a
`tax_rate` column to every written row (and the header).

## Alternatives Considered
- Separate `export_widgets_with_tax` function: rejected, duplicates the writer.

## Files / Modules
- `src/widget_export.py` — add optional `tax_rate` param to `export_widgets`; when provided, write an extra `tax_rate` column on every row.
- `tests/test_widget_export.py` — add coverage for the tax_rate export path.

## Data / Control Flow
`export_widgets` builds the CSV header and rows; when `tax_rate` is not None,
extend both header and each row with the value.

## Edge Cases and Risks
- Existing no-tax-rate callers must see unchanged output.

## Verification Plan
- Add and run a test asserting the tax_rate column and value when exporting with a tax rate.

## Open Questions
- None.
""")
    write(repo / "src" / "widget_export.py", """import csv


def widgets():
    return [{"name": "alpha", "status": "open"}]


def export_widgets(items, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["name", "status"])
        for item in items:
            writer.writerow([item["name"], item["status"]])
""")
    write(repo / "tests" / "test_widget_export.py", """from src.widget_export import widgets


def test_widgets_have_status():
    assert widgets()[0]["status"] == "open"
""")
    write(repo / "README.md", "# Implement smoke fixture\n\nWidget export code lives in `src/widget_export.py`.\n")
    commit_and_push(repo, "Initial implement smoke fixture")
    run(["git", "checkout", "-b", BRANCH], cwd=repo)
    initial_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "origin": str(origin),
        "branch": BRANCH,
        "ticket_id": TICKET_ID,
        "checkpoint_path": CHECKPOINT_PATH,
        "initial_head": initial_head,
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
        },
        "path_prepend": [],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-implement-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
