#!/usr/bin/env python3
"""Verify a host-agent implement smoke run."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_and_push, commit_only, init_fixture_repo, run, write
from harness.verification import collect_agent_output, fail, require_stamp_sequence, run_test_functions

CODEX_CONTEXT_STAMP = "✓ implement/codex-delegate-context v1 loaded"

REQUIRED_SECTIONS = [
    "Checkpoint Metadata",
    "State Summary",
    "Key Context",
    "Decisions",
    "Next Step",
    "Open Risks / Questions",
]


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_json(path: Path, errors: list[str], label: str) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(errors, "artifact", f"{label}: unreadable or invalid JSON ({exc})")
        return None
    if not isinstance(payload, dict):
        fail(errors, "artifact", f"{label}: top level must be a JSON object")
        return None
    return payload


def smoke_host(run_dir: Path) -> str | None:
    path = run_dir / "agent-smoke.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    host = payload.get("host")
    return host if isinstance(host, str) else None


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    repo = Path(metadata["repo"])
    branch = metadata["branch"]
    checkpoint_path = metadata["checkpoint_path"]
    initial_head = metadata["initial_head"]

    checkpoint_full_path = repo / checkpoint_path
    if not checkpoint_full_path.is_file():
        fail(errors, "product", f"implementation plan checkpoint missing: {checkpoint_path}")
        checkpoint_text = ""
    else:
        checkpoint_text = checkpoint_full_path.read_text(encoding="utf-8", errors="replace")
    for section in REQUIRED_SECTIONS:
        if section not in checkpoint_text:
            fail(errors, "product", f"implementation plan checkpoint missing section: {section!r}")

    latest_path = repo / ".beislid" / "checkpoints" / "latest.json"
    if not latest_path.is_file():
        fail(errors, "product", f"missing checkpoint pointer: {latest_path}")
    else:
        pointer = load_json(latest_path, errors, "checkpoints/latest.json")
        if pointer is not None:
            entry = (pointer.get("latest") or {}).get("implementation_plan_created")
            if not entry:
                fail(errors, "product", "latest.json has no implementation_plan_created entry")
            else:
                if entry.get("source_skill") != "implement":
                    fail(errors, "product", f"implementation_plan_created pointer source_skill must be 'implement', got {entry.get('source_skill')!r}")
                if entry.get("path") != checkpoint_path:
                    fail(errors, "product", f"implementation_plan_created pointer path must be {checkpoint_path!r}, got {entry.get('path')!r}")
                if entry.get("branch") != branch:
                    fail(errors, "product", f"implementation_plan_created pointer branch must be {branch!r}, got {entry.get('branch')!r}")

    tracked_checkpoints = run(["git", "-C", str(repo), "ls-files", ".beislid/checkpoints"])
    if tracked_checkpoints.strip():
        fail(errors, "product", f"checkpoint pointer must stay untracked, found: {tracked_checkpoints}")

    head = run(["git", "-C", str(repo), "rev-parse", "HEAD"])
    if head == initial_head:
        fail(errors, "product", "no commit was made after the initial fixture commit")

    test_file = repo / "tests" / "test_widget_export.py"
    test_failures = run_test_functions(test_file, repo)
    for failure in test_failures:
        fail(errors, "product", f"tests/test_widget_export.py: {failure}")

    if smoke_host(run_dir) == "codex":
        host_text = collect_agent_output(run_dir, strip_tokens=True)
        require_stamp_sequence(
            errors,
            text=host_text,
            stamps=[CODEX_CONTEXT_STAMP],
            label="agent output",
            kind="verifier",
        )

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-implement-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        origin, repo = init_fixture_repo(run_dir, name="Self Test", email="selftest@example.invalid")
        write(repo / "src" / "__init__.py", "")
        write(repo / "tests" / "__init__.py", "")
        write(repo / "src" / "widget_export.py", """import csv


def widgets():
    return [{"name": "alpha", "status": "open"}]


