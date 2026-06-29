#!/usr/bin/env python3
"""Verify a host-agent walk-the-diff wrap smoke run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.verification import collect_agent_output, require_repo_snapshot, require_stamp_sequence, strip_trailing_stamp_restatement

REQUIRED_STAMPS = [
    "✓ walk-the-diff/phase-1-context v1 loaded",
    "✓ walk-the-diff/phase-2-tour-plan v1 loaded",
    "✓ walk-the-diff/phase-3-present v1 loaded",
    "✓ walk-the-diff/phase-4-wrap v1 loaded",
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def fail(errors: list[str], message: str) -> None:
    errors.append(f"verifier: {message}")


def strip_codex_exec_blocks(text: str) -> str:
    lines: list[str] = []
    skipping_exec = False
    for line in text.splitlines():
        if line.strip() == "exec":
            skipping_exec = True
            continue
        if skipping_exec and line.strip() in {"codex", "user"}:
            skipping_exec = False
        if not skipping_exec:
            lines.append(line)
    return "\n".join(lines)


def agent_output_text(run_dir: Path) -> str:
    chunks: list[str] = []
    for path in sorted(run_dir.glob("*.log")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("$ "):
            if OUTPUT_SENTINEL not in text:
                continue
            text = text.split(OUTPUT_SENTINEL, 1)[1]
        text = text.split("\ntokens used\n", 1)[0]
        if "OpenAI Codex" in text:
            text = strip_codex_exec_blocks(text)
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


def extract_diff_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    in_diff = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```diff"):
            in_diff = True
            current = []
            continue
        if in_diff and stripped.startswith("```"):
            blocks.append("\n".join(current))
            in_diff = False
            current = []
            continue
        if in_diff:
            current.append(line)
    return blocks


def drop_trailing_stamp_restatement(text: str, stamps: list[str]) -> str:
    lines = text.splitlines()
    non_empty = [line.strip() for line in lines if line.strip()]
    if len(non_empty) < len(stamps) * 2 or non_empty[-len(stamps):] != stamps:
        return text
    earlier = non_empty[:-len(stamps)]
    if not all(stamp in earlier for stamp in stamps):
        return text
    remove = len(stamps)
    trimmed = list(lines)
    while trimmed and remove:
        line = trimmed.pop()
        if line.strip():
            remove -= 1
    return "\n".join(trimmed)


def verify_clean_repo(errors: list[str], metadata: dict) -> None:
    repo = Path(metadata["repo"])
    try:
        status = run(["git", "status", "--short"], cwd=repo)
        if status:
            fail(errors, f"fixture repo is dirty:\n{status}")
    except Exception as exc:
        fail(errors, f"could not inspect git status: {exc}")
    expected_head = metadata.get("head_sha")
    if expected_head:
        try:
            actual_head = run(["git", "rev-parse", "HEAD"], cwd=repo)
            if actual_head != expected_head:
                fail(errors, f"fixture repo HEAD changed after smoke: expected {expected_head}, got {actual_head}")
        except Exception as exc:
            fail(errors, f"could not inspect HEAD: {exc}")

    expected_files = sorted(metadata.get("tracked_files") or (metadata.get("tracked_hashes") or {}).keys())
    try:
        actual_files = sorted(run(["git", "ls-files"], cwd=repo).splitlines())
        if actual_files != expected_files:
            fail(errors, f"tracked file set changed after smoke: expected {expected_files!r}, got {actual_files!r}")
    except Exception as exc:
        fail(errors, f"could not inspect tracked files: {exc}")

    for rel, expected in (metadata.get("tracked_hashes") or {}).items():
        path = repo / rel
        if not path.exists():
            fail(errors, f"tracked file missing after smoke: {rel}")
            continue
        actual = sha256(path)
        if actual != expected:
            fail(errors, f"tracked file hash changed after smoke: {rel}")


def verify_feedback_doc(errors: list[str], metadata: dict) -> str:
    state_dir = Path(metadata["state_dir"])
    repo = Path(metadata["repo"])
    docs = sorted((state_dir / "feedback").glob("*.md")) if (state_dir / "feedback").exists() else []
    if not docs:
        fail(errors, "wrap smoke did not write a feedback doc under BEISLID_STATE_DIR/feedback")
        return ""
    if len(docs) > 1:
        fail(errors, f"expected one feedback doc, found {len(docs)}")
    repo_feedback = list(repo.rglob("*feedback*.md"))
    if repo_feedback:
        fail(errors, f"feedback docs must not be written inside repo: {[str(p.relative_to(repo)) for p in repo_feedback]}")
    text = docs[0].read_text(encoding="utf-8", errors="replace")
    for label, pattern in [
        ("date", r"\*\*Date\*\*|Date:"),
        ("branch", r"\*\*Branch\*\*|Branch:"),
        ("chunks reviewed", r"Chunks Reviewed"),
        ("chunk status", r"Status:"),
        ("open items", r"Open Items"),
        ("overall assessment", r"Overall Assessment"),
    ]:
        if not re.search(pattern, text, re.IGNORECASE):
            fail(errors, f"feedback doc missing {label}")
    if re.search(r"Status:\s*needs changes", text, re.IGNORECASE):
        fail(errors, "feedback doc contradicts scripted smoke reviewer: chunk status is needs changes")
    open_match = re.search(r"## Open Items\s*(.*?)(?:\n## |\Z)", text, re.IGNORECASE | re.DOTALL)
    open_body = open_match.group(1).strip() if open_match else ""
    if not re.fullmatch(r"(?:None|No open items\.?|No concerns\.?)", open_body, re.IGNORECASE):
        fail(errors, f"feedback doc should record no open items for scripted smoke reviewer, got: {open_body!r}")
    overall_match = re.search(r"## Overall Assessment\s*(.*?)(?:\n## |\Z)", text, re.IGNORECASE | re.DOTALL)
    overall_body = overall_match.group(1).strip() if overall_match else ""
    if re.search(r"not comfortable|uncomfortable|needs changes", overall_body, re.IGNORECASE) or not re.search(r"comfortable|no (?:open items|concerns)", overall_body, re.IGNORECASE):
        fail(errors, f"feedback doc should record comfortable overall for scripted smoke reviewer, got: {overall_body!r}")
    return text


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    require_repo_snapshot(
        errors,
        repo=Path(metadata["repo"]),
        expected_head=metadata.get("head_sha"),
        expected_files=metadata.get("tracked_files"),
        expected_hashes=metadata.get("tracked_hashes"),
        kind="artifact",
    )
    feedback_text = verify_feedback_doc(errors, metadata)

    host_text = collect_agent_output(run_dir, strip_tokens=True, strip_exec=True)
    stamp_source = strip_trailing_stamp_restatement(host_text, REQUIRED_STAMPS)
    require_stamp_sequence(
        errors,
        text=stamp_source,
        stamps=REQUIRED_STAMPS,
        label="agent output",
        kind="verifier",
    )

    combined_text = "\n".join([host_text, feedback_text])
    for label, pattern in [
        ("base context", r"\bmain\b|merge[- ]base|base branch"),
        ("source chunk", r"src/calculator\.py|add_tax"),
        ("tests/docs chunk", r"tests/test_calculator\.py|README\.md|receipt_total"),
        ("wrap evidence", r"feedback doc|review complete|comfortable overall|Overall Assessment"),
        ("scripted move-on decisions", r"Move on"),
    ]:
        if not re.search(pattern, combined_text, re.IGNORECASE):
            fail(errors, f"smoke evidence missing marker: {label}")

    diff_text = "\n".join(extract_diff_blocks(host_text))
    for marker in [
        "+def add_tax",
        "+def receipt_total",
        "+from src.calculator import receipt_total, subtotal",
        "+def test_receipt_total_includes_tax",
        "+Tax receipts now include a smoke-covered example.",
    ]:
        if marker not in diff_text:
            fail(errors, f"wrap smoke missing presented fenced diff marker: {marker}")

    return errors


def create_selftest_repo(run_dir: Path) -> dict:
    repo = run_dir / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", "selftest@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Self Test"], cwd=repo)
    write(repo / "src" / "calculator.py", "def add_tax(amount, tax_rate):\n    return amount\n")
    write(repo / "tests" / "test_calculator.py", "def test_receipt_total_includes_tax():\n    assert True\n")
    write(repo / "README.md", "README\n")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "fixture"], cwd=repo)
    tracked_files = run(["git", "ls-files"], cwd=repo).splitlines()
    hashes = {rel: sha256(repo / rel) for rel in tracked_files}
    metadata = {
        "repo": str(repo),
        "state_dir": str(run_dir / "state"),
        "head_sha": run(["git", "rev-parse", "HEAD"], cwd=repo),
        "tracked_files": tracked_files,
        "tracked_hashes": hashes,
    }
    write(run_dir / "metadata.json", json.dumps(metadata))
    return metadata


def write_feedback(run_dir: Path) -> None:
    write(run_dir / "state" / "feedback" / "walk-diff-selftest-456.md", """# Review Feedback: Walk Diff Selftest

