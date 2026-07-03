#!/usr/bin/env python3
"""Create a local blueprint smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_and_push, init_fixture_repo, run, setup_main, write, write_lifecycle_action_mock, write_workflow

TICKET_ID = "WID-9"
BRANCH = "wid-9-blueprint-smoke"
EVENT = "blueprint_approved"
ARTIFACT_PATH = "plans/widget-export-design.md"


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    lifecycle_action_log = run_dir / "lifecycle-action.log"

    write_lifecycle_action_mock(
        mock_bin / "lifecycle-action",
        expected_args=[TICKET_ID, TICKET_ID, BRANCH, EVENT, ARTIFACT_PATH],
        usage="<ticket_id> <id_alias> <branch> <event> <artifact_path>",
        success_message="ok: blueprint approved hook ran",
    )

    origin, repo = init_fixture_repo(run_dir, name="Beislid Blueprint Smoke", email="blueprint-smoke@example.invalid")

    write_workflow(repo, f"""<!-- beislid-workflow: v1 -->

# Blueprint smoke workflow

```beislid:lifecycle_actions
events:
  {EVENT}:
    actions:
      - name: write-design-artifact
        type: artifact
        approval: auto
        path: '{ARTIFACT_PATH}'
      - name: run-approved-design-hook
        type: cli
        command: 'lifecycle-action {{ticket_id}} {{id}} {{branch}} {{event}} {{artifact_path}}'
        approval: auto
```

```beislid:probe_cache
ttl_hours: 1
```
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
    write(repo / "README.md", "# Blueprint smoke fixture\n\nWidget export code lives in `src/widget_export.py`.\n")
    commit_and_push(repo, "Initial blueprint smoke fixture")
    run(["git", "checkout", "-b", BRANCH], cwd=repo)

    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "origin": str(origin),
        "branch": BRANCH,
        "ticket_id": TICKET_ID,
        "artifact_path": ARTIFACT_PATH,
        "lifecycle_action_log": str(lifecycle_action_log),
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
            "LIFECYCLE_ACTION_LOG": str(lifecycle_action_log),
        },
        "path_prepend": [str(mock_bin)],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-blueprint-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
