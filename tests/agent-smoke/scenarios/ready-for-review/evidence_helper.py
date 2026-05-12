#!/usr/bin/env python3
"""Smoke-only helper for ready-for-review transcript and memory-marker evidence.

This script is intentionally scoped to the agent-smoke ready-for-review scenario. It is
not part of the portable ready-for-review runtime contract.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SECRETISH = re.compile(r"(?i)(token|secret|password|authorization|api[_-]?key)\s*[:=]\s*\S+")
MARKER = "kind: ready-for-review-session-memory-v1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def redact(text: str) -> str:
    text = SECRETISH.sub(lambda m: m.group(0).split(m.group(1), 1)[0] + m.group(1) + "=[REDACTED]", text)
    return text.replace("\x00", "")[:1000]


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_path(transcript: Path) -> Path:
    return transcript.parent / "evidence.json"


def repo_hash(repo: Path) -> str:
    import subprocess

    result = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().splitlines()[0][:12]
    return "unknown-repo"


def command_init(args: argparse.Namespace) -> int:
    state_dir = Path(os.environ.get("BEISLID_STATE_DIR", Path.home() / ".local/state/beislid")).resolve()
    repo = Path(args.repo).resolve()
    hash_value = args.repo_hash or repo_hash(repo)
    run_root = state_dir / "runs" / "ready-for-review" / hash_value
    base_stamp = stamp()
    run_dir = run_root / base_stamp
    suffix = 1
    while run_dir.exists():
        suffix += 1
        run_dir = run_root / f"{base_stamp}-{suffix}"
    run_dir.mkdir(parents=True, exist_ok=False)
    transcript = run_dir / "transcript.md"
    evidence = evidence_path(transcript)
    started = now()
    transcript.write_text(
        "# ready-for-review verbose transcript\n\n"
        f"repo: {repo}\n"
        f"branch: {redact(args.branch)}\n"
        f"base: {redact(args.base)}\n"
        f"ticket_id: `{redact(args.ticket_id)}`\n"
        f"started: {started}\n\n",
        encoding="utf-8",
    )
    payload = {
        "kind": "ready-for-review-smoke-evidence-v1",
        "repo": str(repo),
        "branch": args.branch,
        "base": args.base,
        "ticket_id": args.ticket_id,
        "transcript": str(transcript),
        "started_at": started,
        "events": [],
        "finalized": False,
    }
    write_json(evidence, payload)
    print(f"TRANSCRIPT_PATH={transcript}")
    print(f"EVIDENCE_PATH={evidence}")
    return 0


def command_event(args: argparse.Namespace) -> int:
    transcript = Path(args.transcript).resolve()
    evidence = evidence_path(transcript)
    if not transcript.exists() or not evidence.exists():
        print("transcript/evidence not initialized", file=sys.stderr)
        return 2
    title = redact(args.title)
    summary = redact(args.summary)
    phase_match = re.search(r"phase[-_ ]?(\d)", f"{title} {summary}", re.IGNORECASE)
    normalized_phase = f"\n- phase {phase_match.group(1)} boundary" if phase_match else ""
    with transcript.open("a", encoding="utf-8") as f:
        f.write(f"\n## {title}\n- {summary}{normalized_phase}\n")
    payload = read_json(evidence)
    payload.setdefault("events", []).append({"timestamp": now(), "title": title, "summary": summary})
    write_json(evidence, payload)
    print(f"EVENT_RECORDED={title}")
    return 0


def command_finalize(args: argparse.Namespace) -> int:
    transcript = Path(args.transcript).resolve()
    evidence = evidence_path(transcript)
    if not transcript.exists() or not evidence.exists():
        print("transcript/evidence not initialized", file=sys.stderr)
        return 2
    text = transcript.read_text(encoding="utf-8", errors="replace")
    payload = read_json(evidence)
    loaded_aux = args.loaded_aux or []
    memory = {
        "kind": "ready-for-review-session-memory-v1",
        "summary": args.summary,
        "repo": payload.get("repo", "unknown"),
        "branch": args.branch or payload.get("branch", "unknown"),
        "base": args.base or payload.get("base", "unknown"),
        "ticket": {"id": args.ticket_id or payload.get("ticket_id", "none"), "title": args.ticket_title, "url": args.ticket_url},
        "pr": {"url": args.pr_url, "title": args.pr_title, "base": args.base or payload.get("base", "unknown")},
        "phase_path": args.phase_path,
        "evidence": {
            "loaded_aux_files": loaded_aux,
            "transcript": str(transcript),
            "gates": args.gates,
            "review": args.review,
        },
        "decisions": {
            "accepted_risks": args.accepted_risk,
            "reduced_review_coverage": args.reduced_review_coverage,
            "domain_capture": args.domain_capture,
        },
        "side_effects": args.side_effect,
        "runtime": {"host": args.host, "timestamp": now(), "duration": args.duration},
    }
    payload["memory"] = memory
    payload["finalized"] = True
    payload["finalized_at"] = now()
    write_json(evidence, payload)
    if MARKER not in text:
        with transcript.open("a", encoding="utf-8") as f:
            f.write("\n## Structured session memory\n")
            f.write(f"{MARKER}\n")
            f.write("```json\n")
            f.write(json.dumps(memory, indent=2, sort_keys=True) + "\n")
            f.write("```\n")
    print(f"MEMORY_MARKER={MARKER}")
    return 0


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="beislid-ready-for-review-evidence-helper-") as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "repo"
        repo.mkdir()
        os.environ["BEISLID_STATE_DIR"] = str(tmp_path / "state")
        init_args = argparse.Namespace(repo=str(repo), branch="agent-smoke/no-ticket-verbose", base="main", ticket_id="none", repo_hash="abc123")
        command_init(init_args)
        transcripts = sorted((tmp_path / "state").glob("runs/ready-for-review/*/*/transcript.md"))
        if len(transcripts) != 1:
            print("self-test expected one transcript", file=sys.stderr)
            return 1
        transcript = transcripts[0]
        command_event(argparse.Namespace(transcript=str(transcript), title="phase-1-detect", summary="phase 1 loaded"))
        finalize_args = argparse.Namespace(
            transcript=str(transcript),
            summary="smoke ready for review",
            branch="agent-smoke/no-ticket-verbose",
            base="main",
            ticket_id="none",
            ticket_title="none",
            ticket_url="",
            pr_url="https://example.invalid/beislid-smoke/pull/1",
            pr_title="Smoke",
            phase_path="new-pr-fast-path",
            gates="parallel validate-fixture ok",
            review="combined review/fresh-eyes complete",
            accepted_risk=[],
            reduced_review_coverage="none",
            domain_capture="not configured",
            side_effect=["push", "PR create"],
            loaded_aux=["phase-1-detect", "phase-2-gates", "phase-3-review", "phase-4-submit"],
            host="self-test",
            duration="1s",
        )
        command_finalize(finalize_args)
        command_finalize(finalize_args)
        text = transcript.read_text(encoding="utf-8")
        if text.count(MARKER) != 1:
            print("self-test expected exactly one memory marker", file=sys.stderr)
            return 1
        evidence = read_json(evidence_path(transcript))
        if not evidence.get("finalized") or evidence.get("memory", {}).get("kind") != MARKER.split(": ", 1)[1]:
            print("self-test expected finalized evidence memory", file=sys.stderr)
            return 1
        print("ok: evidence helper self-test passed")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init")
    init_p.add_argument("--repo", required=True)
    init_p.add_argument("--branch", required=True)
    init_p.add_argument("--base", default="main")
    init_p.add_argument("--ticket-id", default="none")
    init_p.add_argument("--repo-hash")
    init_p.set_defaults(func=command_init)

    event_p = sub.add_parser("event")
    event_p.add_argument("--transcript", required=True)
    event_p.add_argument("--title", required=True)
    event_p.add_argument("--summary", required=True)
    event_p.set_defaults(func=command_event)

    final_p = sub.add_parser("finalize")
    final_p.add_argument("--transcript", required=True)
    final_p.add_argument("--summary", required=True)
    final_p.add_argument("--branch")
    final_p.add_argument("--base")
    final_p.add_argument("--ticket-id")
    final_p.add_argument("--ticket-title", default="none")
    final_p.add_argument("--ticket-url", default="")
    final_p.add_argument("--pr-url", default="")
    final_p.add_argument("--pr-title", default="")
    final_p.add_argument("--phase-path", default="new-pr")
    final_p.add_argument("--gates", default="unknown")
    final_p.add_argument("--review", default="unknown")
    final_p.add_argument("--accepted-risk", action="append", default=[])
    final_p.add_argument("--reduced-review-coverage", default="none")
    final_p.add_argument("--domain-capture", default="unknown")
    final_p.add_argument("--side-effect", action="append", default=[])
    final_p.add_argument("--loaded-aux", action="append", default=[])
    final_p.add_argument("--host", default="unknown")
    final_p.add_argument("--duration", default="unknown")
    final_p.set_defaults(func=command_finalize)

    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