**Date**: 2026-01-01
**Branch**: 456-walk-diff-smoke
**Ticket**: 456

## Chunks Reviewed

### Source helpers
- Status: approved
- Feedback:
  - None

### Tests and docs
- Status: approved
- Feedback:
  - None

## Open Items
None

## Overall Assessment
Comfortable overall.
""")


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-walk-diff-wrap-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        create_selftest_repo(run_dir)

        prompt_only = "\n".join(REQUIRED_STAMPS)
        write(run_dir / "prompt-only.log", f"$ host command with multiline prompt\n\n{prompt_only}\n\n")
        prompt_errors = verify(run_dir)
        if not any("aux load stamps" in error for error in prompt_errors):
            print("self-test failed: prompt-only markers should not satisfy aux stamp checks", file=sys.stderr)
            return 1
        (run_dir / "prompt-only.log").unlink()

        write_feedback(run_dir)
        write(run_dir / "duplicate.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            REQUIRED_STAMPS[-1],
            "Base branch main; src/calculator.py add_tax; tests/test_calculator.py; feedback doc saved; comfortable overall",
            "",
        ]))
        duplicate_errors = verify(run_dir)
        if not any("exactly the expected" in error for error in duplicate_errors):
            print("self-test failed: duplicate aux stamps should fail", file=sys.stderr)
            return 1
        (run_dir / "duplicate.log").unlink()

        # A repo-local feedback file must fail even when the state feedback exists.
        write(run_dir / "repo" / "review-feedback.md", "bad\n")
        write(run_dir / "repo-feedback.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; src/calculator.py add_tax; tests/test_calculator.py; feedback doc saved; comfortable overall",
            "",
        ]))
        repo_errors = verify(run_dir)
        if not any("inside repo" in error or "fixture repo is dirty" in error for error in repo_errors):
            print("self-test failed: repo-local feedback should fail", file=sys.stderr)
            return 1
        (run_dir / "repo" / "review-feedback.md").unlink()
        (run_dir / "repo-feedback.log").unlink()

        feedback_path = run_dir / "state" / "feedback" / "walk-diff-selftest-456.md"
        good_feedback = feedback_path.read_text(encoding="utf-8")
        write(feedback_path, """# Review Feedback: Bad Smoke State

