#!/usr/bin/env python3
"""Durable Beislið run ledger utility.

Stores run state outside the repo by default:
${BEISLID_STATE_DIR:-~/.local/state/beislid}/runs/<flow>/<repo_hash>/<run_id>/
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
LEDGER_KIND = "run-ledger-v1"
CHECKPOINT_KIND = "run-ledger-checkpoint-v1"
SECRETISH_ASSIGNMENT = re.compile(
    r"(?i)\b((?:[a-z0-9]+[_-])*(?:api[_-]?key|token|secret|password|private[_-]?key|auth[_-]?header)"
    r"(?:[_-][a-z0-9]+)*)\b\s*[:=]\s*"
    r"(\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;)}\]]+)"
)
SECRETISH_BEARER = re.compile(
    r"(?i)(authorization\s*:\s*bearer\s+)(\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;)}\]]+)"
)
SECRETISH_ENV = re.compile(r"(?i)\$\{?(TOKEN|SECRET|PASSWORD|API[_-]?KEY|AUTH|GITHUB_TOKEN)\}?")
SECRETISH_JSON_KEY = re.compile(
    r"(?i)\b(?:[a-z0-9]+[_-])*(?:api[_-]?key|token|secret|password|authorization|private[_-]?key|auth[_-]?header)"
    r"(?:[_-][a-z0-9]+)*\b"
)
VALID_STATUSES = {"running", "interrupted", "failed", "completed"}
INCOMPLETE_STATUSES = {"running", "interrupted", "failed", "active"}
RUN_ID_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def state_dir() -> Path:
    return Path(os.environ.get("BEISLID_STATE_DIR", Path.home() / ".local" / "state" / "beislid")).resolve()


def new_run_id() -> str:
    return f"{stamp()}-{secrets.token_hex(3)}"


def validate_run_id(value: str) -> str:
    if not RUN_ID_SEGMENT.fullmatch(value) or value in {".", ".."}:
        raise SystemExit("invalid run id: use a single path-safe segment [A-Za-z0-9_.-]")
    return value


def slug(value: str, fallback: str = "item") -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-._")
    return safe or fallback


def redact_text(text: str, limit: int = 2000) -> str:
    redacted = text.replace("\x00", "")
    redacted = SECRETISH_BEARER.sub(lambda m: f"{m.group(1)}[REDACTED]", redacted)
    redacted = SECRETISH_ASSIGNMENT.sub(lambda m: f"{m.group(1)}=[REDACTED]", redacted)
    redacted = SECRETISH_ENV.sub("[REDACTED]", redacted)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{secrets.token_hex(4)}.tmp"
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        with tmp.open("w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        if tmp.exists():
            tmp.unlink()


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


def normalize_flow(flow: str | None, skill: str | None = None) -> str:
    return slug(flow or skill or "run", "run")


def run_root_for_repo(flow: str, hash_value: str) -> Path:
    return state_dir() / "runs" / normalize_flow(flow) / hash_value


def candidate_roots(repo: Path | None = None, flow: str | None = None) -> list[Path]:
    runs_root = state_dir() / "runs"
    if repo is not None and flow:
        return [run_root_for_repo(flow, repo_hash(repo))]
    if repo is not None:
        hash_value = repo_hash(repo)
        roots = [path / hash_value for path in sorted(runs_root.glob("*"))] if runs_root.exists() else []
        legacy_root = runs_root / hash_value
        if legacy_root.exists():
            roots.append(legacy_root)
        return roots
    if flow:
        flow_root = runs_root / normalize_flow(flow)
        return sorted(flow_root.glob("*")) if flow_root.exists() else []
    return sorted(runs_root.glob("*/*")) if runs_root.exists() else []


def find_run_dir(rid: str, repo: Path | None = None, flow: str | None = None) -> Path:
    matches = [root / rid for root in candidate_roots(repo, flow) if (root / rid / "run.json").is_file()]
    if not matches:
        raise SystemExit(f"run not found: {rid}")
    if len(matches) > 1:
        raise SystemExit(f"run id is ambiguous; pass --flow to disambiguate: {rid}")
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
    if transcript_summary is None:
        summary = json.dumps(safe_payload, sort_keys=True)[:2000]
    else:
        summary = redact_text(transcript_summary)
    with (run_dir / "transcript.md").open("a", encoding="utf-8") as f:
        f.write(f"\n## {redact_text(event_type, 160)}\n- {summary}\n")
    run = read_json(run_dir / "run.json")
    run.setdefault("events", {})["count"] = int(run.get("events", {}).get("count", 0)) + 1
    run["updated_at"] = event["timestamp"]
    write_json(run_dir / "run.json", run)
    return event


def checkpoint_payload(name: str, payload: dict[str, Any], resume_hint: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "kind": CHECKPOINT_KIND,
        "checkpoint": name,
        "timestamp": now(),
        "payload": redact_json(payload),
    }
    if resume_hint:
        body["resume_hint"] = redact_text(resume_hint, 500)
    return body


def record_checkpoint(run_dir: Path, name: str, payload: dict[str, Any], resume_hint: str | None = None) -> Path:
    checkpoint_path = run_dir / "checkpoints" / f"{slug(name, 'checkpoint')}.json"
    write_json(checkpoint_path, checkpoint_payload(name, payload, resume_hint))
    run = read_json(run_dir / "run.json")
    entry = {"name": name, "path": str(checkpoint_path), "timestamp": now()}
    if resume_hint:
        entry["resume_hint"] = redact_text(resume_hint, 500)
        run["resume_hint"] = entry["resume_hint"]
    run["latest_checkpoint"] = entry
    run["last_checkpoint"] = str(checkpoint_path)
    run["current_step"] = name
    run.setdefault("checkpoints", []).append(str(checkpoint_path))
    write_json(run_dir / "run.json", run)
    return checkpoint_path


def next_attempt_dir(gate_root: Path) -> Path:
    attempt = 1
    while (gate_root / str(attempt)).exists():
        attempt += 1
    path = gate_root / str(attempt)
    path.mkdir(parents=True, exist_ok=False)
    return path


def command_init(args: argparse.Namespace) -> int:
    repo = repo_root(Path.cwd())
    hash_value = repo_hash(repo)
    flow = normalize_flow(args.flow, args.skill)
    rid = validate_run_id(args.run_id) if args.run_id else new_run_id()
    root = run_root_for_repo(flow, hash_value)
    rdir = root / rid
    suffix = 1
    while rdir.exists():
        suffix += 1
        rid = f"{validate_run_id(args.run_id) if args.run_id else new_run_id()}-{suffix}"
        rdir = root / rid
    for sub in ("artifacts", "artifacts/gates", "artifacts/reviews", "logs", "checkpoints"):
        (rdir / sub).mkdir(parents=True, exist_ok=False)
    started = now()
    ticket = {"id": args.ticket_id or "none", "title": args.ticket_title or "none", "url": args.ticket_url or ""}
    run = {
        "kind": LEDGER_KIND,
        "schema_version": SCHEMA_VERSION,
        "run_id": rid,
        "flow": flow,
        "repo": str(repo),
        "repo_hash": hash_value,
        "branch": args.branch or current_branch(repo),
        "skill": args.skill,
        "ticket": ticket,
        "ticket_id": ticket["id"],
        "status": "running",
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
        "checkpoints": [],
        "artifacts": [],
        "logs": [],
        "accepted_risks": [],
        "side_effects": [],
        "events": {"count": 0},
    }
    write_json(rdir / "run.json", run)
    (rdir / "events.jsonl").write_text("", encoding="utf-8")
    (rdir / "transcript.md").write_text(
        "# Beislið run transcript\n\n"
        f"kind: `{LEDGER_KIND}`\n"
        f"run_id: `{rid}`\n"
        f"flow: `{flow}`\n"
        f"repo: {repo}\n"
        f"branch: {redact_text(run['branch'])}\n"
        f"ticket_id: `{redact_text(ticket['id'])}`\n"
        f"skill: {redact_text(args.skill)}\n"
        f"started: {started}\n",
        encoding="utf-8",
    )
    append_event(rdir, "run_initialized", {"skill": args.skill, "flow": flow, "ticket": ticket, "branch": run["branch"]})
    print(json.dumps({"run_id": rid, "flow": flow, "run_dir": str(rdir), "run_json": str(rdir / "run.json")}, sort_keys=True))
    return 0


def command_event(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()), args.flow)
    payload = load_payload(args.json_file)
    append_event(rdir, args.type, payload, args.summary)
    print(json.dumps({"run_id": args.run_id, "event_type": args.type}, sort_keys=True))
    return 0


def command_checkpoint(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()), args.flow)
    payload = load_payload(args.json_file)
    checkpoint_path = record_checkpoint(rdir, args.name, payload, args.resume_hint)
    append_event(rdir, "checkpoint", {"name": args.name, "path": str(checkpoint_path), "payload": payload, "resume_hint": args.resume_hint})
    print(json.dumps({"run_id": args.run_id, "checkpoint": str(checkpoint_path)}, sort_keys=True))
    return 0


def command_gate(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()), args.flow)
    envelope = load_payload(args.envelope_file)
    scope = slug(args.scope or envelope.get("gate", {}).get("scope", "repo"), "repo")
    safe_name = slug(args.name, "gate")
    attempt_dir = next_attempt_dir(rdir / "artifacts" / "gates" / scope / safe_name)
    envelope_path = attempt_dir / "envelope.json"
    write_json(envelope_path, redact_json(envelope))
    run = read_json(rdir / "run.json")
    artifact = {"name": args.name, "path": str(envelope_path), "kind": "gate", "scope": scope}
    run.setdefault("artifacts", []).append(artifact)
    run.setdefault("logs", []).append(artifact)
    write_json(rdir / "run.json", run)
    checkpoint_path = record_checkpoint(
        rdir,
        f"gate-{scope}-{safe_name}",
        {"name": args.name, "scope": scope, "path": str(envelope_path), "status": envelope.get("status"), "envelope": envelope},
        args.resume_hint or "continue after reviewing gate result",
    )
    append_event(rdir, "gate_result", {"name": args.name, "scope": scope, "path": str(envelope_path), "checkpoint": str(checkpoint_path), "envelope": envelope})
    print(json.dumps({"run_id": args.run_id, "gate_log": str(envelope_path), "checkpoint": str(checkpoint_path)}, sort_keys=True))
    return 0


def command_interrupt(args: argparse.Namespace) -> int:
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()), args.flow)
    checkpoint_path = record_checkpoint(rdir, "interrupted", {"reason": args.reason}, args.resume_hint)
    run = read_json(rdir / "run.json")
    run["status"] = "interrupted"
    run["interruption"] = {"timestamp": now(), "reason": redact_text(args.reason), "checkpoint": str(checkpoint_path)}
    if args.resume_hint:
        run["resume_hint"] = redact_text(args.resume_hint, 500)
    write_json(rdir / "run.json", run)
    append_event(rdir, "interrupted", {"reason": args.reason, "resume_hint": args.resume_hint, "checkpoint": str(checkpoint_path)})
    print(json.dumps({"run_id": args.run_id, "status": "interrupted", "checkpoint": str(checkpoint_path)}, sort_keys=True))
    return 0


def command_finalize(args: argparse.Namespace) -> int:
    if args.status not in VALID_STATUSES - {"running"}:
        raise SystemExit(f"invalid final status: {args.status}")
    rdir = find_run_dir(args.run_id, repo_root(Path.cwd()), args.flow)
    report_path = None
    if args.report_file:
        report_path = rdir / "final-report.md"
        shutil.copyfile(args.report_file, report_path)
    checkpoint_path = record_checkpoint(
        rdir,
        "final-report",
        {"status": args.status, "final_report": str(report_path) if report_path else None},
        "run complete" if args.status == "completed" else "inspect final status before resuming",
    )
    run = read_json(rdir / "run.json")
    run["status"] = args.status
    run["finalized_at"] = now()
    if report_path:
        run["paths"]["final_report"] = str(report_path)
    write_json(rdir / "run.json", run)
    append_event(rdir, "finalized", {"status": args.status, "final_report": str(report_path) if report_path else None, "checkpoint": str(checkpoint_path)})
    print(json.dumps({"run_id": args.run_id, "status": args.status, "final_report": str(report_path) if report_path else None}, sort_keys=True))
    return 0


def command_resume(args: argparse.Namespace) -> int:
    repo = repo_root(Path.cwd())
    allowed = VALID_STATUSES | {"active"} if args.include_completed else INCOMPLETE_STATUSES
    candidates: list[dict[str, Any]] = []
    for root in candidate_roots(repo, args.flow):
        for run_file in sorted(root.glob("*/run.json")) if root.exists() else []:
            try:
                run = read_json(run_file)
            except (OSError, json.JSONDecodeError) as exc:
                print(f"warning: skipping unreadable run file {run_file}: {exc}", file=sys.stderr)
                continue
            if run.get("status") not in allowed:
                continue
            if args.ticket_id and str(run.get("ticket_id") or run.get("ticket", {}).get("id")) != str(args.ticket_id):
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
        "flow": selected.get("flow"),
        "run_dir": selected["paths"]["run_dir"],
        "status": selected["status"],
        "ticket": selected.get("ticket"),
        "branch": selected.get("branch"),
        "latest_checkpoint": selected.get("latest_checkpoint"),
        "last_checkpoint": selected.get("last_checkpoint"),
        "resume_hint": selected.get("resume_hint"),
    }, sort_keys=True))
    return 0


def command_dashboard(args: argparse.Namespace) -> int:
    repo = repo_root(Path.cwd())
    allowed = VALID_STATUSES if args.all else (INCOMPLETE_STATUSES | {"active"})
    runs: list[dict[str, Any]] = []

    flow_filter = normalize_flow(args.flow) if args.flow else None

    for root in candidate_roots(repo, args.flow):
        for run_file in sorted(root.glob("*/run.json")) if root.exists() else []:
            try:
                run = read_json(run_file)
            except (OSError, json.JSONDecodeError):
                continue
            if run.get("status") not in allowed:
                continue
            if flow_filter and normalize_flow(run.get("flow", "run")) != flow_filter:
                continue
            run["_dir"] = str(run_file.parent)
            runs.append(run)

    if not runs:
        if args.json:
            print(json.dumps({"runs": [], "total": 0}, sort_keys=True))
            return 0
        print("No matching runs found.")
        return 0

    runs.sort(key=lambda r: r.get("updated_at") or r.get("started_at") or "", reverse=True)

    if args.json:
        result = []
        for run in runs:
            entry = _dashboard_run_entry(run, args.limit)
            result.append(entry)
        print(json.dumps({"runs": result, "total": len(result)}, indent=2, sort_keys=True))
        return 0

    _print_text_dashboard(runs, args.limit)
    return 0


def _dashboard_run_entry(run: dict[str, Any], gate_limit: int) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "run_id": run.get("run_id"),
        "flow": run.get("flow"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "updated_at": run.get("updated_at"),
        "ticket": run.get("ticket") or {"id": run.get("ticket_id", "none")},
        "branch": run.get("branch"),
    }
    if run.get("latest_checkpoint"):
        cp = run["latest_checkpoint"]
        entry["latest_checkpoint"] = {"name": cp.get("name"), "timestamp": cp.get("timestamp")}
    if run.get("resume_hint"):
        entry["resume_hint"] = run["resume_hint"]
    if run.get("interruption"):
        entry["interruption"] = {
            "reason": run["interruption"].get("reason"),
            "timestamp": run["interruption"].get("timestamp"),
        }
    if run.get("finalized_at"):
        entry["finalized_at"] = run["finalized_at"]
    if run.get("paths"):
        entry["run_dir"] = run["paths"].get("run_dir")
        report_path = run["paths"].get("final_report")
        if run.get("finalized_at") and report_path and Path(report_path).is_file():
            entry["final_report"] = report_path

    gates = _collect_gate_history(run, gate_limit)
    if gates:
        entry["gates"] = gates

    return entry


def _collect_gate_history(run: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    run_dir = Path(run.get("_dir") or run.get("paths", {}).get("run_dir", ""))
    if not run_dir or not run_dir.exists():
        return []

    gates_root = run_dir / "artifacts" / "gates"
    if not gates_root.exists():
        return []

    gate_entries: list[tuple[str, dict[str, Any]]] = []
    for scope_dir in sorted(gates_root.iterdir()):
        if not scope_dir.is_dir():
            continue
        for name_dir in sorted(scope_dir.iterdir()):
            if not name_dir.is_dir():
                continue
            for attempt_dir in sorted(name_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0, reverse=True):
                if not attempt_dir.is_dir():
                    continue
                envelope_path = attempt_dir / "envelope.json"
                if not envelope_path.is_file():
                    continue
                try:
                    envelope = read_json(envelope_path)
                except (OSError, json.JSONDecodeError):
                    continue
                gate_status = envelope.get("status", "unknown")
                env_failure = envelope.get("environment_failure", False)
                if gate_status == "fail" and env_failure:
                    classification = "environment_failure"
                elif gate_status == "fail":
                    classification = envelope.get("classification", "code_failure")
                else:
                    classification = None
                entry = {
                    "name": envelope.get("gate", {}).get("name") or attempt_dir.parent.name,
                    "scope": scope_dir.name,
                    "attempt": int(attempt_dir.name) if attempt_dir.name.isdigit() else attempt_dir.name,
                    "status": gate_status,
                    "path": str(envelope_path),
                }
                if classification:
                    entry["classification"] = classification
                gate_entries.append((envelope.get("gate", {}).get("timestamp", ""), entry))
                break

    gate_entries.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in gate_entries[:limit]]


def _status_indicator(status: str) -> str:
    symbols = {
        "running": "●",
        "interrupted": "◐",
        "failed": "✗",
        "completed": "✓",
        "active": "○",
    }
    return symbols.get(status, "?")


def _print_text_dashboard(runs: list[dict[str, Any]], gate_limit: int) -> None:
    print(f"\n{'='*72}")
    print(f"  Beislið Run Dashboard")
    print(f"{'='*72}")
    total_completed = sum(1 for r in runs if r.get("status") == "completed")
    interrupted_count = sum(1 for r in runs if r.get("status") == "interrupted")
    running_count = sum(1 for r in runs if r.get("status") == "running")
    failed_count = sum(1 for r in runs if r.get("status") == "failed")
    active_count = sum(1 for r in runs if r.get("status") == "active")
    print(f"  {len(runs)} run(s)")
    parts = []
    if running_count:
        parts.append(f"{running_count} running")
    if interrupted_count:
        parts.append(f"{interrupted_count} interrupted")
    if failed_count:
        parts.append(f"{failed_count} failed")
    if active_count:
        parts.append(f"{active_count} active")
    if total_completed:
        parts.append(f"{total_completed} completed")
    if parts:
        print(f"  {'  '.join(parts)}")
    print()

    for i, run in enumerate(runs):
        status = run.get("status", "unknown")
        indicator = _status_indicator(status)
        run_id = run.get("run_id", "?")
        flow = run.get("flow", "?")
        ticket = run.get("ticket") or {}
        ticket_id = ticket.get("id") or run.get("ticket_id", "-")
        ticket_title = ticket.get("title", "")
        branch = run.get("branch", "-")
        started = run.get("started_at", "-")
        updated = run.get("updated_at", "-")

        print(f"  {indicator} [{status.upper()}] {run_id}")
        print(f"     Flow:        {flow}")
        if ticket_id and ticket_id != "none":
            print(f"     Ticket:      {ticket_id}" + (f" — {ticket_title}" if ticket_title else ""))
        print(f"     Branch:      {branch}")
        print(f"     Started:     {started}")
        print(f"     Updated:     {updated}")

        if run.get("interruption"):
            ir = run["interruption"]
            print(f"     Interrupted: {ir.get('timestamp', '-')}")
            reason = ir.get("reason", "")
            if reason:
                print(f"     Reason:      {reason}")

        if run.get("latest_checkpoint"):
            cp = run["latest_checkpoint"]
            print(f"     Checkpoint:  {cp.get('name', '-')} ({cp.get('timestamp', '-')})")

        if run.get("resume_hint"):
            print(f"     Resume hint: {run['resume_hint']}")

        report_path = (run.get("paths") or {}).get("final_report")
        if run.get("finalized_at") and report_path and Path(report_path).is_file():
            print(f"     Report:      {report_path}")

        gates = _collect_gate_history(run, gate_limit)
        if gates:
            print(f"     Gates ({len(gates)} recent):")
            for gate in gates:
                gs = gate["status"]
                gname = f"{gate['scope']}/{gate['name']}"
                attempt = gate.get("attempt", "?")
                status_mark = {"pass": "✓", "fail": "✗", "skip": "—", "error": "!"}.get(gs, "?")
                class_note = ""
                if gate.get("classification") == "environment_failure":
                    class_note = " [ENV]"
                elif gate.get("classification") == "code_failure":
                    class_note = " [CODE]"
                print(f"       {status_mark} {gs:<6} {gname} (attempt {attempt}){class_note}")
                if gs in ("fail", "error"):
                    print(f"         artifact: {gate['path']}")
        else:
            print(f"     Gates:       none recorded")

        if run.get("paths") and run["paths"].get("run_dir"):
            print(f"     Dir:         {run['paths']['run_dir']}")

        if i < len(runs) - 1:
            print()

    print(f"{'='*72}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init")
    init_p.add_argument("--skill", required=True)
    init_p.add_argument("--flow", help="Ledger flow name; defaults to --skill")
    init_p.add_argument("--ticket-id", default="none")
    init_p.add_argument("--ticket-title", default="none")
    init_p.add_argument("--ticket-url", default="")
    init_p.add_argument("--branch")
    init_p.add_argument("--run-id")
    init_p.set_defaults(func=command_init)

    event_p = sub.add_parser("event")
    event_p.add_argument("--run-id", required=True)
    event_p.add_argument("--flow")
    event_p.add_argument("--type", required=True)
    event_p.add_argument("--json-file")
    event_p.add_argument("--summary")
    event_p.set_defaults(func=command_event)

    checkpoint_p = sub.add_parser("checkpoint")
    checkpoint_p.add_argument("--run-id", required=True)
    checkpoint_p.add_argument("--flow")
    checkpoint_p.add_argument("--name", required=True)
    checkpoint_p.add_argument("--json-file")
    checkpoint_p.add_argument("--resume-hint")
    checkpoint_p.set_defaults(func=command_checkpoint)

    gate_p = sub.add_parser("gate")
    gate_p.add_argument("--run-id", required=True)
    gate_p.add_argument("--flow")
    gate_p.add_argument("--name", required=True)
    gate_p.add_argument("--scope")
    gate_p.add_argument("--envelope-file", required=True)
    gate_p.add_argument("--resume-hint")
    gate_p.set_defaults(func=command_gate)

    interrupt_p = sub.add_parser("interrupt")
    interrupt_p.add_argument("--run-id", required=True)
    interrupt_p.add_argument("--flow")
    interrupt_p.add_argument("--reason", required=True)
    interrupt_p.add_argument("--resume-hint")
    interrupt_p.set_defaults(func=command_interrupt)

    final_p = sub.add_parser("finalize")
    final_p.add_argument("--run-id", required=True)
    final_p.add_argument("--flow")
    final_p.add_argument("--status", required=True)
    final_p.add_argument("--report-file")
    final_p.set_defaults(func=command_finalize)

    resume_p = sub.add_parser("resume")
    resume_p.add_argument("--flow")
    resume_p.add_argument("--ticket-id")
    resume_p.add_argument("--branch")
    resume_p.add_argument("--include-completed", action="store_true")
    resume_p.set_defaults(func=command_resume)

    dashboard_p = sub.add_parser("dashboard")
    dashboard_p.add_argument("--flow", help="Filter by flow name")
    dashboard_p.add_argument("--all", action="store_true", help="Include completed runs")
    dashboard_p.add_argument("--limit", type=int, default=5, help="Max gates per run (default: 5)")
    dashboard_p.add_argument("--json", action="store_true", help="Output as JSON")
    dashboard_p.set_defaults(func=command_dashboard)

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
