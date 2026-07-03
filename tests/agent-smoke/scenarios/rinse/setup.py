#!/usr/bin/env python3
"""Create a local rinse smoke fixture: a real regression plus a real gate script.

The precondition rinse actually needs is "review findings exist" - since the
side-effect-free `review` primitive never persists findings to disk, the
smallest artifact that satisfies that precondition is just a deterministic,
real bug in the diff (exactly like the `review` scenario's fixture) rather
than a fabricated review-report file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, setup_main, write, write_workflow

BRANCH = "wid-11-rinse-smoke"


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    repo = init_plain_repo(run_dir, name="Beislid Rinse Smoke", email="rinse-smoke@example.invalid")

    write_workflow(repo, """<!-- beislid-workflow: v1 -->

# Rinse smoke workflow

## Quality gates

```beislid:gates
- name: check-discount
  command: 'python3 scripts/check_discount.py'
  parallel_safe: true
  mutates: false
  cost: cheap
```

## Probe cache

```beislid:probe_cache
ttl_hours: 1
```
""")
    write(repo / "src" / "discount.py", """def apply_discount(price, percent):
    return price - (price * percent / 100)
""")
    write(repo / "scripts" / "check_discount.py", """#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.discount import apply_discount

assert apply_discount(100, 10) == 90, "apply_discount(100, 10) must be 90"
print("ok: check-discount passed")
""")
    os.chmod(repo / "scripts" / "check_discount.py", 0o755)
    write(repo / "README.md", "# Rinse smoke fixture\n\nDiscount code lives in `src/discount.py`; gate script in `scripts/check_discount.py`.\n")
    write(repo / ".gitignore", "__pycache__/\n*.pyc\n")
    commit_only(repo, "Initial discount fixture")
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "checkout", "-b", BRANCH], cwd=repo)

    # Regression: drops the /100 scaling. scripts/check_discount.py currently fails
    # against this code.
    write(repo / "src" / "discount.py", """def apply_discount(price, percent):
    return price - (price * percent)
""")
    commit_only(repo, "Simplify discount math", paths=["src/discount.py"])
    regressed_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "branch": BRANCH,
        "base_branch": "main",
        "regressed_head": regressed_head,
        "gate_command": ["python3", "scripts/check_discount.py"],
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
        },
        "path_prepend": [],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-rinse-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
