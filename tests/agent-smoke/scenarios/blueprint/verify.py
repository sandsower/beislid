#!/usr/bin/env python3
"""Verify a host-agent blueprint smoke run."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.fixtures import commit_and_push, init_fixture_repo, run, write
from harness.verification import fail

REQUIRED_SECTIONS = [
    "## Status",
    "## Source Requirements",
    "## Recommended Approach",
    "## Alternatives Considered",
    "## Files / Modules",
    "## Data / Control Flow",
    "## Edge Cases and Risks",
    "## Verification Plan",
    "## Open Questions",
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


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata = load_metadata(run_dir)
    repo = Path(metadata["repo"])
    branch = metadata["branch"]
    ticket_id = metadata["ticket_id"]
    artifact_path = metadata["artifact_path"]
    lifecycle_action_log = Path(metadata["lifecycle_action_log"])

    artifact_full_path = repo / artifact_path
    if not artifact_full_path.is_file():
        fail(errors, "product", f"blueprint_approved design artifact missing: {artifact_path}")
        artifact_text = ""
    else:
        artifact_text = artifact_full_path.read_text(encoding="utf-8", errors="replace")

    for section in REQUIRED_SECTIONS:
        if section not in artifact_text:
            fail(errors, "product", f"design artifact missing section: {section!r}")

    if artifact_text and not re.search(r"widget_export\.py", artifact_text):
        fail(errors, "product", "design artifact never grounds itself in the fixture's src/widget_export.py")

    checkpoint_path = repo / ".beislid" / "checkpoints" / "latest.json"
    if not checkpoint_path.is_file():
        fail(errors, "product", f"missing checkpoint pointer: {checkpoint_path}")
    else:
        pointer = load_json(checkpoint_path, errors, "checkpoints/latest.json")
        if pointer is not None:
            latest = pointer.get("latest") or {}
            entry = latest.get("blueprint_approved")
            if not entry:
                fail(errors, "product", "latest.json has no blueprint_approved entry")
            else:
                if entry.get("source_skill") != "blueprint":
                    fail(errors, "product", f"blueprint_approved pointer source_skill must be 'blueprint', got {entry.get('source_skill')!r}")
                if entry.get("event") != "blueprint_approved":
                    fail(errors, "product", f"blueprint_approved pointer event must be 'blueprint_approved', got {entry.get('event')!r}")
                if entry.get("path") != artifact_path:
                    fail(errors, "product", f"blueprint_approved pointer path must be {artifact_path!r}, got {entry.get('path')!r}")
                branch_field = entry.get("branch")
                if branch_field != branch:
                    fail(errors, "product", f"blueprint_approved pointer branch must be {branch!r}, got {branch_field!r}")

    tracked_checkpoints = run(["git", "-C", str(repo), "ls-files", ".beislid/checkpoints"])
    if tracked_checkpoints.strip():
        fail(errors, "product", f"checkpoint pointer must stay untracked, found: {tracked_checkpoints}")

    lifecycle_text = lifecycle_action_log.read_text(encoding="utf-8", errors="replace") if lifecycle_action_log.exists() else ""
    expected_invocation = f"lifecycle-action {ticket_id} {ticket_id} {branch} blueprint_approved {artifact_path}"
    if expected_invocation not in lifecycle_text:
        fail(errors, "product", f"mock lifecycle-action did not run with expected placeholders: {expected_invocation!r}")

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-blueprint-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        origin, repo = init_fixture_repo(run_dir, name="Self Test", email="selftest@example.invalid")
        write(repo / "src" / "widget_export.py", "def export_widgets(items, path):\n    pass\n")
        commit_and_push(repo, "Initial fixture")
        branch = "wid-9-blueprint-smoke"
        run(["git", "checkout", "-b", branch], cwd=repo)

        artifact_path = "plans/widget-export-design.md"
        write(repo / artifact_path, "\n\n".join(
            [f"# Widget export design"] + [f"{section}\ncontent referencing src/widget_export.py" for section in REQUIRED_SECTIONS]
        ) + "\n")
        write(
            repo / ".beislid" / "checkpoints" / "latest.json",
            json.dumps({
                "latest": {
                    "blueprint_approved": {
                        "event": "blueprint_approved",
                        "path": artifact_path,
                        "ticket": {"id": "WID-9"},
                        "branch": branch,
                        "source_skill": "blueprint",
                        "written_at": "2026-01-01T00:00:00Z",
                    }
                }
            }, indent=2) + "\n",
        )

        lifecycle_action_log = run_dir / "lifecycle-action.log"
        write(lifecycle_action_log, f"2026-01-01T00:00:00Z\tcwd={repo}\tlifecycle-action WID-9 WID-9 {branch} blueprint_approved {artifact_path}\n")

        metadata = {
            "repo": str(repo),
            "branch": branch,
            "ticket_id": "WID-9",
            "artifact_path": artifact_path,
            "lifecycle_action_log": str(lifecycle_action_log),
        }
        write(run_dir / "metadata.json", json.dumps(metadata, indent=2) + "\n")

        errors = verify(run_dir)
        if errors:
            print("self-test failed (expected pass):", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        # Negative: drop a required section from the design artifact.
        broken_text = (repo / artifact_path).read_text(encoding="utf-8").replace("## Open Questions\ncontent referencing src/widget_export.py", "")
        write(repo / artifact_path, broken_text)
        negative_errors = verify(run_dir)
        if not any("Open Questions" in error for error in negative_errors):
            print("self-test failed: missing design section should fail", file=sys.stderr)
            return 1

        print("ok: blueprint verify self-test passed")
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
        print("blueprint smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: blueprint agent smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
