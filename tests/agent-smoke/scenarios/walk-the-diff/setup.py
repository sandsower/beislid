#!/usr/bin/env python3
"""Create a local walk-the-diff pacing smoke fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tracked_hashes(repo: Path) -> dict[str, str]:
    files = run(["git", "ls-files"], cwd=repo).splitlines()
    hashes: dict[str, str] = {}
    for rel in files:
        data = (repo / rel).read_bytes()
        hashes[rel] = hashlib.sha256(data).hexdigest()
    return hashes


def create_fixture(run_dir: Path) -> dict[str, object]:
    state_dir = run_dir / "state"
    repo = run_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", "walk-diff-smoke@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Beislid Walk Diff Smoke"], cwd=repo)

    write(repo / "src" / "calculator.py", """def subtotal(items):
    return sum(items)
""")
    write(repo / "tests" / "test_calculator.py", """from src.calculator import subtotal


def test_subtotal_adds_items():
    assert subtotal([2, 3]) == 5
""")
    write(repo / "README.md", "# Walk-the-diff smoke fixture\n\nCalculator helpers live in `src/calculator.py`.\n")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "Initial calculator fixture"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)
    run(["git", "checkout", "-b", "456-walk-diff-smoke"], cwd=repo)

    write(repo / "src" / "calculator.py", """def subtotal(items):
    return sum(items)


def add_tax(amount, tax_rate):
    return round(amount * (1 + tax_rate), 2)


def receipt_total(items, tax_rate):
    return add_tax(subtotal(items), tax_rate)
""")
    run(["git", "add", "src/calculator.py"], cwd=repo)
    run(["git", "commit", "-m", "Add taxable receipt helpers"], cwd=repo)

    write(repo / "tests" / "test_calculator.py", """from src.calculator import receipt_total, subtotal


def test_subtotal_adds_items():
    assert subtotal([2, 3]) == 5


def test_receipt_total_includes_tax():
    assert receipt_total([40, 60], 0.1) == 110.0
""")
    write(repo / "README.md", "# Walk-the-diff smoke fixture\n\nCalculator helpers live in `src/calculator.py`.\n\nTax receipts now include a smoke-covered example.\n")
    run(["git", "add", "tests/test_calculator.py", "README.md"], cwd=repo)
    run(["git", "commit", "-m", "Document and test tax receipts"], cwd=repo)

    metadata: dict[str, object] = {
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
        "first_chunk_diff_markers": ["+def add_tax", "+def receipt_total"],
        "forbidden_later_diff_markers": [
            "-from src.calculator import subtotal",
            "+from src.calculator import receipt_total, subtotal",
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
        run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-walk-diff-smoke-{stamp}-"))
    print(json.dumps(create_fixture(run_dir), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
