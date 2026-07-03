#!/usr/bin/env python3
"""Create a local kickoff smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import (
    commit_and_push,
    init_fixture_repo,
    run,
    setup_main,
    write,
    write_gh_mock,
    write_lifecycle_action_mock,
    write_file_relay_mock,
    write_workflow,
)


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    skills_dir = run_dir / "skills"
    gh_log = run_dir / "gh.log"
    comment_log = run_dir / "ticket-comment.log"
    comment_body = run_dir / "ticket-comment-body.md"
    lifecycle_action_log = run_dir / "lifecycle-action.log"

    write(skills_dir / "kickoff-smoke-explorer" / "SKILL.md", """---
name: kickoff-smoke-explorer
description: Smoke-only kickoff explore enhancer.
---

# Kickoff smoke explorer

Return this exact context marker when used: skill-only-context-token-44.
Confirm the fixture remains a single PR.
""")

    write_gh_mock(mock_bin / "gh", routes=[
        {
            "match": "issue view",
            "validate": (
                '  id=${3:-}\n'
                '  if [[ "$id" != "123" && "$id" != "#123" ]]; then\n'
                '    echo "mock gh: expected issue 123, got $id" >&2\n'
                '    exit 44\n'
                '  fi'
            ),
            "response": (
                '{"number":123,"title":"Add activity summary filters",'
                '"body":"Users need a small filter control on the activity summary so they can switch '
                'between all, open, and archived items. Acceptance criteria: reuse the existing summary '
                'renderer; add tests for filter behavior; keep the change in one PR.",'
                '"state":"OPEN","labels":[{"name":"enhancement"},{"name":"frontend"}]}'
            ),
        },
    ])
    write_lifecycle_action_mock(
        mock_bin / "lifecycle-action",
        expected_args=["123", "123", "123-kickoff-smoke", "kickoff_start"],
        usage="<ticket_id> <id_alias> <branch> <event>",
        success_message="ok: lifecycle action ran",
    )
    write_file_relay_mock(
        mock_bin / "ticket-comment",
        log_env="TICKET_COMMENT_LOG",
        out_env="TICKET_COMMENT_BODY_COPY",
        expected_leading_args=["123"],
        success_message="ok: ticket comment posted for 123",
        command_name="ticket-comment",
    )

    origin, repo = init_fixture_repo(run_dir, name="Beislid Kickoff Smoke", email="kickoff-smoke@example.invalid")

    write_workflow(repo, """<!-- beislid-workflow: v1 -->

# Kickoff smoke workflow

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json number,title,body,state,labels'
id_pattern: '^#?\\d+$'
```

```beislid:branch_pattern
^(\\d+)-
```

```beislid:ticket_update
type: cli
comment_command: 'ticket-comment {id} {body_file}'
```

```beislid:lifecycle_actions
events:
  kickoff_start:
    actions:
      - name: smoke-start-work
        type: cli
        command: 'lifecycle-action {ticket_id} {id} {branch} {event}'
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
    commit_and_push(repo, "Initial kickoff smoke fixture")
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
    return metadata


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-kickoff-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
