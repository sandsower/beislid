#!/usr/bin/env python3
"""Verify a host-agent rinse smoke run."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, write, write_workflow
from harness.verification import collect_agent_output, fail

REQUIRED_SUMMARY_FIELDS = [
    "Input",
    "Iterations run",
    "Findings fixed",
    "Findings accepted/pushed back",
    "Verification run",
    "Fresh-eyes run",
    "Remaining risk",
    "Suggested next action",
]


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    repo = Path(metadata["repo"])
    regressed_head = metadata["regressed_head"]
    gate_command = metadata["gate_command"]

    head = run(["git", "-C", str(repo), "rev-parse", "HEAD"])
    if head == regressed_head:
        fail(errors, "product", "no fix commit was made after the regressed commit")

    # The real product check: actually run the configured gate against whatever
    # the agent left in the tree, and require it to pass for real - not a claim
    # in the transcript.
    gate_result = subprocess.run(gate_command, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if gate_result.returncode != 0:
        fail(errors, "product", f"configured gate {' '.join(gate_command)} failed (exit {gate_result.returncode}):\n{gate_result.stdout}")

    status = run(["git", "-C", str(repo), "status", "--short"])
    if status.strip():
        fail(errors, "product", f"fixture repo left dirty after rinse: {status}")

    output = collect_agent_output(run_dir, strip_tokens=True)
    if "### Rinse Summary" not in output:
        fail(errors, "product", "agent output missing the '### Rinse Summary' section")
    else:
        summary = output.split("### Rinse Summary", 1)[1]
        for field in REQUIRED_SUMMARY_FIELDS:
            if field not in summary:
                fail(errors, "product", f"Rinse Summary missing field: {field!r}")

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-rinse-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        repo = init_plain_repo(run_dir, name="Self Test", email="selftest@example.invalid")
        write_workflow(repo, "<!-- beislid-workflow: v1 -->\n\n# Rinse smoke workflow\n")
        write(repo / "src" / "discount.py", "def apply_discount(price, percent):\n    return price - (price * percent)\n")
        write(repo / "scripts" / "check_discount.py", """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.discount import apply_discount

assert apply_discount(100, 10) == 90, "apply_discount(100, 10) must be 90"
print("ok: check-discount passed")
""")
        os.chmod(repo / "scripts" / "check_discount.py", 0o755)
        write(repo / ".gitignore", "__pycache__/\n*.pyc\n")
        commit_only(repo, "Regressed fixture")
        regressed_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

        gate_command = ["python3", "scripts/check_discount.py"]
        metadata = {
            "repo": str(repo),
            "regressed_head": regressed_head,
            "gate_command": gate_command,
        }
        write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")

        summary = "\n".join([
            "=== BEISLID_AGENT_SMOKE_OUTPUT ===",
            "### Rinse Summary",
            "- Input/base/head: local diff / main / HEAD",
            "- Iterations run: 1",
            "- Findings fixed: R1 (discount scaling regression)",
            "- Findings accepted/pushed back: none",
            "- Verification run: python3 scripts/check_discount.py (passed)",
            "- Fresh-eyes run: no",
            "- Remaining risk: none",
            "- Suggested next action: ready-for-review",
            "",
        ])
        write(run_dir / "agent.log", summary)

        write(repo / "src" / "discount.py", "def apply_discount(price, percent):\n    return price - (price * percent / 100)\n")
        commit_only(repo, "Restore percent scaling", paths=["src/discount.py"])

        errors = verify(run_dir)
        if errors:
            print("self-test failed (expected pass):", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        # Negative: revert the fix (simulate a claimed-but-not-applied fix) - the
        # real gate execution must catch it even though Rinse Summary still reads
        # clean.
        write(repo / "src" / "discount.py", "def apply_discount(price, percent):\n    return price - (price * percent)\n")
        commit_only(repo, "Oops, reverted the fix", paths=["src/discount.py"])
        negative_errors = verify(run_dir)
        if not any("check_discount.py failed" in error for error in negative_errors):
            print("self-test failed: unfixed regression should fail the real gate run", file=sys.stderr)
            for error in negative_errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        print("ok: rinse verify self-test passed")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.run_dir:
        parser.error("run_dir is required unless --self-test is used")
    errors = verify(Path(args.run_dir).resolve())
    if errors:
        print("rinse smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: rinse agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
