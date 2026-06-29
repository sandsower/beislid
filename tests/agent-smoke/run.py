#!/usr/bin/env python3
"""Generic host-agent smoke harness for Beislið skills."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent
WORKTREE = HARNESS_ROOT.parents[1]
sys.path.insert(0, str(HARNESS_ROOT))

from harness.hosts import get_host  # noqa: E402
from harness.links import activate, cleanup as cleanup_links  # noqa: E402
from harness.terminal import open_terminal  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def set_status(run_dir: Path, state: str, exit_code: int | None = None) -> None:
    path = run_dir / "status.json"
    status = read_json(path) if path.exists() else {}
    status.update({"state": state, "updated_at": now()})
    if state == "running" and "started_at" not in status:
        status["started_at"] = now()
    if state == "exited" and "exited_at" not in status:
        status["exited_at"] = now()
    if exit_code is not None:
        status["exit_code"] = exit_code
    write_json(path, status)


def system_exit_result(exc: SystemExit) -> tuple[int, str]:
    code = exc.code
    if isinstance(code, int):
        return code, ""
    if code is None:
        return 1, ""
    return 1, str(code).strip()


def scenario_dir(name: str) -> Path:
    path = HARNESS_ROOT / "scenarios" / name
    if not path.exists():
        known = ", ".join(sorted(p.name for p in (HARNESS_ROOT / "scenarios").iterdir() if p.is_dir()))
        raise SystemExit(f"unknown scenario {name!r}; known scenarios: {known}")
    return path


def load_scenario(name: str) -> tuple[Path, dict]:
    path = scenario_dir(name)
    config = read_json(path / "scenario.json")
    return path, config


def run_setup(path: Path, run_dir: Path, config: dict) -> dict:
    setup = path / config.get("setup", "setup.py")
    result = subprocess.run(
        [sys.executable, str(setup), "--run-dir", str(run_dir)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"scenario setup failed ({result.returncode}):\n{result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"scenario setup did not print JSON: {exc}\n{result.stdout}") from exc


def write_env(run_dir: Path, metadata: dict) -> None:
    lines = ["# Source this file to reproduce the smoke launcher environment."]
    for key, value in sorted((metadata.get("env") or {}).items()):
        lines.append(f"export {key}={shlex.quote(str(value))}")
    path_parts = [str(p) for p in metadata.get("path_prepend", [])]
    if path_parts:
        joined = ":".join(shlex.quote(p) for p in path_parts)
        lines.append(f"export PATH={joined}:$PATH")
    (run_dir / "env.sh").write_text("\n".join(lines) + "\n", encoding="utf-8")


def host_exec_argv(host_name: str, repo: Path, prompt: str) -> list[str]:
    if host_name == "claude":
        return [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--permission-mode",
            "bypassPermissions",
            prompt,
        ]
    if host_name == "codex":
        return [
            "codex",
            "exec",
            "--cd",
            str(repo),
            "--dangerously-bypass-approvals-and-sandbox",
            prompt,
        ]
    raise SystemExit(f"non-interactive smoke is not configured for host {host_name!r}")


def smoke_env(metadata: dict) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in (metadata.get("env") or {}).items():
        env[key] = str(value)
    path_parts = [str(p) for p in metadata.get("path_prepend", [])]
    if path_parts:
        env["PATH"] = os.pathsep.join(path_parts + [env.get("PATH", "")])
    return env


def write_launcher(run_dir: Path, host_name: str, host_command: str, metadata: dict, prompt: str) -> Path:
    launcher = run_dir / f"launch-{host_name}.sh"
    repo = metadata["repo"]
    content = f"""#!/usr/bin/env bash
