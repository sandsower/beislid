"""Shared fixture-building helpers for agent-smoke scenario setup.py and verify.py self-tests.

Every scenario under tests/agent-smoke/scenarios/<name>/ hand-rolled its own git
fixture-repo bootstrap, mock-bin fakes, and setup.py main() wrapper. This module
extracts the repeated shape so scenario setup.py files stay focused on what makes
that scenario unique: seed files, workflow.md content, and prompt-specific mock
routes. It intentionally does not decide scenario content - callers still write
their own workflow.md bodies, seed files, and mock route tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence

# --- basic process/file helpers -------------------------------------------------


def run(args: list[str], cwd: Path | None = None) -> str:
    """Run a command, raising with captured stderr on failure. Used by both fixture
    setup (real subprocesses) and verify.py self-tests (synthetic fixtures)."""
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tracked_hashes(repo: Path) -> dict[str, str]:
    """sha256 per git-tracked file, relative path -> hex digest. Used by scenarios
    that assert the fixture repo's tracked files are byte-identical after a smoke
    run (see harness.verification.require_repo_snapshot's expected_hashes)."""
    files = run(["git", "ls-files"], cwd=repo).splitlines()
    hashes: dict[str, str] = {}
    for rel in files:
        data = (repo / rel).read_bytes()
        hashes[rel] = hashlib.sha256(data).hexdigest()
    return hashes


# --- setup.py main() wrapper -----------------------------------------------------


def setup_main(build_metadata: Callable[[Path], dict], *, prefix: str) -> int:
    """Standard setup.py entrypoint body: parse --run-dir, resolve/create the run
    dir (or make a fresh tempdir), call build_metadata(run_dir), persist the result
    to <run-dir>/metadata.json (verify.py always reads this file from disk - run.py
    itself never writes it), print the same JSON to stdout, and translate exceptions
    into the conventional 'setup failed: ...' exit 1.

    Every scenario's setup.py should reduce to:

        def main() -> int:
            return fixtures.setup_main(create_fixture, prefix="beislid-<name>-smoke")

        if __name__ == "__main__":
            raise SystemExit(main())
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    if args.run_dir:
        run_dir = Path(args.run_dir).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(tempfile.mkdtemp(prefix=f"{prefix}-{stamp}-"))
    try:
        metadata = build_metadata(run_dir)
    except Exception as exc:  # noqa: BLE001 - setup failures are reported, not raised
        print(f"setup failed: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(metadata, indent=2) + "\n"
    write(run_dir / "metadata.json", payload)
    print(payload, end="")
    return 0


# --- fixture-repo builder ---------------------------------------------------------


def init_fixture_repo(run_dir: Path, *, name: str, email: str, origin_dirname: str = "origin.git", repo_dirname: str = "repo") -> tuple[Path, Path]:
    """Bare origin + clone + user config. Used by scenarios that push and/or expect
    a remote (envelope, kickoff, ready-for-review, review-response*)."""
    origin = run_dir / origin_dirname
    repo = run_dir / repo_dirname
    run(["git", "init", "--bare", str(origin)])
    run(["git", "clone", str(origin), str(repo)])
    run(["git", "config", "user.email", email], cwd=repo)
    run(["git", "config", "user.name", name], cwd=repo)
    return origin, repo


def init_plain_repo(run_dir: Path, *, name: str, email: str, repo_dirname: str = "repo") -> Path:
    """Plain `git init` (no origin/remote). Used by scenarios that only need local
    history (bootstrap-route, walk-the-diff, walk-the-diff-wrap)."""
    repo = run_dir / repo_dirname
    repo.mkdir(parents=True, exist_ok=True)
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.email", email], cwd=repo)
    run(["git", "config", "user.name", name], cwd=repo)
    return repo


def commit_only(repo: Path, message: str, *, paths: Sequence[str] = (".",)) -> None:
    run(["git", "add", *paths], cwd=repo)
    run(["git", "commit", "-m", message], cwd=repo)


def commit_and_push(repo: Path, message: str, *, branch: str = "main", paths: Sequence[str] = (".",)) -> None:
    """Commit then rename to `branch` and push -u to the already-cloned origin.
    Requires the repo to have come from init_fixture_repo (has an `origin` remote)."""
    commit_only(repo, message, paths=paths)
    run(["git", "branch", "-M", branch], cwd=repo)
    run(["git", "push", "-u", "origin", branch], cwd=repo)


def workflow_path(repo: Path) -> Path:
    return repo / ".beislid" / "workflow.md"


def write_workflow(repo: Path, body: str) -> None:
    """Write `.beislid/workflow.md`. `body` is the full file content (including the
    `<!-- beislid-workflow: v1 -->` stamp) - scenarios keep full control over their
    config blocks; this just fixes the well-known path."""
    write(workflow_path(repo), body)


# --- mock-bin ----------------------------------------------------------------------


def install_static_mock_bin(scenario_dir: Path, mock_bin: Path, names: Iterable[str]) -> None:
    """Copy prebuilt, unchanging mock-bin/<name> scripts straight from the scenario
    directory. Use this when a scenario's mock behavior isn't worth generating
    (rare) - prefer write_gh_mock/write_lifecycle_action_mock/write_file_relay_mock
    for anything with declarative routes."""
    mock_bin.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(scenario_dir / "mock-bin" / name, mock_bin / name)
        os.chmod(mock_bin / name, 0o755)


def write_mock_script(path: Path, *, log_env: str, command_name: str, body: str) -> None:
    """Write an executable bash mock with the standard invocation-logging preamble
    every mock-bin fake needs: require `log_env` to be set, log a timestamped,
    shell-quoted argv line to it, then run scenario-specific `body`."""
    script = f"""#!/usr/bin/env bash
set -euo pipefail
log=${{{log_env}:-}}
if [[ -z "$log" ]]; then
  echo "{log_env} is not set" >&2
  exit 98
fi
mkdir -p "$(dirname "$log")"
printf '%s\\tcwd=%s\\t{command_name}' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$PWD" >> "$log"
for arg in "$@"; do printf ' %q' "$arg" >> "$log"; done
printf '\\n' >> "$log"

{body.strip()}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, script)
    os.chmod(path, 0o755)


