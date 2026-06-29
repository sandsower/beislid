#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HARNESS_DIR = ROOT / "tests" / "agent-smoke"
sys.path.insert(0, str(HARNESS_DIR))

RUN_SPEC = importlib.util.spec_from_file_location("agent_smoke_run", HARNESS_DIR / "run.py")
assert RUN_SPEC and RUN_SPEC.loader
run = importlib.util.module_from_spec(RUN_SPEC)
RUN_SPEC.loader.exec_module(run)

import harness.links as links  # noqa: E402
from harness.links import _acquire_lock, _lock_path  # noqa: E402


class AgentSmokeHarnessTests(unittest.TestCase):
    def test_changed_only_requires_origin_main(self) -> None:
        orig_git_output = run.git_output
        try:
            run.git_output = lambda args: []  # type: ignore[assignment]
            self.assertTrue(run.should_run_changed_only())

            responses = {
                ("git", "merge-base", "HEAD", "origin/main"): ["base"],
                ("git", "diff", "--name-only", "base", "HEAD"): ["docs/readme.md"],
                ("git", "diff", "--name-only"): [],
                ("git", "diff", "--name-only", "--cached"): [],
                ("git", "ls-files", "--others", "--exclude-standard"): [],
            }
            run.git_output = lambda args: responses.get(tuple(args), [])  # type: ignore[assignment]
            self.assertFalse(run.should_run_changed_only())

            responses[("git", "diff", "--name-only", "base", "HEAD")] = ["tests/agent-smoke/run.py"]
            self.assertTrue(run.should_run_changed_only())
        finally:
            run.git_output = orig_git_output  # type: ignore[assignment]

    def test_gate_reports_system_exit_per_host(self) -> None:
        orig_run_host = run.run_host
        orig_should_run_changed_only = run.should_run_changed_only
        try:
            run.should_run_changed_only = lambda: True  # type: ignore[assignment]

            def fake_run_host(args: argparse.Namespace) -> int:
                if args.host == "codex":
                    raise SystemExit("setup boom")
                return 0

            run.run_host = fake_run_host  # type: ignore[assignment]

            stdout = io.StringIO()
            stderr = io.StringIO()
            args = argparse.Namespace(scenario="ready-for-review", suite=None, hosts="codex,claude", timeout=5, changed_only=False, serial=False)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rc = run.gate(args)

            self.assertEqual(rc, 1)
            self.assertIn("failed: ready-for-review/codex rc=1: setup boom", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
        finally:
            run.run_host = orig_run_host  # type: ignore[assignment]
            run.should_run_changed_only = orig_should_run_changed_only  # type: ignore[assignment]

    def test_gate_supports_suite(self) -> None:
        orig_run_host = run.run_host
        orig_load_suite = run.load_suite
        orig_should_run_changed_only = run.should_run_changed_only
        try:
            run.should_run_changed_only = lambda: True  # type: ignore[assignment]
            run.load_suite = lambda name: {"name": name, "scenarios": ["walk-the-diff", "walk-the-diff-wrap"]}  # type: ignore[assignment]
            seen: list[str] = []

            def fake_run_host(args: argparse.Namespace) -> int:
                seen.append(args.scenario)
                return 0

            run.run_host = fake_run_host  # type: ignore[assignment]
            stdout = io.StringIO()
            stderr = io.StringIO()
            args = argparse.Namespace(scenario=None, suite="walk-the-diff-suite", hosts="codex", timeout=5, changed_only=False, serial=False)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rc = run.gate(args)

            self.assertEqual(rc, 0)
            self.assertEqual(seen, ["walk-the-diff", "walk-the-diff-wrap"])
            self.assertIn("ok: suite walk-the-diff-suite agent smoke passed on codex", stdout.getvalue())
        finally:
            run.run_host = orig_run_host  # type: ignore[assignment]
            run.load_suite = orig_load_suite  # type: ignore[assignment]
            run.should_run_changed_only = orig_should_run_changed_only  # type: ignore[assignment]

    def test_cleanup_complete_does_not_fabricate_exited_at(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-agent-smoke-status-") as tmp:
            run_dir = Path(tmp)
            run.set_status(run_dir, "cleanup-complete")
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["state"], "cleanup-complete")
            self.assertNotIn("exited_at", status)

            run.set_status(run_dir, "exited", 17)
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["state"], "exited")
            self.assertIn("exited_at", status)
            exited_at = status["exited_at"]

            run.set_status(run_dir, "cleanup-complete")
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["state"], "cleanup-complete")
            self.assertEqual(status["exited_at"], exited_at)

    def test_verify_marks_run_verified_on_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-agent-smoke-verify-") as tmp:
            run_dir = Path(tmp)
            scenario_dir = run_dir / "scenario"
            scenario_dir.mkdir()
            (scenario_dir / "scenario.json").write_text(json.dumps({"verify": "verify.py"}) + "\n", encoding="utf-8")
            (scenario_dir / "verify.py").write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
            (run_dir / "agent-smoke.json").write_text(json.dumps({"scenario_dir": str(scenario_dir)}) + "\n", encoding="utf-8")
            run.set_status(run_dir, "running")

            with patch.object(run.subprocess, "call", return_value=0):
                rc = run.verify(argparse.Namespace(run_dir=str(run_dir)))

            self.assertEqual(rc, 0)
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["state"], "verified")
            self.assertEqual(status["exit_code"], 0)

    def test_run_host_marks_verified_when_verify_passes_after_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-agent-smoke-run-host-") as tmp:
            run_dir = Path(tmp)
            repo = run_dir / "repo"
            repo.mkdir()
            metadata = {"repo": str(repo)}
            host = type("Host", (), {"name": "codex"})()

            def fake_create_run(scenario: str, host_name: str) -> tuple[Path, dict, str]:
                self.assertEqual(scenario, "ready-for-review")
                self.assertEqual(host_name, "codex")
                return run_dir, metadata, "prompt"

            with (
                patch.object(run, "create_run", side_effect=fake_create_run),
                patch.object(run, "get_host", return_value=host),
                patch.object(run, "host_exec_argv", return_value=["codex", "exec", "prompt"]),
                patch.object(run, "activate"),
                patch.object(run, "cleanup_links"),
                patch.object(run, "smoke_env", return_value={}),
                patch.object(run, "print_run_kv"),
                patch.object(run, "verify", return_value=0),
                patch.object(run.subprocess, "run", side_effect=run.subprocess.TimeoutExpired(cmd=["codex"], timeout=5)),
            ):
                rc = run.run_host(argparse.Namespace(scenario="ready-for-review", host="codex", timeout=5, no_verify=False, no_cleanup=False))

            self.assertEqual(rc, 124)
            status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["state"], "verified")
            self.assertEqual(status["exit_code"], 124)

    def test_lock_blocks_second_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-agent-smoke-lock-") as tmp:
            tmp_path = Path(tmp)
            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()
            run_dir_1 = tmp_path / "run-1"
            run_dir_2 = tmp_path / "run-2"
            run_dir_1.mkdir()
            run_dir_2.mkdir()

            _acquire_lock("codex", skills_dir, run_dir_1, tmp_path)
            self.assertTrue(_lock_path(skills_dir).exists())

            _acquire_lock("codex", skills_dir, run_dir_1, tmp_path)

            with self.assertRaises(SystemExit):
                _acquire_lock("codex", skills_dir, run_dir_2, tmp_path)

    def test_lock_blocks_contending_acquire_before_publish(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-agent-smoke-lock-race-") as tmp:
            tmp_path = Path(tmp)
            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()
            run_dir_1 = tmp_path / "run-1"
            run_dir_2 = tmp_path / "run-2"
            run_dir_1.mkdir()
            run_dir_2.mkdir()

            original_link = links.os.link
            first_link_started = threading.Event()
            allow_first_link = threading.Event()
            first_error: list[BaseException] = []
            second_error: list[BaseException] = []
            first_link = {"seen": False}
            lock = threading.Lock()

            def blocking_link(src: str, dst: str, *args: object, **kwargs: object) -> None:
                should_block = False
                with lock:
                    if not first_link["seen"]:
                        first_link["seen"] = True
                        should_block = True
                        first_link_started.set()
                if should_block:
                    self.assertTrue(allow_first_link.wait(timeout=5), "timed out waiting to publish first lock")
                return original_link(src, dst, *args, **kwargs)

            def first_acquire() -> None:
                try:
                    _acquire_lock("codex", skills_dir, run_dir_1, tmp_path)
                except BaseException as exc:  # pragma: no cover - re-raised in the main test thread
                    first_error.append(exc)

            worker: threading.Thread | None = None
            links.os.link = blocking_link  # type: ignore[assignment]
            try:
                worker = threading.Thread(target=first_acquire)
                worker.start()
                self.assertTrue(first_link_started.wait(timeout=5), "first lock publication never blocked")

                try:
                    _acquire_lock("codex", skills_dir, run_dir_2, tmp_path)
                except BaseException as exc:
                    second_error.append(exc)
            finally:
                links.os.link = original_link  # type: ignore[assignment]
                allow_first_link.set()
                if worker is not None:
                    worker.join(timeout=5)
                    self.assertFalse(worker.is_alive())

            self.assertTrue((len(first_error) == 1) ^ (len(second_error) == 1))
            if first_error:
                self.assertIsInstance(first_error[0], SystemExit)
            if second_error:
                self.assertIsInstance(second_error[0], SystemExit)
            lock_data = json.loads(_lock_path(skills_dir).read_text(encoding="utf-8"))
            self.assertIn(lock_data["run_dir"], {str(run_dir_1.resolve()), str(run_dir_2.resolve())})

    def test_release_lock_cleans_up_legacy_canonicalized_run_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-agent-smoke-lock-release-") as tmp:
            root = Path(tmp)
            resolved_run_dir = root / "private" / "var" / "run"
            resolved_run_dir.mkdir(parents=True)
            legacy_run_dir = root / "var" / "run"
            (root / "var").symlink_to(root / "private" / "var")
            skills_dir = root / "skills"
            skills_dir.mkdir()
            _lock_path(skills_dir).write_text(
                json.dumps({"host": "codex", "run_dir": str(legacy_run_dir), "worktree": str(root)}) + "\n",
                encoding="utf-8",
            )

            warnings: list[str] = []
            links._release_lock(skills_dir, resolved_run_dir, warnings)

            self.assertFalse(_lock_path(skills_dir).exists())
            self.assertEqual(warnings, [])

            # Clean up the symlinked directory before the temporary directory is removed.
            (root / "var").unlink()


if __name__ == "__main__":
    unittest.main()