set -u
RUN_DIR={shlex.quote(str(run_dir))}
RUN_PY={shlex.quote(str(Path(__file__).resolve()))}
cleanup() {{
  python3 "$RUN_PY" cleanup "$RUN_DIR" >/dev/null 2>&1 || true
}}
trap cleanup EXIT INT TERM
python3 "$RUN_PY" _set-status "$RUN_DIR" running
python3 "$RUN_PY" activate-links "$RUN_DIR" || exit $?
source "$RUN_DIR/env.sh"
cd {shlex.quote(str(repo))} || exit 1
printf '\nBeislið agent smoke is active. Do not start another {host_name} session until cleanup completes.\n'
printf 'Prompt to paste:\n\n'
cat "$RUN_DIR/prompt.txt"
printf '\n\nStarting {host_command}...\n'
{shlex.quote(host_command)}
code=$?
python3 "$RUN_PY" _set-status "$RUN_DIR" exited --exit-code "$code"
exit "$code"
"""
    launcher.write_text(content, encoding="utf-8")
    launcher.chmod(0o755)
    (run_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    return launcher


def create_run(scenario: str, host_name: str) -> tuple[Path, dict, str]:
    path, config = load_scenario(scenario)
    host = get_host(host_name)
    if host.name not in config.get("supported_hosts", []):
        raise SystemExit(f"scenario {scenario!r} does not support host {host.name!r}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(tempfile.mkdtemp(prefix=f"beislid-agent-smoke-{scenario}-{stamp}-"))
    metadata = run_setup(path, run_dir, config)
    prompt = config["prompt"]
    write_env(run_dir, metadata)

    smoke_meta = {
        "scenario": scenario,
        "scenario_dir": str(path),
        "host": host.name,
        "host_command": host.command,
        "worktree": str(WORKTREE),
        "created_at": now(),
        "metadata": metadata,
    }
    write_json(run_dir / "agent-smoke.json", smoke_meta)
    set_status(run_dir, "created")
    return run_dir, metadata, prompt


def launch(args: argparse.Namespace) -> int:
    host = get_host(args.host)
    run_dir, metadata, prompt = create_run(args.scenario, args.host)
    launcher = write_launcher(run_dir, host.name, host.command, metadata, prompt)

    launched = False
    launch_detail = "not requested"
    if not args.no_launch:
        if args.foreground:
            print_kv(run_dir, launcher, "foreground")
            return subprocess.call([str(launcher)])
        launched, launch_detail = open_terminal(launcher)

    status = "launched" if launched else "prepared"
    print_kv(run_dir, launcher, status, launch_detail)
    return 0


def print_kv(run_dir: Path, launcher: Path, status: str, detail: str = "") -> None:
    print(f"RUN_DIR={run_dir}")
    print(f"LAUNCHER={launcher}")
    print(f"VERIFY_CMD=python3 {Path(__file__).resolve()} verify {run_dir}")
    print(f"STATUS_CMD=python3 {Path(__file__).resolve()} status {run_dir}")
    print(f"CLEANUP_CMD=python3 {Path(__file__).resolve()} cleanup {run_dir}")
    print(f"STATUS={status}")
    if detail:
        print(f"DETAIL={detail}")


def print_run_kv(run_dir: Path, host_name: str, status: str, detail: str = "") -> None:
    print(f"RUN_DIR={run_dir}", flush=True)
    print(f"HOST={host_name}", flush=True)
    print(f"LOG={run_dir / (host_name + '.log')}", flush=True)
    print(f"VERIFY_CMD=python3 {Path(__file__).resolve()} verify {run_dir}", flush=True)
    print(f"STATUS_CMD=python3 {Path(__file__).resolve()} status {run_dir}", flush=True)
    print(f"CLEANUP_CMD=python3 {Path(__file__).resolve()} cleanup {run_dir}", flush=True)
    print(f"STATUS={status}", flush=True)
    if detail:
        print(f"DETAIL={detail}", flush=True)


def verify(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    meta = read_json(run_dir / "agent-smoke.json")
    scenario_path = Path(meta["scenario_dir"])
    config = read_json(scenario_path / "scenario.json")
    verifier = scenario_path / config.get("verify", "verify.py")
    return subprocess.call([sys.executable, str(verifier), str(run_dir)])


def cleanup_cmd(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    cleanup_links(run_dir)
    set_status(run_dir, "cleanup-complete")
    if args.remove_run_dir:
        shutil.rmtree(run_dir)
    return 0


def status_cmd(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    path = run_dir / "status.json"
    payload = read_json(path) if path.exists() else {"state": "unknown"}
    print(json.dumps(payload, indent=2))
    return 0


def activate_cmd(args: argparse.Namespace) -> int:
    activate(Path(args.run_dir).resolve())
    return 0


def set_status_cmd(args: argparse.Namespace) -> int:
    set_status(Path(args.run_dir).resolve(), args.state, args.exit_code)
    return 0


def run_host(args: argparse.Namespace) -> int:
    host = get_host(args.host)
    run_dir, metadata, prompt = create_run(args.scenario, args.host)
    repo = Path(metadata["repo"])
    argv = host_exec_argv(host.name, repo, prompt)
    write_json(
        run_dir / "host-command.json",
        {
            "host": host.name,
            "argv": argv,
            "cwd": str(repo),
            "timeout_seconds": args.timeout,
            "permission_mode": "broadest-local-smoke",
        },
    )
    print_run_kv(run_dir, host.name, "running", shlex.join(argv))

    host_rc = 1
    verify_rc = 1
    try:
        activate(run_dir)
        set_status(run_dir, "running")
        with (run_dir / f"{host.name}.log").open("w", encoding="utf-8") as log:
            log.write(f"$ {shlex.join(argv)}\n\n=== BEISLID_AGENT_SMOKE_OUTPUT ===\n")
            log.flush()
            try:
                result = subprocess.run(
                    argv,
                    cwd=repo,
                    env=smoke_env(metadata),
                    text=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=args.timeout,
                    check=False,
                )
                host_rc = result.returncode
                set_status(run_dir, "exited", host_rc)
            except subprocess.TimeoutExpired:
                host_rc = 124
                log.write(f"\nTIMEOUT after {args.timeout}s\n")
                set_status(run_dir, "timeout", host_rc)
    finally:
        if not args.no_cleanup:
            cleanup_links(run_dir)

    if not args.no_verify:
        verify_rc = verify(argparse.Namespace(run_dir=str(run_dir)))
    else:
        verify_rc = 0

    if host_rc == 0 and verify_rc == 0:
        set_status(run_dir, "verified", 0)
        print_run_kv(run_dir, host.name, "passed")
        return 0
    set_status(run_dir, "failed", host_rc if host_rc else verify_rc)
    print_run_kv(run_dir, host.name, "failed", f"host_rc={host_rc} verify_rc={verify_rc}")
    return host_rc if host_rc else verify_rc


SMOKE_TRIGGER_PREFIXES = ("skills/", ".beislid/", "tests/agent-smoke/")
SMOKE_TRIGGER_PATHS = {"install.sh", "scripts/test_install.sh"}


def git_output(args: list[str]) -> list[str]:
    result = subprocess.run(
        args,
        cwd=WORKTREE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def changed_files() -> set[str]:
    files: set[str] = set()
    base = git_output(["git", "merge-base", "HEAD", "origin/main"])
    if base:
        files.update(git_output(["git", "diff", "--name-only", base[0], "HEAD"]))
    files.update(git_output(["git", "diff", "--name-only"]))
    files.update(git_output(["git", "diff", "--name-only", "--cached"]))
    files.update(git_output(["git", "ls-files", "--others", "--exclude-standard"]))
    return files


def has_origin_main_merge_base() -> bool:
    return bool(git_output(["git", "merge-base", "HEAD", "origin/main"]))


def should_run_changed_only() -> bool:
    if not has_origin_main_merge_base():
        return True
    files = changed_files()
    return any(path.startswith(SMOKE_TRIGGER_PREFIXES) or path in SMOKE_TRIGGER_PATHS for path in files)


def gate(args: argparse.Namespace) -> int:
    if args.changed_only and not should_run_changed_only():
        print("ok: agent smoke skipped; no Beislið skill/smoke files changed")
        return 0

    hosts = [host.strip() for host in args.hosts.split(",") if host.strip()]
    failures: list[tuple[str, int, str]] = []

    def run_one(host: str) -> tuple[str, int, str]:
        try:
            rc = run_host(
                argparse.Namespace(
                    scenario=args.scenario,
                    host=host,
                    timeout=args.timeout,
                    no_verify=False,
                    no_cleanup=False,
                )
            )
            return host, rc, ""
        except SystemExit as exc:
            rc, detail = system_exit_result(exc)
            return host, rc, detail

    if args.serial or len(hosts) == 1:
        results = [run_one(host) for host in hosts]
    else:
        results = []
        with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
            futures = {executor.submit(run_one, host): host for host in hosts}
            for future in as_completed(futures):
                results.append(future.result())

    for host, rc, detail in results:
        if rc != 0:
            failures.append((host, rc, detail))
    if failures:
        for host, rc, detail in failures:
            suffix = f": {detail}" if detail else ""
            print(f"failed: {host} rc={rc}{suffix}", file=sys.stderr)
        return 1
    print(f"ok: {args.scenario} agent smoke passed on {', '.join(hosts)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    launch_p = sub.add_parser("launch")
    launch_p.add_argument("scenario")
    launch_p.add_argument("--host", required=True, choices=sorted(["claude", "codex"]))
    launch_p.add_argument("--no-launch", action="store_true")
    launch_p.add_argument("--foreground", action="store_true")
    launch_p.set_defaults(func=launch)

    run_p = sub.add_parser("run", help="Run one host non-interactively with broad local permissions")
    run_p.add_argument("scenario")
    run_p.add_argument("--host", required=True, choices=sorted(["claude", "codex"]))
    run_p.add_argument("--timeout", type=int, default=900)
    run_p.add_argument("--no-verify", action="store_true")
    run_p.add_argument("--no-cleanup", action="store_true")
    run_p.set_defaults(func=run_host)

    gate_p = sub.add_parser("gate", help="Run a scenario across hosts non-interactively")
    gate_p.add_argument("scenario")
    gate_p.add_argument("--hosts", default="codex")
    gate_p.add_argument("--timeout", type=int, default=900)
    gate_p.add_argument("--changed-only", action="store_true", help="Skip unless skill/smoke files changed")
    gate_p.add_argument("--serial", action="store_true", help="Run hosts one after another instead of in parallel")
    gate_p.set_defaults(func=gate)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("run_dir")
    verify_p.set_defaults(func=verify)

    cleanup_p = sub.add_parser("cleanup")
    cleanup_p.add_argument("run_dir")
    cleanup_p.add_argument("--remove-run-dir", action="store_true")
    cleanup_p.set_defaults(func=cleanup_cmd)

    status_p = sub.add_parser("status")
    status_p.add_argument("run_dir")
    status_p.set_defaults(func=status_cmd)

    activate_p = sub.add_parser("activate-links")
    activate_p.add_argument("run_dir")
    activate_p.set_defaults(func=activate_cmd)

    set_p = sub.add_parser("_set-status")
    set_p.add_argument("run_dir")
    set_p.add_argument("state")
    set_p.add_argument("--exit-code", type=int)
    set_p.set_defaults(func=set_status_cmd)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    known = {"launch", "run", "gate", "verify", "cleanup", "status", "activate-links", "_set-status", "-h", "--help"}
    if argv and argv[0] not in known:
        argv = ["launch", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
