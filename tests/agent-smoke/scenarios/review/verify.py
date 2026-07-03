#!/usr/bin/env python3
"""Verify a host-agent review smoke run."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_only, init_plain_repo, run, tracked_hashes, write
from harness.verification import collect_agent_output, fail, require_repo_snapshot

REQUIRED_SECTIONS = [
    "### Review Metadata",
    "### Strengths",
    "### Findings",
    "#### Critical",
    "#### Important",
    "#### Minor",
    "### Caller Handoff",
    "### Verdict",
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

    # review is a side-effect-free primitive: the fixture repo must come out
    # byte-identical to how setup.py left it.
    require_repo_snapshot(
        errors,
        repo=repo,
        expected_head=metadata.get("head_sha"),
        expected_hashes=metadata.get("tracked_hashes"),
        kind="product",
        label="review fixture repo",
    )

    output = collect_agent_output(run_dir, strip_tokens=True)
    for section in REQUIRED_SECTIONS:
        if section not in output:
            fail(errors, "product", f"agent output missing Review Contract section: {section!r}")

    if not re.search(r"discount\.py", output):
        fail(errors, "product", "agent output never grounds a finding in src/discount.py")

    verdict_match = re.search(r"Ready to merge:\s*(Yes|With fixes|No)", output, re.IGNORECASE)
    if not verdict_match:
        fail(errors, "product", "agent output missing a 'Ready to merge: Yes/With fixes/No' verdict line")
    elif verdict_match.group(1).strip().lower() == "yes":
        fail(errors, "product", "verdict says 'Ready to merge: Yes' despite the real regression in apply_discount")

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-review-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        repo = init_plain_repo(run_dir, name="Self Test", email="selftest@example.invalid")
        write(repo / "src" / "discount.py", "def apply_discount(price, percent):\n    return price - (price * percent)\n")
        write(repo / "tests" / "test_discount.py", "from src.discount import apply_discount\n\n\ndef test_apply_discount_ten_percent():\n    assert apply_discount(100, 10) == 90\n")
        commit_only(repo, "Initial fixture")
        head_sha = run(["git", "rev-parse", "HEAD"], cwd=repo)
        tracked_files = run(["git", "ls-files"], cwd=repo).splitlines()
        hashes = tracked_hashes(repo)

        metadata = {
            "repo": str(repo),
            "head_sha": head_sha,
            "tracked_files": tracked_files,
            "tracked_hashes": hashes,
        }
        write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")

        good_output = "\n".join([
            "=== BEISLID_AGENT_SMOKE_OUTPUT ===",
            "### Review Metadata",
            "- Input: local diff",
            "- Requirements: not available",
            "",
            "### Strengths",
            "- Small, focused diff",
            "",
            "### Findings",
            "",
            "#### Critical",
            "##### R1: apply_discount drops percent scaling",
            "- File: src/discount.py:2",
            "- Confidence: high",
            "- Issue: percent is no longer divided by 100",
            "- Evidence: tests/test_discount.py expects 90 for a 10 percent discount on 100",
            "- Why it matters: massively over-discounts",
            "- Suggested fix: restore `/ 100`",
            "- Verification: rerun tests/test_discount.py",
            "",
            "#### Important",
            "None.",
            "",
            "#### Minor",
            "None.",
            "",
            "### Caller Handoff",
            "- Blocking findings: R1",
            "- Optional findings: none",
            "- Suggested next action: fix R1 before merge",
            "",
            "### Verdict",
            "Ready to merge: No",
            "Reason: R1 is a correctness regression.",
            "",
        ])
        write(run_dir / "agent.log", good_output)

        errors = verify(run_dir)
        if errors:
            print("self-test failed (expected pass):", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        # Negative 1: review claims ready-to-merge Yes despite the regression.
        bad_verdict = good_output.replace("Ready to merge: No", "Ready to merge: Yes")
        write(run_dir / "agent.log", bad_verdict)
        verdict_errors = verify(run_dir)
        if not any("Ready to merge: Yes" in error for error in verdict_errors):
            print("self-test failed: false-positive verdict should fail", file=sys.stderr)
            return 1
        write(run_dir / "agent.log", good_output)

        # Negative 2: review is supposed to be side-effect-free - a dirtied repo
        # (as if it had "fixed" the bug itself) must fail even with good output.
        write(repo / "src" / "discount.py", "def apply_discount(price, percent):\n    return price - (price * percent / 100)\n")
        dirty_errors = verify(run_dir)
        if not any("dirty" in error for error in dirty_errors):
            print("self-test failed: dirtied repo should fail the side-effect-free check", file=sys.stderr)
            return 1
        run(["git", "checkout", "--", "src/discount.py"], cwd=repo)

        print("ok: review verify self-test passed")
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
        print("review smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: review agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