def _dispatch_route_block(route: dict, *, arity: int) -> str:
    args = " ".join(f'${{{i}:-}}' for i in range(1, arity + 1))
    lines = [f'if [[ "{args}" == "{route["match"]}" ]]; then']
    contains = route.get("contains")
    if contains:
        lines.append('  case " $* " in')
        lines.append(f'    *" {contains} "*) : ;;')
        lines.append(f'    *) echo "mock {route.get("name", "cli")}: expected {contains!r} in args: $*" >&2; exit {route.get("contains_exit_code", 46)} ;;')
        lines.append('  esac')
    validate = route.get("validate")
    if validate:
        lines.append(validate.rstrip())
    lines.append("  cat <<'JSON'")
    lines.append(route["response"].rstrip())
    lines.append("JSON")
    lines.append(f'  exit {route.get("exit_code", 0)}')
    lines.append("fi")
    return "\n".join(lines) + "\n"


def write_dispatch_mock(
    path: Path,
    *,
    log_env: str,
    command_name: str,
    routes: Sequence[dict],
    arity: int = 2,
    fallback: str,
) -> None:
    """Generic 'match a subcommand, emit canned JSON' mock. Each route is a dict:
    - match: the space-joined first `arity` args to match exactly, e.g. "issue view"
    - validate: optional raw bash snippet (positional args $1.. available) that may
      `exit <code>` before the response is emitted - covers per-route argument
      validation (e.g. kickoff's gh requiring issue id 123)
    - contains: optional substring that must appear in the full "$*"; mismatches
      exit with contains_exit_code (default 46)
    - response: heredoc body to print on success
    - exit_code: defaults to 0

    `fallback` is raw bash appended after every route falls through (e.g. gh's
    'auth status' -> ok, then 'unsupported command' exit)."""
    blocks = "".join(_dispatch_route_block({**route, "name": command_name}, arity=arity) for route in routes)
    body = f"{blocks}\n{fallback.strip()}\n"
    write_mock_script(path, log_env=log_env, command_name=command_name, body=body)


