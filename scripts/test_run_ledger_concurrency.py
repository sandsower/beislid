#!/usr/bin/env python3
"""Concurrency tests for scripts/run_ledger.py.

These tests intentionally use only the Python standard library and isolate all
state under a temporary BEISLID_STATE_DIR.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
LEDGER = REPO_DIR / "scripts" / "run_ledger.py"


class TestFailure(AssertionError):
    pass


def run(cmd: list[str], *, cwd: Path, env: dict[str, str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise TestFailure(
            f"command failed ({result.returncode}): {' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def setup_fixture(tmp: Path) -> tuple[Path, dict[str, str]]:
    repo = tmp / "repo"
    repo.mkdir()
    run(["git", "init", "-q"], cwd=repo, env=os.environ.copy())
    run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, env=os.environ.copy())
    run(["git", "config", "user.name", "Test"], cwd=repo, env=os.environ.copy())
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    run(["git", "add", "README.md"], cwd=repo, env=os.environ.copy())
    run(["git", "commit", "-q", "-m", "init"], cwd=repo, env=os.environ.copy())

    env = os.environ.copy()
    env["BEISLID_STATE_DIR"] = str(tmp / "state")
    return repo, env


def init_run(repo: Path, env: dict[str, str], *, run_id: str | None = None) -> dict[str, str]:
    cmd = [
        "python3",
        str(LEDGER),
        "init",
        "--skill",
        "kickoff",
        "--flow",
        "kickoff",
        "--ticket-id",
        "127",
        "--ticket-title",
        "Concurrency",
        "--branch",
        "feature/concurrency",
    ]
    if run_id:
        cmd.extend(["--run-id", run_id])
    result = run(cmd, cwd=repo, env=env)
    return json.loads(result.stdout)


def reset_events(run_dir: Path) -> None:
    run_path = run_dir / "run.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    payload["events"] = {"count": 0}
    run_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")


def jsonl_line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def test_concurrent_event_appends() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        repo, env = setup_fixture(Path(tmp_name))
        init = init_run(repo, env)
        run_id = init["run_id"]
        run_dir = Path(init["run_dir"])
        reset_events(run_dir)

        def append_event(index: int) -> subprocess.CompletedProcess[str]:
            return run(
                [
                    "python3",
                    str(LEDGER),
                    "event",
                    "--run-id",
                    run_id,
                    "--flow",
                    "kickoff",
                    "--type",
                    f"concurrent_{index}",
                    "--summary",
                    f"event {index}",
                ],
                cwd=repo,
                env=env,
                check=False,
            )

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = [future.result() for future in as_completed(executor.submit(append_event, i) for i in range(20))]

        failures = [result for result in results if result.returncode != 0]
        if failures:
            first = failures[0]
            raise TestFailure(f"event append failed: stdout={first.stdout!r} stderr={first.stderr!r}")

        run_payload = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        event_count = int(run_payload.get("events", {}).get("count", -1))
        line_count = jsonl_line_count(run_dir / "events.jsonl")
        transcript_headings = {
            line.strip()
            for line in (run_dir / "transcript.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        }
        transcript_count = sum(1 for i in range(20) if f"## concurrent_{i}" in transcript_headings)
        if event_count != 20 or line_count != 20 or transcript_count != 20:
            raise TestFailure(
                "expected 20 events, 20 jsonl lines, and 20 transcript sections; "
                f"got events.count={event_count}, lines={line_count}, transcript_sections={transcript_count}"
            )


def test_concurrent_gate_attempt_dirs() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        repo, env = setup_fixture(tmp)
        init = init_run(repo, env)
        run_id = init["run_id"]
        gate_payload = tmp / "gate.json"
        gate_payload.write_text('{"gate":{"name":"concurrency-gate"},"status":"pass"}\n', encoding="utf-8")

        def record_gate(index: int) -> subprocess.CompletedProcess[str]:
            return run(
                [
                    "python3",
                    str(LEDGER),
                    "gate",
                    "--run-id",
                    run_id,
                    "--flow",
                    "kickoff",
                    "--name",
                    "concurrency-gate",
                    "--scope",
                    "repo",
                    "--envelope-file",
                    str(gate_payload),
                    "--resume-hint",
                    f"gate {index}",
                ],
                cwd=repo,
                env=env,
                check=False,
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = [future.result() for future in as_completed(executor.submit(record_gate, i) for i in range(10))]

        failures = [result for result in results if result.returncode != 0]
        if failures:
            first = failures[0]
            raise TestFailure(f"gate command failed: stdout={first.stdout!r} stderr={first.stderr!r}")

        gate_logs = []
        for result in results:
            payload = json.loads(result.stdout)
            gate_logs.append(Path(payload["gate_log"]))
        if len(set(gate_logs)) != 10:
            raise TestFailure(f"expected 10 distinct gate logs, got {sorted(str(path) for path in gate_logs)}")
        for path in gate_logs:
            if not path.is_file():
                raise TestFailure(f"missing gate log: {path}")

        attempts_root = Path(init["run_dir"]) / "artifacts" / "gates" / "repo" / "concurrency-gate"
        attempts = [path.name for path in sorted(attempts_root.iterdir(), key=lambda p: int(p.name)) if path.is_dir()]
        if attempts != [str(i) for i in range(1, 11)]:
            raise TestFailure(f"expected attempts 1..10, got {attempts}")


def test_explicit_run_id_collision_errors() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        repo, env = setup_fixture(Path(tmp_name))
        init = init_run(repo, env, run_id="fixed-run")
        colliding_dir = init["run_dir"]
        result = run(
            [
                "python3",
                str(LEDGER),
                "init",
                "--skill",
                "kickoff",
                "--flow",
                "kickoff",
                "--run-id",
                "fixed-run",
            ],
            cwd=repo,
            env=env,
            check=False,
        )
        if result.returncode == 0:
            raise TestFailure(f"explicit --run-id collision should fail, got success: {result.stdout}")
        combined = result.stdout + result.stderr
        if "run id already exists" not in combined or colliding_dir not in combined:
            raise TestFailure(f"collision diagnostic should name the colliding directory; got: {combined!r}")


def main() -> int:
    tests = [
        ("concurrent event appends", test_concurrent_event_appends),
        ("concurrent gate attempt dirs", test_concurrent_gate_attempt_dirs),
        ("explicit run-id collision", test_explicit_run_id_collision_errors),
    ]
    passed = 0
    failed: list[str] = []
    for name, test in tests:
        print(f"-- {name}")
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - tiny stdlib-only test runner
            failed.append(name)
            print(f"   FAIL: {exc}")
        else:
            passed += 1
            print("   pass")
    print(f"\n{passed} passed, {len(failed)} failed")
    if failed:
        print("Failures:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
