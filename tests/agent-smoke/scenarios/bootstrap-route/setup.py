#!/usr/bin/env python3
"""Create a local bootstrap-route smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, setup_main, write, write_workflow


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"

    repo = init_plain_repo(run_dir, name="Beislid Bootstrap Route Smoke", email="bootstrap-route-smoke@example.invalid")

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
    write_workflow(repo, """<!-- beislid-workflow: v1 -->

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
    commit_only(repo, "Initial bootstrap route smoke fixture")
    run(["git", "checkout", "-b", "123-bootstrap-route"], cwd=repo)

    return {
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


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-bootstrap-route")


if __name__ == "__main__":
    raise SystemExit(main())
