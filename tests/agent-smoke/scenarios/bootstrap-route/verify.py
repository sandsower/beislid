#!/usr/bin/env python3
"""Verify a host-agent bootstrap-route smoke run."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.verification import collect_agent_output, fail, require_markers


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
    repo = Path(metadata["repo"])
    expected_step = str(metadata.get("expected_step", "kickoff"))

    agents = (repo / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    workflow = (repo / ".beislid" / "workflow.md").read_text(encoding="utf-8", errors="replace")

    for label, pattern in [
        ("agents read cue", r"Read `\.beislid/workflow\.md` first"),
        ("agents kickoff route", r"kickoff"),
        ("agents blueprint route", r"blueprint"),
        ("agents verify route", r"verify"),
        ("agents ready-for-review route", r"ready-for-review"),
    ]:
        if not re.search(pattern, agents, re.IGNORECASE):
            fail(errors, "artifact", f"AGENTS.md missing {label}")

    if "beislid-workflow: v1" not in workflow:
        fail(errors, "artifact", ".beislid/workflow.md missing version stamp")
    if "branch_pattern" not in workflow:
        fail(errors, "artifact", ".beislid/workflow.md missing branch_pattern")

    host_text = collect_agent_output(run_dir, strip_tokens=True)
    require_markers(
        errors,
        text=host_text,
        markers=[
            ("first-step kickoff", rf"first step:\s*{re.escape(expected_step)}"),
            ("workflow read", r"\.beislid/workflow\.md|workflow\.md"),
            ("ticket/branch state", r"ticket|branch"),
        ],
        kind="verifier",
    )

    return errors


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-bootstrap-route-verify-selftest-") as tmp:
        run_dir = Path(tmp)
        repo = run_dir / "repo"
        repo.mkdir()
        metadata = {
            "repo": str(repo),
            "expected_step": "kickoff",
        }
        write(run_dir / "metadata.json", json.dumps(metadata))
        write(repo / "AGENTS.md", "Read `.beislid/workflow.md` first. kickoff blueprint verify ready-for-review\n")
        write(repo / ".beislid" / "workflow.md", "<!-- beislid-workflow: v1 -->\n\n```beislid:branch_pattern\n^(\\d+)-\n```\n\n## Probe cache\n\n```beislid:probe_cache\nttl_hours: 1\n```\n")

        write(run_dir / "prompt-only.log", "first step: kickoff because branch state says ticket branch\n")
        prompt_errors = verify(run_dir)
        if not any("workflow read" in error for error in prompt_errors):
            print("self-test failed: prompt-only markers should not satisfy AGENTS/workflow checks", file=sys.stderr)
            return 1
        (run_dir / "prompt-only.log").unlink()

        write(run_dir / "codex.log", "\n".join([
            "=== BEISLID_AGENT_SMOKE_OUTPUT ===",
            "first step: kickoff because this is an existing ticket branch",
            "I read .beislid/workflow.md first",
            "ticket branch state",
            "",
        ]))
        errors = verify(run_dir)
        if errors:
            print("self-test failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("ok: bootstrap-route verify self-test passed")
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
        print("bootstrap-route smoke verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("ok: bootstrap-route smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