GH_AUTH_FALLBACK = """
if [[ "${1:-} ${2:-}" == "auth status" ]]; then
  echo "github.com mock auth ok"
  exit 0
fi

echo "mock gh: unsupported command: $*" >&2
exit 45
"""


def write_gh_mock(path: Path, *, routes: Sequence[dict], log_env: str = "GH_MOCK_LOG") -> None:
    """`gh` fake: dispatches on the first two args (e.g. "issue view", "pr view"),
    always supports `gh auth status` -> ok, and rejects anything else with exit 45.
    See write_dispatch_mock for the route dict shape."""
    write_dispatch_mock(
        path,
        log_env=log_env,
        command_name="gh",
        routes=routes,
        arity=2,
        fallback=GH_AUTH_FALLBACK,
    )


def write_lifecycle_action_mock(
    path: Path,
    *,
    expected_args: Sequence[str],
    log_env: str = "LIFECYCLE_ACTION_LOG",
    usage: str = "<ticket_id> <id_alias> <branch> <event>",
    success_message: str = "ok: lifecycle action ran",
) -> None:
    """`lifecycle-action` fake: requires exactly len(expected_args) positional args
    and validates each against `expected_args` (declarative table), erroring with a
    distinct exit code per mismatched position."""
    checks = [
        f'if [[ $# -ne {len(expected_args)} ]]; then\n'
        f'  echo "lifecycle-action requires: {usage}" >&2\n'
        f'  exit 40\n'
        f'fi'
    ]
    for index, expected in enumerate(expected_args, start=1):
        checks.append(
            f'if [[ "${index}" != "{expected}" ]]; then\n'
            f'  echo "lifecycle-action expected arg {index} to be {expected!r}, got ${index}" >&2\n'
            f'  exit {40 + index}\n'
            f'fi'
        )
    body = "\n".join(checks) + f'\necho "{success_message}"\n'
    write_mock_script(path, log_env=log_env, command_name="lifecycle-action", body=body)


def write_file_relay_mock(
    path: Path,
    *,
    log_env: str,
    out_env: str,
    expected_leading_args: Sequence[str],
    success_message: str,
    command_name: str | None = None,
) -> None:
    """Fake for CLIs that take some fixed leading args plus a trailing file path,
    validate the leading args, copy the file to `out_env` for later inspection, and
    echo a success message. Covers ticket-comment (`<id> <body_file>`) and
    pr-review-update (`reply <json_file>`)."""
    name = command_name or path.name
    arg_count = len(expected_leading_args) + 1
    file_index = arg_count
    checks = [
        f'out=${{{out_env}:-}}\n'
        f'if [[ -z "$out" ]]; then\n'
        f'  echo "{out_env} must be set" >&2\n'
        f'  exit 98\n'
        f'fi\n'
        f'mkdir -p "$(dirname "$out")"',
        f'if [[ $# -ne {arg_count} ]]; then\n'
        f'  echo "{name} requires exactly {arg_count} args" >&2\n'
        f'  exit 40\n'
        f'fi',
    ]
    for index, expected in enumerate(expected_leading_args, start=1):
        checks.append(
            f'if [[ "${index}" != "{expected}" && "${index}" != "#{expected}" ]]; then\n'
            f'  echo "{name} expected arg {index} to be {expected!r}, got ${index}" >&2\n'
            f'  exit {50 + index}\n'
            f'fi'
        )
    checks.append(
        f'file_arg=${file_index}\n'
        f'if [[ ! -f "$file_arg" ]]; then\n'
        f'  echo "{name} expected a real file path, got $file_arg" >&2\n'
        f'  exit 42\n'
        f'fi\n'
        f'case "$file_arg" in\n'
        f'  *$\'\\n\'*)\n'
        f'    echo "{name} got raw-looking content instead of a path" >&2\n'
        f'    exit 43\n'
        f'    ;;\n'
        f'esac\n'
        f'cp "$file_arg" "${{{out_env}}}"\n'
        f'echo "{success_message}"'
    )
    body = "\n".join(checks) + "\n"
    write_mock_script(path, log_env=log_env, command_name=name, body=body)
