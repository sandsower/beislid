#!/usr/bin/env python3
"""Create a local walk-the-diff pacing smoke fixture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, setup_main, tracked_hashes, write


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    repo = init_plain_repo(run_dir, name="Beislid Walk Diff Smoke", email="walk-diff-smoke@example.invalid")

    write(repo / "src" / "calculator.py", """def subtotal(items):
    return sum(items)
""")
    write(repo / "tests" / "test_calculator.py", """from src.calculator import subtotal


def test_subtotal_adds_items():
    assert subtotal([2, 3]) == 5
""")
    write(repo / "README.md", "# Walk-the-diff smoke fixture\n\nCalculator helpers live in `src/calculator.py`.\n")
    commit_only(repo, "Initial calculator fixture")
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "checkout", "-b", "456-walk-diff-smoke"], cwd=repo)

    write(repo / "src" / "calculator.py", """def subtotal(items):
    return sum(items)


def add_tax(amount, tax_rate):
    return round(amount * (1 + tax_rate), 2)


def receipt_total(items, tax_rate):
    return add_tax(subtotal(items), tax_rate)
""")
    commit_only(repo, "Add taxable receipt helpers", paths=["src/calculator.py"])

    write(repo / "tests" / "test_calculator.py", """from src.calculator import receipt_total, subtotal


def test_subtotal_adds_items():
    assert subtotal([2, 3]) == 5


def test_receipt_total_includes_tax():
    assert receipt_total([40, 60], 0.1) == 110.0
""")
    write(repo / "README.md", "# Walk-the-diff smoke fixture\n\nCalculator helpers live in `src/calculator.py`.\n\nTax receipts now include a smoke-covered example.\n")
    commit_only(repo, "Document and test tax receipts", paths=["tests/test_calculator.py", "README.md"])

    return {
        "run_dir": str(run_dir),
        "repo": str(repo),
        "state_dir": str(state_dir),
        "branch": "456-walk-diff-smoke",
        "base_branch": "main",
        "head_sha": run(["git", "rev-parse", "HEAD"], cwd=repo),
        "tracked_files": run(["git", "ls-files"], cwd=repo).splitlines(),
        "tracked_hashes": tracked_hashes(repo),
        "first_chunk_file": "src/calculator.py",
        "first_chunk_markers": ["src/calculator.py", "add_tax", "receipt_total"],
        "forbidden_later_diff_markers": [
            "def test_receipt_total_includes_tax",
            "assert receipt_total([40, 60], 0.1) == 110.0",
            "Tax receipts now include a smoke-covered example.",
        ],
        "env": {
            "BEISLID_VERBOSE": "1",
            "BEISLID_STATE_DIR": str(state_dir),
        },
        "path_prepend": [],
    }


def main() -> int:
    return setup_main(create_fixture, prefix="beislid-walk-diff-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
