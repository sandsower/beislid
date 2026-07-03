#!/usr/bin/env python3
"""Create a local no-network fixture for host-agent ready-for-review smoke runs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_and_push, commit_only, init_fixture_repo, install_static_mock_bin, run, setup_main, write, write_workflow

SCENARIO_DIR = Path(__file__).resolve().parent


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    mock_bin = run_dir / "mock-bin"
    gh_log = run_dir / "gh.log"

    # This gh fake does dynamic --flag parsing and a side-effect file write for
    # `pr create`, which doesn't fit the declarative route tables cleanly - kept
    # as a static mock-bin script (see scenarios/ready-for-review/mock-bin/gh).
    install_static_mock_bin(SCENARIO_DIR, mock_bin, ["gh"])

    origin, repo = init_fixture_repo(run_dir, name="Beislid Agent Smoke", email="agent-smoke@example.invalid")

    write_workflow(repo, """<!-- beislid-workflow: v1 -->

# Agent smoke workflow

```beislid:ticket_source
type: cli
command: 'gh issue view {id} --json number,title,body,state,labels'
id_pattern: '^#?\\d+$'
```

```beislid:gate_sets
sets:
  docs:
    gates:
      - name: validate-fixture
        command: 'python3 scripts/validate_fixture.py'
        parallel_safe: true
  skills:
    gates:
      - name: validate-skills-area
        command: 'python3 scripts/validate_skills_area.py'
        parallel_safe: true
  workflows:
    gates:
      - name: workflows-should-skip
        command: 'python3 scripts/workflows_should_skip.py'
        parallel_safe: true
selectors:
  - name: docs-files
    paths: ['docs/**']
    gate_sets: ['docs']
  - name: skill-files
    paths: ['skills/**', '.beislid/**']
    gate_sets: ['skills']
  - name: workflow-files
    paths: ['.github/**']
    gate_sets: ['workflows']
```

```beislid:fresh_eyes
type: command
command: 'python3 scripts/fresh_eyes_check.py "$FRESH_EYES_LOG"'
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
    write(repo / "scripts" / "validate_skills_area.py", """#!/usr/bin/env python3
from pathlib import Path
assert Path('skills/example/SKILL.md').exists(), 'skills example missing'
print('ok: skills area validated')
""")
    os.chmod(repo / "scripts" / "validate_skills_area.py", 0o755)
    write(repo / "scripts" / "workflows_should_skip.py", """#!/usr/bin/env python3
from pathlib import Path
assert Path('.github/workflows/validate.yml').exists(), 'workflow file missing'
print('ok: workflow gate validated')
""")
    os.chmod(repo / "scripts" / "workflows_should_skip.py", 0o755)
    write(repo / ".github" / "workflows" / "validate.yml", """name: Validate Fixture
on:
  push:
    branches: [main]
  pull_request:

jobs:
  placeholder:
    runs-on: ubuntu-latest
    steps:
      - run: echo 'fixture workflow change'
""")
    write(repo / "scripts" / "fresh_eyes_check.py", """#!/usr/bin/env python3
import os
import sys
from pathlib import Path
log = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ['FRESH_EYES_LOG'])
log.parent.mkdir(parents=True, exist_ok=True)
log.write_text('fresh_eyes.command invoked\\n', encoding='utf-8')
gh_log = os.environ.get('GH_MOCK_LOG')
if gh_log:
    with Path(gh_log).open('a', encoding='utf-8') as fh:
        fh.write('fresh_eyes.command invoked\\n')
print('ok: fresh_eyes command final-check passed')
""")
    os.chmod(repo / "scripts" / "fresh_eyes_check.py", 0o755)
    write(repo / "docs" / "smoke.md", "# Smoke fixture\n\nInitial text.\n")
    write(repo / "skills" / "example" / "SKILL.md", """---
name: example
description: Fixture skill for changed-file gate-set smoke.
---

# Example fixture skill

Initial text.
""")
    commit_and_push(repo, "Initial smoke fixture")

    branch = "agent-smoke/no-ticket-verbose"
    run(["git", "checkout", "-b", branch], cwd=repo)
    write(repo / "docs" / "smoke.md", "# Smoke fixture\n\nInitial text.\n\nVerbose no-ticket ready-for-review smoke change.\n")
    write(repo / "skills" / "example" / "SKILL.md", """---
name: example
description: Fixture skill for changed-file gate-set smoke.
---

# Example fixture skill

Initial text.

Skill-area smoke change.
""")
    write(repo / ".github" / "workflows" / "validate.yml", """name: Validate Fixture
on:
  push:
    branches: [main]
  pull_request:

jobs:
  placeholder:
    runs-on: ubuntu-latest
    steps:
      - run: echo 'fixture workflow change on branch'
""")
    commit_only(repo, "Update smoke fixture docs, skills, and workflows", paths=["docs/smoke.md", "skills/example/SKILL.md", ".github/workflows/validate.yml"])

    evidence_helper = SCENARIO_DIR / "evidence_helper.py"
    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "gh_log": str(gh_log),
        "fresh_eyes_log": str(run_dir / "fresh-eyes.log"),
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
            "FRESH_EYES_LOG": str(run_dir / "fresh-eyes.log"),
        },
        "path_prepend": [str(mock_bin)],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-ready-for-review-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
