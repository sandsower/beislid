#!/usr/bin/env python3
"""Verify review-response stops at strict paste when PR source is absent."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.verification import collect_agent_output, fail, require_markers, require_repo_snapshot, require_stamp_sequence

REQUIRED_STAMPS = ["✓ review-response/phase-1-detect v1 loaded"]
FORBIDDEN_GH_PATTERNS = [
    ("gh api", r"\bgh api\b"),
    ("gh pr view --comments", r"\bgh pr view\b.*--comments"),
    ("gh pr view comments/reviews JSON", r"\bgh pr view\b.*--json[^\n]*(comments|reviews|reviewThreads)"),
    ("gh pr review", r"\bgh pr review\b"),
    ("gh pr comment", r"\bgh pr comment\b"),
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    repo = Path(metadata["repo"])
    gh_log = Path(metadata["gh_log"])
    expected_head = str(metadata.get("expected_head", "")) or None

    gh_text = gh_log.read_text(encoding="utf-8", errors="replace") if gh_log.exists() else ""
    if "gh pr view --json url,number,baseRefName,headRefName" not in gh_text:
        fail(errors, "product", "mock gh did not record identity-only PR detection")
    if gh_text and f"cwd={repo}" not in gh_text:
        fail(errors, "artifact", "mock gh did not run from fixture repo cwd")
    for label, pattern in FORBIDDEN_GH_PATTERNS:
        if re.search(pattern, gh_text):
            fail(errors, "product", f"forbidden review-source/update command ran despite missing pr_review_source: {label}")

    host_text = collect_agent_output(run_dir, strip_tokens=True)
    require_stamp_sequence(errors, text=host_text, stamps=REQUIRED_STAMPS, label="agent output", kind="verifier")
    if "✓ review-response/phase-2-fix v1 loaded" in host_text or "✓ review-response/phase-3-push v1 loaded" in host_text:
        fail(errors, "product", "agent loaded Phase 2/3 even though strict paste feedback was required")
    require_markers(
        errors,
        text=host_text,
        markers=[
            ("missing source disclosure", r"pr_review_source[`']?\s+is\s+not\s+configured|`pr_review_source` is not configured"),
            ("strict paste prompt", r"Paste the full source"),
            ("no ad-hoc gh fetch", r"not fetch|will not fetch|identity-only|does not authorize"),
        ],
    )

    require_repo_snapshot(errors, repo=repo, expected_head=expected_head, kind="artifact")
    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-review-response-no-source-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        repo = run_dir / "repo"
        repo.mkdir()
        write(repo / "README.md", "unchanged\n")
        run(["git", "init"], cwd=repo)
        run(["git", "config", "user.email", "selftest@example.invalid"], cwd=repo)
        run(["git", "config", "user.name", "Self Test"], cwd=repo)
        run(["git", "add", "."], cwd=repo)
        run(["git", "commit", "-m", "initial"], cwd=repo)
        expected_head = run(["git", "rev-parse", "HEAD"], cwd=repo)
        metadata = {
            "repo": str(repo),
            "gh_log": str(run_dir / "gh.log"),
            "expected_head": expected_head,
        }
        write(run_dir / "metadata.json", json.dumps(metadata))
        write(
            run_dir / "gh.log",
            f"2026-01-01T00:00:00Z\tcwd={repo}\tgh pr view --json url,number,baseRefName,headRefName\n",
        )
        write(
            run_dir / "agent.log",
            "\n".join([
                "=== BEISLID_AGENT_SMOKE_OUTPUT ===",
                REQUIRED_STAMPS[0],
                "`pr_review_source` is not configured. I will not fetch PR review feedback with ad-hoc gh commands.",
                "Paste the full source, including unresolved threads, author/source, status, file/line if relevant, and links if available.",
                "PR detection is identity-only and does not authorize feedback retrieval.",
                "",
            ]),
        )
        errors = verify(run_dir)
        if errors:
            print("self-test failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        write(
            run_dir / "gh.log",
            f"2026-01-01T00:00:00Z\tcwd={repo}\tgh pr view --json url,number,baseRefName,headRefName\n"
            f"2026-01-01T00:00:01Z\tcwd={repo}\tgh api repos/sandsower/review-response-no-source/pulls/9/comments\n",
        )
        forbidden_errors = verify(run_dir)
        if not any("forbidden" in error for error in forbidden_errors):
            print("self-test failed: forbidden gh api should fail", file=sys.stderr)
            return 1
        print("ok: review-response no-source verify self-test passed")
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
        print("review-response no-source smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: review-response no-source agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
