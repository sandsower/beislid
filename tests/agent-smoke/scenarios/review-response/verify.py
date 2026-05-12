#!/usr/bin/env python3
"""Verify a host-agent review-response smoke run."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_STAMPS = [
    "✓ review-response/phase-1-detect v1 loaded",
    "✓ review-response/phase-2-fix v1 loaded",
    "✓ review-response/phase-3-push v1 loaded",
]

OUTPUT_SENTINEL = "=== BEISLID_AGENT_SMOKE_OUTPUT ==="


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


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def agent_output_text(run_dir: Path) -> str:
    chunks: list[str] = []
    for path in sorted(run_dir.glob("*.log")):
        if path.name in {"gh.log", "pr-review-source.log", "pr-review-update.log"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("$ "):
            if OUTPUT_SENTINEL not in text:
                continue
            text = text.split(OUTPUT_SENTINEL, 1)[1]
        # Codex logs may repeat the final assistant answer after a `tokens used`
        # footer. Ignore that host-rendered duplicate, but keep earlier duplicate
        # stamp groups visible so real protocol double-emission still fails.
        text = text.split("\ntokens used\n", 1)[0]
        chunks.append(text)
    return "\n".join(chunks)


def strip_markdown_fences(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    repo = Path(metadata["repo"])
    origin = Path(metadata["origin"])
    branch = metadata["branch"]
    gh_log = Path(metadata["gh_log"])
    source_log = Path(metadata["pr_review_source_log"])
    update_log = Path(metadata["pr_review_update_log"])
    update_payload = Path(metadata["pr_review_update_payload"])
    gate_marker = Path(metadata["gate_marker"])

    gh_text = gh_log.read_text(encoding="utf-8", errors="replace") if gh_log.exists() else ""
    if "gh pr view" not in gh_text:
        fail(errors, "mock gh did not record PR detection")
    if gh_text and f"cwd={repo}" not in gh_text:
        fail(errors, "mock gh did not run from fixture repo cwd")

    source_text = source_log.read_text(encoding="utf-8", errors="replace") if source_log.exists() else ""
    expected_pr_args = "sandsower review-response-smoke 7 https://example.invalid/sandsower/review-response-smoke/pull/7"
    if f"pr-review-source summary {expected_pr_args}" not in source_text:
        fail(errors, "mock PR review source summary was not called with expected PR identity")
    if f"pr-review-source threads {expected_pr_args}" not in source_text:
        fail(errors, "mock PR review source threads command was not called with expected PR identity")
    if source_text and f"cwd={repo}" not in source_text:
        fail(errors, "mock PR review source did not run from fixture repo cwd")

    update_text = update_log.read_text(encoding="utf-8", errors="replace") if update_log.exists() else ""
    if "pr-review-update reply" not in update_text:
        fail(errors, "mock PR review update reply was not called")
    if update_text and f"cwd={repo}" not in update_text:
        fail(errors, "mock PR review update did not run from fixture repo cwd")
    if not update_payload.exists():
        fail(errors, f"PR review update payload copy missing: {update_payload}")
        payload = {}
    else:
        try:
            payload = json.loads(update_payload.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(errors, f"PR review update payload is not valid JSON: {exc}")
            payload = {}
    body = str(payload.get("body", ""))
    if not re.search(r"fixed|addressed|hello reviewer", body, re.IGNORECASE):
        fail(errors, "PR review reply body does not mention the fix")
    if str(payload.get("in_reply_to", "")) != "7001":
        fail(errors, "PR review reply payload missing in_reply_to=7001")

    source_file = repo / "src" / "reply.py"
    source = source_file.read_text(encoding="utf-8", errors="replace") if source_file.exists() else ""
    if "return 'hello reviewer'" not in source and 'return "hello reviewer"' not in source:
        fail(errors, "fixture source was not fixed to return hello reviewer")
    if not gate_marker.exists():
        fail(errors, f"gate marker missing; validate-fixture did not prove execution: {gate_marker}")

    try:
        count = int(run(["git", "rev-list", "--count", "HEAD"], cwd=repo))
        if count < 2:
            fail(errors, "no feedback-fix commit was created")
    except Exception as exc:
        fail(errors, f"could not inspect local commit count: {exc}")
    try:
        local = run(["git", "rev-parse", "HEAD"], cwd=repo)
        remote = run(["git", f"--git-dir={origin}", "rev-parse", f"refs/heads/{branch}"])
        if local != remote:
            fail(errors, "fixture branch HEAD was not pushed to origin")
    except Exception as exc:
        fail(errors, f"could not verify pushed branch: {exc}")

    host_text = agent_output_text(run_dir)
    stamp_text = strip_markdown_fences(host_text)
    stamp_lines = [line.strip().rstrip() for line in stamp_text.splitlines() if line.strip().startswith("✓ review-response/phase-")]
    if stamp_lines != REQUIRED_STAMPS:
        fail(errors, f"agent output must contain exactly the expected aux load stamps in order: {stamp_lines!r}")

    combined_text = "\n".join([host_text, update_text, source_text, gh_text, body])
    for label, pattern in [
        ("fix evidence", r"hello reviewer|Fixed|addressed|clear fix|categor"),
        ("gate evidence", r"validate-fixture|gate|checks?"),
        ("reply evidence", r"reply|posted|Fixed in|addressed"),
    ]:
        if not re.search(pattern, combined_text, re.IGNORECASE):
            fail(errors, f"smoke evidence missing marker: {label}")

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-review-response-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        repo = run_dir / "repo"
        origin = run_dir / "origin.git"
        repo.mkdir()
        origin.mkdir()
        metadata = {
            "repo": str(repo),
            "origin": str(origin),
            "branch": "agent-smoke/review-response-review",
            "gh_log": str(run_dir / "gh.log"),
            "pr_review_source_log": str(run_dir / "pr-review-source.log"),
            "pr_review_update_log": str(run_dir / "pr-review-update.log"),
            "pr_review_update_payload": str(run_dir / "pr-review-update-payload.json"),
            "gate_marker": str(run_dir / "validate-fixture.marker"),
        }
        write(run_dir / "metadata.json", json.dumps(metadata))
        write(repo / "src" / "reply.py", "def greeting():\n    return 'hello reviewer'\n")
        run(["git", "init"], cwd=repo)
        run(["git", "config", "user.email", "selftest@example.invalid"], cwd=repo)
        run(["git", "config", "user.name", "Self Test"], cwd=repo)
        run(["git", "add", "."], cwd=repo)
        run(["git", "commit", "-m", "initial"], cwd=repo)
        write(repo / "README.md", "fix\n")
        run(["git", "add", "README.md"], cwd=repo)
        run(["git", "commit", "-m", "Address feedback"], cwd=repo)
        run(["git", "init", "--bare", str(origin)])
        run(["git", "branch", "-M", "agent-smoke/review-response-review"], cwd=repo)
        run(["git", "remote", "add", "origin", str(origin)], cwd=repo)
        run(["git", "push", "-u", "origin", "agent-smoke/review-response-review"], cwd=repo)
        write(run_dir / "gh.log", f"2026-01-01T00:00:00Z\tcwd={repo}\tgh pr view --json url,number,baseRefName,headRefName\n")
        expected_url = "https://example.invalid/sandsower/review-response-smoke/pull/7"
        write(run_dir / "pr-review-source.log", f"2026-01-01T00:00:01Z\tcwd={repo}\tpr-review-source summary sandsower review-response-smoke 7 {expected_url}\n2026-01-01T00:00:02Z\tcwd={repo}\tpr-review-source threads sandsower review-response-smoke 7 {expected_url}\n")
        write(run_dir / "pr-review-update.log", f"2026-01-01T00:00:03Z\tcwd={repo}\tpr-review-update reply /tmp/payload.json\n")
        write(run_dir / "pr-review-update-payload.json", json.dumps({"body": "Fixed in abc1234: hello reviewer", "in_reply_to": 7001}))
        write(run_dir / "validate-fixture.marker", "validate-fixture ran\n")

        missing_gate = run_dir / "missing-gate.log"
        gate_marker = run_dir / "validate-fixture.marker"
        gate_marker.unlink()
        write(missing_gate, "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "categorized as clear fix",
            "validate-fixture gate passed",
            "reply posted",
            "",
        ]))
        gate_errors = verify(run_dir)
        if not any("gate marker missing" in error for error in gate_errors):
            print("self-test failed: missing gate marker should fail", file=sys.stderr)
            return 1
        missing_gate.unlink()
        write(gate_marker, "validate-fixture ran\n")

        prompt_only = "\n".join(REQUIRED_STAMPS)
        write(run_dir / "prompt-only.log", f"$ host command with multiline prompt\n\n{prompt_only}\n\n")
        prompt_errors = verify(run_dir)
        if not any("aux load stamps" in error for error in prompt_errors):
            print("self-test failed: prompt-only markers should not satisfy aux stamp checks", file=sys.stderr)
            return 1
        (run_dir / "prompt-only.log").unlink()

        write(run_dir / "duplicate.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            REQUIRED_STAMPS[-1],
            "categorized as clear fix",
            "validate-fixture gate passed",
            "reply posted",
            "",
        ]))
        duplicate_errors = verify(run_dir)
        if not any("exactly the expected aux load stamps" in error for error in duplicate_errors):
            print("self-test failed: duplicate aux stamps should fail", file=sys.stderr)
            return 1
        (run_dir / "duplicate.log").unlink()

        write(run_dir / "codex.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "categorized as clear fix",
            "validate-fixture gate passed",
            "reply posted",
            "tokens used",
            "123",
            *REQUIRED_STAMPS,
            "categorized as clear fix",
            "validate-fixture gate passed",
            "reply posted",
            "",
        ]))
        errors = verify(run_dir)
        if errors:
            print("self-test failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        (run_dir / "codex.log").unlink()

        write(run_dir / "claude.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "categorized as clear fix",
            "validate-fixture gate passed",
            "reply posted",
            "",
        ]))
        errors = verify(run_dir)
        if errors:
            print("self-test failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("ok: review-response verify self-test passed")
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
        print("review-response smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: review-response agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