**Date**: 2026-01-01
**Branch**: 456-walk-diff-smoke
**Ticket**: 456

## Chunks Reviewed

### Source helpers
- Status: needs changes
- Feedback:
  - Something is wrong.

## Open Items
- Fix the source helper.

## Overall Assessment
Not comfortable.
""")
        write(run_dir / "bad-feedback.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; src/calculator.py add_tax; tests/test_calculator.py; feedback doc saved; not comfortable overall",
            "",
        ]))
        bad_feedback_errors = verify(run_dir)
        if not any("scripted smoke reviewer" in error or "comfortable overall" in error or "no open items" in error for error in bad_feedback_errors):
            print("self-test failed: bad feedback doc should fail", file=sys.stderr)
            return 1
        write(feedback_path, good_feedback)
        (run_dir / "bad-feedback.log").unlink()

        write(run_dir / "commit-mutation.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; src/calculator.py add_tax; tests/test_calculator.py; feedback doc saved; comfortable overall",
            "",
        ]))
        repo = run_dir / "repo"
        write(repo / "extra.txt", "unexpected\n")
        run(["git", "add", "extra.txt"], cwd=repo)
        run(["git", "commit", "-m", "unexpected repo mutation"], cwd=repo)
        mutation_errors = verify(run_dir)
        if not any("HEAD changed" in error or "tracked file set changed" in error for error in mutation_errors):
            print("self-test failed: committed repo mutation should fail", file=sys.stderr)
            return 1
        run(["git", "reset", "--hard", "HEAD~1"], cwd=repo)
        (run_dir / "commit-mutation.log").unlink()

        write(run_dir / "empty-commit.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; src/calculator.py add_tax; tests/test_calculator.py; feedback doc saved; comfortable overall",
            "",
        ]))
        run(["git", "commit", "--allow-empty", "-m", "unexpected empty mutation"], cwd=repo)
        empty_errors = verify(run_dir)
        if not any("HEAD changed" in error for error in empty_errors):
            print("self-test failed: empty commit should fail", file=sys.stderr)
            return 1
        run(["git", "reset", "--hard", "HEAD~1"], cwd=repo)
        (run_dir / "empty-commit.log").unlink()

        write(run_dir / "trailing-restatement.log", "\n".join([
            OUTPUT_SENTINEL,
            REQUIRED_STAMPS[0],
            "Base branch main",
            REQUIRED_STAMPS[1],
            "src/calculator.py add_tax",
            REQUIRED_STAMPS[2],
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "+def receipt_total(items, tax_rate):",
            "```",
            "Move on",
            "tests/test_calculator.py and README.md",
            "```diff",
            "+from src.calculator import receipt_total, subtotal",
            "+def test_receipt_total_includes_tax():",
            "+Tax receipts now include a smoke-covered example.",
            "```",
            "Move on",
            REQUIRED_STAMPS[3],
            "feedback doc saved; comfortable overall",
            *REQUIRED_STAMPS,
            "",
        ]))
        trailing_errors = verify(run_dir)
        if trailing_errors:
            print("self-test failed: trailing final stamp restatement should be ignored:", file=sys.stderr)
            for error in trailing_errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        (run_dir / "trailing-restatement.log").unlink()

        write(run_dir / "summary-only.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; src/calculator.py add_tax; tests/test_calculator.py; feedback doc saved; comfortable overall; Move on",
            "",
        ]))
        summary_only_errors = verify(run_dir)
        if not any("fenced diff marker" in error for error in summary_only_errors):
            print("self-test failed: summary-only wrap output should fail", file=sys.stderr)
            return 1
        (run_dir / "summary-only.log").unlink()

        write(run_dir / "missing-readme-diff.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; src/calculator.py add_tax",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "+def receipt_total(items, tax_rate):",
            "```",
            "Move on",
            "tests/test_calculator.py and README.md",
            "```diff",
            "+from src.calculator import receipt_total, subtotal",
            "+def test_receipt_total_includes_tax():",
            "```",
            "Move on; feedback doc saved; comfortable overall",
            "",
        ]))
        missing_readme_errors = verify(run_dir)
        if not any("Tax receipts" in error for error in missing_readme_errors):
            print("self-test failed: wrap output without README diff marker should fail", file=sys.stderr)
            return 1
        (run_dir / "missing-readme-diff.log").unlink()

        write(run_dir / "codex.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; src/calculator.py add_tax",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "+def receipt_total(items, tax_rate):",
            "```",
            "Move on",
            "tests/test_calculator.py and README.md",
            "```diff",
            "+from src.calculator import receipt_total, subtotal",
            "+def test_receipt_total_includes_tax():",
            "+Tax receipts now include a smoke-covered example.",
            "```",
            "Move on; feedback doc saved; comfortable overall",
            "tokens used",
            "123",
            *REQUIRED_STAMPS,
            "",
        ]))
        errors = verify(run_dir)
        if errors:
            print("self-test failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("ok: walk-the-diff-wrap verify self-test passed")
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
        print("walk-the-diff-wrap smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: walk-the-diff-wrap agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
