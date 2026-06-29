#!/usr/bin/env python3
"""Verify a host-agent kickoff smoke run."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.verification import collect_agent_output, fail, require_stamp_sequence

REQUIRED_STAMPS = [
    "✓ kickoff/step-1-ticket v1 loaded",
    "✓ kickoff/step-2-context v1 loaded",
    "✓ kickoff/step-3-team-guidance v1 loaded",
    "✓ kickoff/step-4-readiness v1 loaded",
    "✓ kickoff/step-5-scope v1 loaded",
    "✓ kickoff/step-6-blueprint v1 loaded",
    "✓ kickoff/step-7-discoveries v1 loaded",
    "✓ kickoff/step-8-ticket-update v1 loaded",
]

REQUIRED_PATTERNS = [
    ("fixture code explored", r"src/summary\.py|test_summary\.py"),
    ("explore skill marker", r"skill-only-context-token-44"),
    ("blueprint route", r"blueprint"),
    ("scope classifier", r"scope_classification|scope classification"),
    ("single_pr kind", r"kind:\s*single_pr|\bsingle_pr\b"),
    ("implement handoff", r"implement"),
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    gh_log = Path(metadata["gh_log"])
    comment_log = Path(metadata["ticket_comment_log"])
    comment_body = Path(metadata["ticket_comment_body"])
    lifecycle_action_log = Path(metadata["lifecycle_action_log"])
    repo = Path(metadata["repo"])

    gh_text = gh_log.read_text(encoding="utf-8", errors="replace") if gh_log.exists() else ""
    if "gh issue view 123" not in gh_text:
        fail(errors, "product", "mock gh did not record `gh issue view 123`")
    if gh_text and f"cwd={repo}" not in gh_text:
        fail(errors, "artifact", "mock gh did not run from fixture repo cwd")

    comment_text = comment_log.read_text(encoding="utf-8", errors="replace") if comment_log.exists() else ""
    if "ticket-comment 123" not in comment_text:
        fail(errors, "product", "mock ticket-comment did not post update for ticket 123")

    lifecycle_text = lifecycle_action_log.read_text(encoding="utf-8", errors="replace") if lifecycle_action_log.exists() else ""
    if "lifecycle-action 123 123 123-kickoff-smoke kickoff_start" not in lifecycle_text:
        fail(errors, "product", "mock lifecycle action did not run with ticket, branch, and event placeholders")
    if lifecycle_text and f"cwd={repo}" not in lifecycle_text:
        fail(errors, "artifact", "mock lifecycle action did not run from fixture repo cwd")

    if not comment_body.exists():
        fail(errors, "artifact", f"ticket update body copy missing: {comment_body}")
        body = ""
    else:
        body = comment_body.read_text(encoding="utf-8", errors="replace")
    for label, pattern in [
        ("approach", r"approach|plan"),
        ("files/modules", r"files|modules|src/summary\.py|tests/test_summary\.py"),
        ("tests", r"test|verification"),
        ("risks", r"risk|open question"),
        ("explore skill marker", r"skill-only-context-token-44"),
        ("scope classification", r"scope_classification|scope classification"),
        ("single_pr kind", r"kind:\s*single_pr|\bsingle_pr\b"),
        ("blueprint route", r"recommended_route:\s*blueprint|recommended route:\s*blueprint"),
        ("approval field", r"requires_human_approval:\s*false|requires human approval:\s*false"),
        ("split field", r"requires_split:\s*false|requires split:\s*false"),
    ]:
        if not re.search(pattern, body, re.IGNORECASE):
            fail(errors, "verifier", f"ticket update body missing {label} content")

    host_text = collect_agent_output(run_dir, skip_names={"gh.log", "ticket-comment.log"})
    require_stamp_sequence(
        errors,
        text=host_text,
        stamps=REQUIRED_STAMPS,
        label="agent output",
        kind="verifier",
    )

    combined_text = "\n".join([host_text, body, gh_text, comment_text, lifecycle_text])
    for label, pattern in REQUIRED_PATTERNS:
        if not re.search(pattern, combined_text, re.IGNORECASE):
            fail(errors, "product", f"smoke evidence missing marker: {label}")

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-kickoff-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        repo = run_dir / "repo"
        repo.mkdir()
        metadata = {
            "repo": str(repo),
            "gh_log": str(run_dir / "gh.log"),
            "ticket_comment_log": str(run_dir / "ticket-comment.log"),
            "ticket_comment_body": str(run_dir / "ticket-comment-body.md"),
            "lifecycle_action_log": str(run_dir / "lifecycle-action.log"),
        }
        write(run_dir / "metadata.json", json.dumps(metadata))
        write(run_dir / "gh.log", f"2026-01-01T00:00:00Z\tcwd={repo}\tgh issue view 123 --json number,title,body,state,labels\n")
        write(run_dir / "ticket-comment-log".replace("-log", ".log"), f"2026-01-01T00:00:01Z\tcwd={repo}\tticket-comment 123 /tmp/body.md\n")
        write(run_dir / "lifecycle-action.log", f"2026-01-01T00:00:01Z\tcwd={repo}\tlifecycle-action 123 123 123-kickoff-smoke kickoff_start\n")
        write(run_dir / "ticket-comment-body.md", "Approach summary\nskill-only-context-token-44\nscope_classification:\n  kind: single_pr\n  recommended_route: blueprint\n  requires_human_approval: false\n  requires_split: false\nFiles: src/summary.py and tests/test_summary.py\nTests: pytest\nRisks: none\n")
        prompt_only = "\n".join(REQUIRED_STAMPS)
        write(run_dir / "prompt-only.log", f"$ host command with multiline prompt\n\n{prompt_only}\n\n")
        prompt_errors = verify(run_dir)
        if not any("aux load stamps" in error for error in prompt_errors):
            print("self-test failed: prompt-only markers should not satisfy aux stamp checks", file=sys.stderr)
            return 1
        (run_dir / "prompt-only.log").unlink()

        write(run_dir / "duplicate.log", "\n".join([
            "=== BEISLID_AGENT_SMOKE_OUTPUT ===",
            *REQUIRED_STAMPS,
            REQUIRED_STAMPS[-1],
            "Add activity summary filters",
            "src/summary.py tests/test_summary.py",
            "blueprint approved",
            "single PR",
            "implement handoff prepared",
            "",
        ]))
        duplicate_errors = verify(run_dir)
        if not any("expected aux load stamps" in error for error in duplicate_errors):
            print("self-test failed: duplicate aux stamps should fail", file=sys.stderr)
            return 1
        (run_dir / "duplicate.log").unlink()

        write(run_dir / "codex.log", "\n".join([
            "=== BEISLID_AGENT_SMOKE_OUTPUT ===",
            *REQUIRED_STAMPS,
            "Add activity summary filters",
            "src/summary.py tests/test_summary.py",
            "skill-only-context-token-44",
            "blueprint approved",
            "single PR",
            "implement handoff prepared",
            "",
        ]))
        errors = verify(run_dir)
        if errors:
            print("self-test failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("ok: kickoff verify self-test passed")
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
        print("kickoff smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: kickoff agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
