from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

OUTPUT_SENTINEL = "=== BEISLID_AGENT_SMOKE_OUTPUT ==="
TOKEN_FOOTER = "\ntokens used\n"


def run_test_functions(module_path: Path, repo_root: Path) -> list[str]:
    """Actually execute a fixture's bare `def test_x(): assert ...` functions -
    the pytest-free style every agent-smoke fixture ships (no pytest runtime
    dependency for this harness or its CI). Runs in a fresh subprocess per call
    so repeated verify() invocations against a mutated fixture (as in --self-test
    positive/negative pairs) never see a stale sys.modules cache from a prior
    call. Returns a list of 'test_name: error' failure strings (empty = all
    passed); a missing module or zero discovered test_* functions is also a
    failure, since a scenario with no real tests proves nothing."""
    if not module_path.is_file():
        return [f"{module_path}: test module missing"]
    script = (
        "import importlib.util, json, sys\n"
        f"sys.path.insert(0, {str(repo_root)!r})\n"
        f"spec = importlib.util.spec_from_file_location({module_path.stem!r}, {str(module_path)!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "failures = []\n"
        "found = False\n"
        "for name in dir(module):\n"
        "    if not name.startswith('test_'):\n"
        "        continue\n"
        "    fn = getattr(module, name)\n"
        "    if not callable(fn):\n"
        "        continue\n"
        "    found = True\n"
        "    try:\n"
        "        fn()\n"
        "    except Exception as exc:\n"
        "        failures.append(f'{name}: {exc}')\n"
        "if not found:\n"
        "    failures.append('no test_* functions found')\n"
        "print(json.dumps(failures))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        return [f"test runner crashed (exit {result.returncode}): {result.stdout.strip()}"]
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not output_lines:
        return ["test runner produced no output"]
    try:
        return json.loads(output_lines[-1])
    except json.JSONDecodeError:
        return [f"could not parse test runner output: {result.stdout.strip()}"]


def failure(kind: str, message: str) -> str:
    return f"{kind}: {message}"


def fail(errors: list[str], kind: str, message: str) -> None:
    errors.append(failure(kind, message))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_output_sentinel(text: str) -> str:
    if text.startswith("$ ") and OUTPUT_SENTINEL in text:
        return text.split(OUTPUT_SENTINEL, 1)[1]
    return text


def strip_token_footer(text: str) -> str:
    return text.split(TOKEN_FOOTER, 1)[0] if TOKEN_FOOTER in text else text


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


def strip_trailing_stamp_restatement(text: str, stamps: list[str]) -> str:
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


def collect_agent_output(
    run_dir: Path,
    *,
    skip_names: set[str] | None = None,
    strip_tokens: bool = False,
    strip_exec: bool = False,
) -> str:
    skip = skip_names or set()
    chunks: list[str] = []
    for path in sorted(run_dir.glob("*.log")):
        if path.name in skip:
            continue
        text = read_text(path)
        if text.startswith("$ ") and OUTPUT_SENTINEL not in text:
            continue
        is_codex = "OpenAI Codex" in text
        text = strip_output_sentinel(text)
        if strip_tokens:
            text = strip_token_footer(text)
        if strip_exec and is_codex:
            text = strip_codex_exec_blocks(text)
        chunks.append(text)
    return "\n".join(chunks)


def stamp_lines(text: str, prefix: str, *, strip_fences: bool = True) -> list[str]:
    source = strip_markdown_fences(text) if strip_fences else text
    return [line.strip() for line in source.splitlines() if line.strip().startswith(prefix)]


def require_exact_stamps(errors: list[str], *, text: str, stamps: list[str], label: str, kind: str = "verifier") -> None:
    require_stamp_sequence(errors, text=text, stamps=stamps, label=label, kind=kind)


def require_repo_snapshot(
    errors: list[str],
    *,
    repo: Path,
    expected_head: str | None = None,
    expected_files: list[str] | None = None,
    expected_hashes: dict[str, str] | None = None,
    kind: str = "artifact",
    label: str = "fixture repo",
) -> None:
    try:
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if status.returncode != 0:
            fail(errors, kind, f"could not inspect git status for {label}: {status.stderr.strip() or status.returncode}")
        elif status.stdout.strip():
            fail(errors, kind, f"{label} is dirty:\n{status.stdout.strip()}")
    except Exception as exc:
        fail(errors, kind, f"could not inspect git status for {label}: {exc}")

    if expected_head:
        try:
            actual_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if actual_head.returncode != 0:
                fail(errors, kind, f"could not inspect HEAD for {label}: {actual_head.stderr.strip() or actual_head.returncode}")
            elif actual_head.stdout.strip() != expected_head:
                fail(
                    errors,
                    kind,
                    f"{label} HEAD changed after smoke: expected {expected_head}, got {actual_head.stdout.strip()}",
                )
        except Exception as exc:
            fail(errors, kind, f"could not inspect HEAD for {label}: {exc}")

    expected_files = sorted(expected_files or (sorted((expected_hashes or {}).keys())))
    if expected_files:
        try:
            actual_files = subprocess.run(
                ["git", "ls-files"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if actual_files.returncode != 0:
                fail(errors, kind, f"could not inspect tracked files for {label}: {actual_files.stderr.strip() or actual_files.returncode}")
            else:
                actual = sorted(line for line in actual_files.stdout.splitlines() if line.strip())
                if actual != expected_files:
                    fail(errors, kind, f"tracked file set changed after smoke: expected {expected_files!r}, got {actual!r}")
        except Exception as exc:
            fail(errors, kind, f"could not inspect tracked files for {label}: {exc}")

    for rel, expected in (expected_hashes or {}).items():
        path = repo / rel
        if not path.exists():
            fail(errors, kind, f"tracked file missing after smoke: {rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            fail(errors, kind, f"tracked file hash changed after smoke: {rel}")


def require_stamp_sequence(
    errors: list[str],
    *,
    text: str,
    stamps: list[str],
    label: str,
    kind: str = "verifier",
    allow_codex_footer: bool = False,
    allow_trailing_restatement: bool = False,
    strip_fences: bool = True,
) -> None:
    source = text
    if allow_codex_footer:
        source = strip_token_footer(source)
    if allow_trailing_restatement:
        source = strip_trailing_stamp_restatement(source, stamps)
    if strip_fences:
        source = strip_markdown_fences(source)
    found = [line.strip() for line in source.splitlines() if line.strip().startswith("✓ ")]
    if found != stamps:
        fail(errors, kind, f"{label} must contain exactly the expected aux load stamps in order: {found!r}")


def require_markers(errors: list[str], *, text: str, markers: list[tuple[str, str]], kind: str = "product") -> None:
    for label, pattern in markers:
        if not re.search(pattern, text, re.IGNORECASE):
            fail(errors, kind, f"smoke evidence missing marker: {label}")