def export_widgets(items, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["name", "status"])
        for item in items:
            writer.writerow([item["name"], item["status"]])
""")
        write(repo / "tests" / "test_widget_export.py", """from src.widget_export import widgets


def test_widgets_have_status():
    assert widgets()[0]["status"] == "open"
""")
        commit_and_push(repo, "Initial fixture")
        branch = "wid-9-implement-smoke"
        run(["git", "checkout", "-b", branch], cwd=repo)
        initial_head = run(["git", "rev-parse", "HEAD"], cwd=repo)

        checkpoint_path = "checkpoints/implementation_plan_created-WID-9.md"
        write(repo / checkpoint_path, "\n".join(
            ["# Implementation plan checkpoint", ""] + [f"## {section}\ncontent" for section in REQUIRED_SECTIONS]
        ) + "\n")
        write(
            repo / ".beislid" / "checkpoints" / "latest.json",
            json.dumps({
                "latest": {
                    "implementation_plan_created": {
                        "event": "implementation_plan_created",
                        "path": checkpoint_path,
                        "ticket": {"id": "WID-9"},
                        "branch": branch,
                        "source_skill": "implement",
                        "written_at": "2026-01-01T00:00:00Z",
                    }
                }
            }, indent=2) + "\n",
        )

        # Real implementation: export_widgets gains a working tax_rate column.
        write(repo / "src" / "widget_export.py", """import csv


def widgets():
    return [{"name": "alpha", "status": "open"}]


def export_widgets(items, path, tax_rate=None):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        header = ["name", "status"] + (["tax_rate"] if tax_rate is not None else [])
        writer.writerow(header)
        for item in items:
            row = [item["name"], item["status"]] + ([tax_rate] if tax_rate is not None else [])
            writer.writerow(row)
""")
        write(repo / "tests" / "test_widget_export.py", """import csv
import os
import tempfile

from src.widget_export import export_widgets, widgets


def test_widgets_have_status():
    assert widgets()[0]["status"] == "open"


def test_export_widgets_with_tax_rate():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        export_widgets([{"name": "alpha", "status": "open"}], path, tax_rate=0.1)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert rows[0] == ["name", "status", "tax_rate"]
        assert rows[1][2] == "0.1"
    finally:
        os.unlink(path)
""")
        commit_only(repo, "Add tax_rate support to widget export", paths=["src/widget_export.py", "tests/test_widget_export.py"])

        metadata = {
            "repo": str(repo),
            "branch": branch,
            "checkpoint_path": checkpoint_path,
            "initial_head": initial_head,
        }
        write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")
        write(run_dir / "agent-smoke.json", json.dumps({"host": "codex"}) + "\n")
        write(run_dir / "agent.log", CODEX_CONTEXT_STAMP + "\n")

        errors = verify(run_dir)
        if errors:
            print("self-test failed (expected pass):", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        write(run_dir / "agent.log", "implemented without loading the Codex context protocol\n")
        missing_stamp_errors = verify(run_dir)
        if not any("expected aux load stamps" in error for error in missing_stamp_errors):
            print("self-test failed: missing Codex context stamp should fail", file=sys.stderr)
            for error in missing_stamp_errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        write(run_dir / "agent.log", CODEX_CONTEXT_STAMP + "\n")

        # Negative: implementation silently ignores tax_rate (a plausible half-done
        # attempt) - the real test execution must catch it even though the checkpoint
        # and pointer are otherwise fine.
        write(repo / "src" / "widget_export.py", """import csv


def widgets():
    return [{"name": "alpha", "status": "open"}]


def export_widgets(items, path, tax_rate=None):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["name", "status"])
        for item in items:
            writer.writerow([item["name"], item["status"]])
""")
        negative_errors = verify(run_dir)
        if not any("test_export_widgets_with_tax_rate" in error for error in negative_errors):
            print("self-test failed: broken tax_rate implementation should fail the real test run", file=sys.stderr)
            for error in negative_errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        print("ok: implement verify self-test passed")
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
        print("implement smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: implement agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
