#!/usr/bin/env python3
"""Verify a host-agent walk-the-diff pacing smoke run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_STAMPS = [
    "✓ walk-the-diff/phase-1-context v1 loaded",
    "✓ walk-the-diff/phase-2-tour-plan v1 loaded",
    "✓ walk-the-diff/phase-3-present v1 loaded",
]
PHASE_4_STAMP = "✓ walk-the-diff/phase-4-wrap v1 loaded"
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
    errors.append(message)


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


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    verify_clean_repo(errors, metadata)

    state_dir = Path(metadata["state_dir"])
    feedback_dir = state_dir / "feedback"
    if feedback_dir.exists() and list(feedback_dir.glob("*.md")):
        fail(errors, "pacing smoke should not write feedback docs before wrap")

    host_text = agent_output_text(run_dir)
    stamp_source = drop_trailing_stamp_restatement(host_text, REQUIRED_STAMPS)
    if PHASE_4_STAMP in stamp_source:
        fail(errors, "default pacing smoke must not load Phase 4 wrap")
    stamp_text = strip_markdown_fences(stamp_source)
    stamp_lines = [line.strip() for line in stamp_text.splitlines() if line.strip().startswith("✓ walk-the-diff/phase-")]
    if stamp_lines != REQUIRED_STAMPS:
        fail(errors, f"agent output must contain exactly the expected Phase 1-3 aux load stamps in order: {stamp_lines!r}")

    for label, pattern in [
        ("base context", r"\bmain\b|merge[- ]base|base branch"),
        ("tour plan", r"tour|chunk|source[- ]first"),
        ("fenced diff", r"```diff"),
        ("gate option Move on", r"Move on"),
        ("gate option I have questions", r"I have questions"),
        ("gate option Flag for follow-up", r"Flag for follow-up"),
    ]:
        if not re.search(pattern, host_text, re.IGNORECASE):
            fail(errors, f"smoke evidence missing marker: {label}")

    for marker in metadata.get("first_chunk_markers", []):
        if marker not in host_text:
            fail(errors, f"first chunk marker missing from output: {marker}")
    diff_text = "\n".join(extract_diff_blocks(host_text))
    first_diff_markers = metadata.get("first_chunk_diff_markers") or []
    for marker in first_diff_markers:
        if marker not in diff_text:
            fail(errors, f"first chunk diff marker missing from fenced diff: {marker}")
    for marker in metadata.get("forbidden_later_diff_markers", []):
        if marker in host_text:
            fail(errors, f"later chunk diff leaked before gate advanced: {marker}")
    for path_marker in ["tests/test_calculator.py", "README.md"]:
        if path_marker in diff_text:
            fail(errors, f"later chunk diff leaked before gate advanced: {path_marker}")

    return errors


def create_selftest_repo(run_dir: Path) -> dict:
    repo = run_dir / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", "selftest@example.invalid"], cwd=repo)
    run(["git", "config", "user.name", "Self Test"], cwd=repo)
    write(repo / "src" / "calculator.py", "def subtotal(items):\n    return sum(items)\n\ndef add_tax(amount, tax_rate):\n    return round(amount * (1 + tax_rate), 2)\n")
    write(repo / "tests" / "test_calculator.py", "def test_receipt_total_includes_tax():\n    assert True\n")
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
        "first_chunk_markers": ["src/calculator.py", "add_tax"],
        "first_chunk_diff_markers": ["+def add_tax"],
        "forbidden_later_diff_markers": ["+from src.calculator import receipt_total, subtotal", "def test_receipt_total_includes_tax"],
    }
    write(run_dir / "metadata.json", json.dumps(metadata))
    return metadata


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-walk-diff-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        create_selftest_repo(run_dir)

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
            "Base branch main; source-first tour plan chunk 1 src/calculator.py",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        duplicate_errors = verify(run_dir)
        if not any("exactly the expected" in error for error in duplicate_errors):
            print("self-test failed: duplicate aux stamps should fail", file=sys.stderr)
            return 1
        (run_dir / "duplicate.log").unlink()

        write(run_dir / "phase4.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            PHASE_4_STAMP,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        phase4_errors = verify(run_dir)
        if not any("Phase 4" in error or "expected Phase 1-3" in error for error in phase4_errors):
            print("self-test failed: Phase 4 stamp should fail default smoke", file=sys.stderr)
            return 1
        (run_dir / "phase4.log").unlink()

        write(run_dir / "phase4-fenced.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py",
            "```text",
            PHASE_4_STAMP,
            "```",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        phase4_fenced_errors = verify(run_dir)
        if not any("Phase 4" in error for error in phase4_fenced_errors):
            print("self-test failed: fenced Phase 4 stamp should fail default smoke", file=sys.stderr)
            return 1
        (run_dir / "phase4-fenced.log").unlink()

        write(run_dir / "empty-diff.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py with add_tax",
            "```diff",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        empty_diff_errors = verify(run_dir)
        if not any("first chunk diff marker missing" in error for error in empty_diff_errors):
            print("self-test failed: empty first chunk diff should fail", file=sys.stderr)
            return 1
        (run_dir / "empty-diff.log").unlink()

        write(run_dir / "commit-mutation.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
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
            "Base branch main; source-first tour plan chunk 1 src/calculator.py",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        run(["git", "commit", "--allow-empty", "-m", "unexpected empty mutation"], cwd=repo)
        empty_errors = verify(run_dir)
        if not any("HEAD changed" in error for error in empty_errors):
            print("self-test failed: empty commit should fail", file=sys.stderr)
            return 1
        run(["git", "reset", "--hard", "HEAD~1"], cwd=repo)
        (run_dir / "empty-commit.log").unlink()

        write(run_dir / "tour-mention.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py then tests/test_calculator.py later",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        tour_errors = verify(run_dir)
        if tour_errors:
            print("self-test failed: later marker outside diff should be allowed:", file=sys.stderr)
            for error in tour_errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        (run_dir / "tour-mention.log").unlink()

        write(run_dir / "leak.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py then tests/test_calculator.py",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "+def test_receipt_total_includes_tax():",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        leak_errors = verify(run_dir)
        if not any("later chunk diff leaked" in error for error in leak_errors):
            print("self-test failed: later chunk diff marker should fail", file=sys.stderr)
            return 1
        (run_dir / "leak.log").unlink()

        write(run_dir / "import-leak.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py then tests/test_calculator.py",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "+from src.calculator import receipt_total, subtotal",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        import_leak_errors = verify(run_dir)
        if not any("later chunk diff leaked" in error for error in import_leak_errors):
            print("self-test failed: later import diff marker should fail", file=sys.stderr)
            return 1
        (run_dir / "import-leak.log").unlink()

        write(run_dir / "path-leak.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py then tests/test_calculator.py",
            "```diff",
            "+++ b/tests/test_calculator.py",
            "+from src.calculator import receipt_total",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        path_leak_errors = verify(run_dir)
        if not any("later chunk diff leaked" in error for error in path_leak_errors):
            print("self-test failed: later diff path should fail", file=sys.stderr)
            return 1
        (run_dir / "path-leak.log").unlink()

        write(run_dir / "trailing-restatement.log", "\n".join([
            OUTPUT_SENTINEL,
            REQUIRED_STAMPS[0],
            "Base branch main",
            REQUIRED_STAMPS[1],
            "source-first tour plan chunk 1 src/calculator.py",
            REQUIRED_STAMPS[2],
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
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

        write(run_dir / "codex-tool-output.log", "\n".join([
            OUTPUT_SENTINEL,
            "OpenAI Codex v0.128.0",
            "codex",
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py then tests/test_calculator.py later",
            "exec",
            "git diff main...HEAD -- tests/test_calculator.py",
            "+def test_receipt_total_includes_tax():",
            "codex",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
            "",
        ]))
        codex_tool_errors = verify(run_dir)
        if codex_tool_errors:
            print("self-test failed: Codex tool output should not count as presented diff leakage:", file=sys.stderr)
            for error in codex_tool_errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        (run_dir / "codex-tool-output.log").unlink()

        write(run_dir / "codex.log", "\n".join([
            OUTPUT_SENTINEL,
            *REQUIRED_STAMPS,
            "Base branch main; source-first tour plan chunk 1 src/calculator.py",
            "```diff",
            "+def add_tax(amount, tax_rate):",
            "```",
            "Move on / I have questions / Flag for follow-up",
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
        print("ok: walk-the-diff verify self-test passed")
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
        print("walk-the-diff smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: walk-the-diff agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
