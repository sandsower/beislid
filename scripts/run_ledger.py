#!/usr/bin/env python3
"""Durable Beislið run ledger utility.

Stores run state outside the repo by default:
${BEISLID_STATE_DIR:-~/.local/state/beislid}/runs/<repo_hash>/<run_id>/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SECRETISH = re.compile(r"(?i)(token|secret|password|authorization|api[_-]?key)\s*[:=]\s*\S+")
SECRETISH_JSON_KEY = re.compile(r"(?i)(token|secret|password|authorization|api[_-]?key)")
VALID_STATUSES = {"active", "interrupted", "failed", "completed"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def state_dir() -> Path:
    return Path(os.environ.get("BEISLID_STATE_DIR", Path.home() / ".local" / "state" / "beislid")).resolve()


def run_id() -> str:
    return f"{stamp()}-{secrets.token_hex(3)}"


def redact_text(text: str, limit: int = 2000) -> str:
    redacted = SECRETISH.sub(lambda m: f"{m.group(1)}=[REDACTED]", text.replace("\x00", ""))
    return redacted[:limit]


def redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if SECRETISH_JSON_KEY.search(str(k)) else redact_json(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_json(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repo_root(cwd: Path | None = None) -> Path:
    cwd = cwd or Path.cwd()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return cwd.resolve()


def repo_hash(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        roots = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
        if roots:
            return roots[0][:12]
    return "unknown-repo"


def current_branch(repo: Path) -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "unknown"


def run_root_for_repo(hash_value: str) -> Path:
    return state_dir() / "runs" / hash_value


def find_run_dir(rid: str, repo: Path | None = None) -> Path:
    roots: list[Path]
    if repo is not None:
        roots = [run_root_for_repo(repo_hash(repo))]
    else:
        roots = sorted((state_dir() / "runs").glob("*")) if (state_dir() / "runs").exists() else []
    matches = [root / rid for root in roots if (root / rid / "run.json").is_file()]
    if not matches:
        raise SystemExit(f"run not found: {rid}")
    if len(matches) > 1:
        raise SystemExit(f"run id is ambiguous across repositories: {rid}")
    return matches[0]


def load_payload(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return read_json(Path(path))


def append_event(run_dir: Path, event_type: str, payload: dict[str, Any], transcript_summary: str | None = None) -> dict[str, Any]:
    safe_payload = redact_json(payload)
    event = {"timestamp": now(), "type": event_type, "payload": safe_payload}
    with (run_dir / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    summary = transcript_summary or json.dumps(safe_payload, sort_keys=True)
    with (run_dir / "transcript.md").open("a", encoding="utf-8") as f:
        f.write(f"\n## {redact_text(event_type, 160)}\n- {redact_text(summary)}\n")
    run = read_json(run_dir / "run.json")
    run.setdefault("events", {})["count"] = int(run.get("events", {}).get("count", 0)) + 1
    run["updated_at"] = event["timestamp"]
    write_json(run_dir / "run.json", run)
    return event


def command_init(args: argparse.Namespace) -> int:
    repo = repo_root(Path.cwd())
    hash_value = repo_hash(repo)
    rid = args.run_id or run_id()
    root = run_root_for_repo(hash_value)
    rdir = root / rid
    suffix = 1
    while rdir.exists():
        suffix += 1
        rid = f"{args.run_id or run_id()}-{suffix}"
        rdir = root / rid
    for sub in ("artifacts", "logs", "checkpoints"):
        (rdir / sub).mkdir(parents=True, exist_ok=False)
    started = now()
    ticket = {"id": args.ticket_id or "none", "title": args.ticket_title or "none", "url": args.ticket_url or ""}
    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": rid,
        "repo": str(repo),
        "repo_hash": hash_value,
        "branch": args.branch or current_branch(repo),
        "skill": args.skill,
        "ticket": ticket,
        "status": "active",
        "started_at": started,
        "updated_at": started,
        "paths": {
            "run_dir": str(rdir),
            "transcript": str(rdir / "transcript.md"),
            "events": str(rdir / "events.jsonl"),
            "final_report": str(rdir / "final-report.md"),
        },
        "selected_guides": [],
        "plan": None,
        "current_step": None,
        "artifacts": [],
        "logs": [],
        "events": {"count": 0},
    }
    write_json(rdir / "run.json", run)
    (rdir / "events.jsonl").write_text("", encoding="utf-8")
    (rdir / "transcript.md").write_text(
        "# Beislið run transcript\n\n"
        f"run_id: `{rid}`\n"
        f"repo: {repo}\n"
        f"branch: {redact_text(run['branch'])}\n"
        f"ticket_id: `{redact_text(ticket['id'])}`\n"
        f"skill: {redact_text(args.skill)}\n"
        f"started: {started}\n",
        encoding="utf-8",
    )
    append_event(rdir, "run_initialized", {"skill": args.skill, "ticket": ticket, "branch": run["branch"]})
    print(json.dumps({"run_id": rid, "run_dir": str(rdir), "run_json": str(rdir / "run.json")}, sort_keys=True))
    return 0


def command_event(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()))
    payload = load_payload(args.json_file)
    append_event(rdir, args.type, payload, args.summary)
    print(json.dumps({"run_id": args.run_id, "event_type": args.type}, sort_keys=True))
    return 0


def command_checkpoint(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()))
    payload = load_payload(args.json_file)
    checkpoint_path = rdir / "checkpoints" / f"{args.name}.json"
    write_json(checkpoint_path, {"name": args.name, "timestamp": now(), "payload": redact_json(payload)})
    run = read_json(rdir / "run.json")
    run["latest_checkpoint"] = {"name": args.name, "path": str(checkpoint_path), "timestamp": now()}
    run["current_step"] = args.name
    write_json(rdir / "run.json", run)
    append_event(rdir, "checkpoint", {"name": args.name, "path": str(checkpoint_path), "payload": payload})
    print(json.dumps({"run_id": args.run_id, "checkpoint": str(checkpoint_path)}, sort_keys=True))
    return 0


def command_gate(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()))
    envelope = load_payload(args.envelope_file)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", args.name).strip("-") or "gate"
    log_path = rdir / "logs" / f"{safe_name}.json"
    write_json(log_path, redact_json(envelope))
    run = read_json(rdir / "run.json")
    run.setdefault("logs", []).append({"name": args.name, "path": str(log_path), "kind": "gate"})
    write_json(rdir / "run.json", run)
    append_event(rdir, "gate_result", {"name": args.name, "path": str(log_path), "envelope": envelope})
    print(json.dumps({"run_id": args.run_id, "gate_log": str(log_path)}, sort_keys=True))
    return 0


def command_interrupt(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()))
    run = read_json(rdir / "run.json")
    run["status"] = "interrupted"
    run["interruption"] = {"timestamp": now(), "reason": args.reason}
    write_json(rdir / "run.json", run)
    append_event(rdir, "interrupted", {"reason": args.reason})
    print(json.dumps({"run_id": args.run_id, "status": "interrupted"}, sort_keys=True))
    return 0


def command_finalize(args: argparse.Namespace) -> int:
    if args.status not in VALID_STATUSES - {"active"}:
        raise SystemExit(f"invalid final status: {args.status}")
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()))
    report_path = None
    if args.report_file:
        report_path = rdir / "final-report.md"
        shutil.copyfile(args.report_file, report_path)
    run = read_json(rdir / "run.json")
    run["status"] = args.status
    run["finalized_at"] = now()
    if report_path:
        run["paths"]["final_report"] = str(report_path)
    write_json(rdir / "run.json", run)
    append_event(rdir, "finalized", {"status": args.status, "final_report": str(report_path) if report_path else None})
    print(json.dumps({"run_id": args.run_id, "status": args.status, "final_report": str(report_path) if report_path else None}, sort_keys=True))
    return 0


def command_resume(args: argparse.Namespace) -> int:
    repo = repo_root(Path.cwd())
    root = run_root_for_repo(repo_hash(repo))
    allowed = VALID_STATUSES if args.include_completed else {"active", "interrupted", "failed"}
    candidates: list[dict[str, Any]] = []
    for run_file in sorted(root.glob("*/run.json")) if root.exists() else []:
        try:
            run = read_json(run_file)
        except Exception:
            continue
        if run.get("status") not in allowed:
            continue
        if args.ticket_id and str(run.get("ticket", {}).get("id")) != str(args.ticket_id):
            continue
        if args.branch and run.get("branch") != args.branch:
            continue
        candidates.append(run)
    if not candidates:
        raise SystemExit("no matching run found")
    candidates.sort(key=lambda r: r.get("updated_at") or r.get("started_at") or "")
    selected = candidates[-1]
    print(json.dumps({
        "run_id": selected["run_id"],
        "run_dir": selected["paths"]["run_dir"],
        "status": selected["status"],
        "ticket": selected.get("ticket"),
        "branch": selected.get("branch"),
        "latest_checkpoint": selected.get("latest_checkpoint"),
    }, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init")
    init_p.add_argument("--skill", required=True)
    init_p.add_argument("--ticket-id", default="none")
    init_p.add_argument("--ticket-title", default="none")
    init_p.add_argument("--ticket-url", default="")
    init_p.add_argument("--branch")
    init_p.add_argument("--run-id")
    init_p.set_defaults(func=command_init)

    event_p = sub.add_parser("event")
    event_p.add_argument("--run-id", required=True)
    event_p.add_argument("--type", required=True)
    event_p.add_argument("--json-file")
    event_p.add_argument("--summary")
    event_p.set_defaults(func=command_event)

    checkpoint_p = sub.add_parser("checkpoint")
    checkpoint_p.add_argument("--run-id", required=True)
    checkpoint_p.add_argument("--name", required=True)
    checkpoint_p.add_argument("--json-file")
    checkpoint_p.set_defaults(func=command_checkpoint)

    gate_p = sub.add_parser("gate")
    gate_p.add_argument("--run-id", required=True)
    gate_p.add_argument("--name", required=True)
    gate_p.add_argument("--envelope-file", required=True)
    gate_p.set_defaults(func=command_gate)

    interrupt_p = sub.add_parser("interrupt")
    interrupt_p.add_argument("--run-id", required=True)
    interrupt_p.add_argument("--reason", required=True)
    interrupt_p.set_defaults(func=command_interrupt)

    final_p = sub.add_parser("finalize")
    final_p.add_argument("--run-id", required=True)
    final_p.add_argument("--status", required=True)
    final_p.add_argument("--report-file")
    final_p.set_defaults(func=command_finalize)

    resume_p = sub.add_parser("resume")
    resume_p.add_argument("--ticket-id")
    resume_p.add_argument("--branch")
    resume_p.add_argument("--include-completed", action="store_true")
    resume_p.set_defaults(func=command_resume)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
