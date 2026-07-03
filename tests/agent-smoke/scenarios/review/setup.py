#!/usr/bin/env python3
"""Create a local review smoke fixture: a branch diff with a real regression."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, setup_main, tracked_hashes, write

BRANCH = "wid-10-review-smoke"


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    repo = init_plain_repo(run_dir, name="Beislid Review Smoke", email="review-smoke@example.invalid")

    write(repo / "src" / "discount.py", """def apply_discount(price, percent):
    return price - (price * percent / 100)
""")
    write(repo / "tests" / "test_discount.py", """from src.discount import apply_discount


def test_apply_discount_ten_percent():
    assert apply_discount(100, 10) == 90
""")
    write(repo / "README.md", "# Review smoke fixture\n\nDiscount code lives in `src/discount.py`.\n")
    commit_only(repo, "Initial discount fixture")
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "checkout", "-b", BRANCH], cwd=repo)

    # Regression: drops the /100 scaling. tests/test_discount.py, unchanged on this
    # branch, would fail against this code (100 - 100*10 == -900, not 90).
    write(repo / "src" / "discount.py", """def apply_discount(price, percent):
    return price - (price * percent)
""")
    commit_only(repo, "Simplify discount math", paths=["src/discount.py"])

    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "branch": BRANCH,
        "base_branch": "main",
        "head_sha": run(["git", "rev-parse", "HEAD"], cwd=repo),
        "tracked_files": run(["git", "ls-files"], cwd=repo).splitlines(),
        "tracked_hashes": tracked_hashes(repo),
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
        },
        "path_prepend": [],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-review-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
