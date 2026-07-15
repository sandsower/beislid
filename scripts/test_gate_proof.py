#!/usr/bin/env python3
"""Tests for the exact gate-proof store."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent
GATE_PROOF = REPO_DIR / "scripts" / "gate_proof.py"


def run(*argv: str, cwd: Path, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [*argv],
        cwd=cwd,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


class GateProofTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.state = self.root / "state"
        self.repo.mkdir()
        run("git", "init", "-q", cwd=self.repo)
        run("git", "config", "user.email", "test@example.invalid", cwd=self.repo)
        run("git", "config", "user.name", "Test", cwd=self.repo)
        (self.repo / ".beislid").mkdir()
        (self.repo / ".beislid" / "workflow.md").write_text("# workflow\n", encoding="utf-8")
        (self.repo / "README.md").write_text("hello\n", encoding="utf-8")
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-q", "-m", "init", cwd=self.repo)
        self.base = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout.strip()
        repository_id = run("git", "rev-list", "--max-parents=0", "HEAD", cwd=self.repo).stdout.strip()[:12]

        self.request = self.root / "request.json"
        self.request.write_text(
            json.dumps(
                {
                    "kind": "gate-proof-request-v1",
                    "gate": {
                        "name": "validate",
                        "scope": "repo",
                        "cwd": ".",
                        "command": "python3 scripts/validate.py",
                        "mutates": False,
                        "evidence_reuse": {
                            "mode": "exact",
                            "environment": {
                                "variables": ["TEST_GATE_PROOF_ENV"],
                                "commands": [["python3", "--version"]],
                            },
                        },
                    },
                    "selection": {"base": self.base},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.run_dir = self.state / "runs" / "ready-for-review" / repository_id / "run-1"
        attempt_dir = self.run_dir / "artifacts" / "gates" / "repo" / "validate" / "1"
        attempt_dir.mkdir(parents=True)
        (self.run_dir / "run.json").write_text(
            json.dumps({"kind": "run-ledger-v1", "run_id": "run-1"}) + "\n",
            encoding="utf-8",
        )
        self.gate_log = attempt_dir / "envelope.json"
        self.gate_log.write_text(
            json.dumps(
                {
                    "gate": {
                        "name": "validate",
                        "scope": "repo",
                        "cwd": ".",
                        "command": "python3 scripts/validate.py",
                    },
                    "status": "pass",
                    "duration_ms": 42,
                    "summary": "green",
                    "raw_logs": {"path": str(attempt_dir / "raw.log")},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (attempt_dir / "raw.log").write_text("ok\n", encoding="utf-8")
        self.env = {
            "BEISLID_STATE_DIR": str(self.state),
            "TEST_GATE_PROOF_ENV": "stable",
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def invoke(self, command: str, *extra: str) -> dict[str, object]:
        result = run(
            "python3",
            str(GATE_PROOF),
            command,
            "--request-file",
            str(self.request),
            *extra,
            cwd=self.repo,
            env=self.env,
        )
        return json.loads(result.stdout)

    def request_payload(self) -> dict[str, object]:
        return json.loads(self.request.read_text(encoding="utf-8"))

    def write_request(self, payload: dict[str, object]) -> None:
        self.request.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def record(self) -> dict[str, object]:
        return self.invoke(
            "record",
            "--envelope-file",
            str(self.gate_log),
            "--run-id",
            "run-1",
        )

    def test_exact_miss_record_hit(self) -> None:
        miss = self.invoke("lookup")
        self.assertEqual("gate-proof-decision-v1", miss["kind"])
        self.assertEqual("rerun", miss["decision"])
        self.assertEqual("proof_missing", miss["reason"])

        recorded = self.record()
        self.assertEqual("gate-proof-record-v1", recorded["kind"])
        self.assertEqual("recorded", recorded["status"])
        self.assertTrue(recorded["proof_key"])

        hit = self.invoke("lookup")
        self.assertEqual("reuse", hit["decision"])
        self.assertEqual("exact_match", hit["reason"])
        self.assertEqual(recorded["proof_key"], hit["proof_key"])

    def test_reuse_requires_explicit_exact_mode(self) -> None:
        payload = self.request_payload()
        payload["gate"]["evidence_reuse"]["mode"] = "off"
        self.write_request(payload)
        result = self.invoke("lookup")
        self.assertEqual("rerun", result["decision"])
        self.assertEqual("reuse_not_enabled", result["reason"])

    def test_mutating_gate_is_never_reused(self) -> None:
        payload = self.request_payload()
        payload["gate"]["mutates"] = True
        self.write_request(payload)
        result = self.invoke("lookup")
        self.assertEqual("gate_mutates", result["reason"])

    def test_dirty_worktree_is_never_reused(self) -> None:
        (self.repo / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
        result = self.invoke("lookup")
        self.assertEqual("dirty_worktree", result["reason"])

    def test_changed_environment_produces_a_miss(self) -> None:
        recorded = self.record()
        self.assertEqual("recorded", recorded["status"])
        self.env["TEST_GATE_PROOF_ENV"] = "changed"
        result = self.invoke("lookup")
        self.assertEqual("proof_missing", result["reason"])
        self.assertNotEqual(recorded["proof_key"], result["proof_key"])

    def test_changed_head_produces_a_miss(self) -> None:
        recorded = self.record()
        (self.repo / "next.txt").write_text("next\n", encoding="utf-8")
        run("git", "add", "next.txt", cwd=self.repo)
        run("git", "commit", "-q", "-m", "next", cwd=self.repo)
        result = self.invoke("lookup")
        self.assertEqual("proof_missing", result["reason"])
        self.assertNotEqual(recorded["proof_key"], result["proof_key"])

    def test_distinct_clone_does_not_reuse_local_repository_proof(self) -> None:
        recorded = self.record()
        clone = self.root / "clone"
        run("git", "clone", "-q", str(self.repo), str(clone), cwd=self.root)
        result = run(
            "python3",
            str(GATE_PROOF),
            "lookup",
            "--request-file",
            str(self.request),
            cwd=clone,
            env=self.env,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("proof_missing", payload["reason"])
        self.assertNotEqual(recorded["proof_key"], payload["proof_key"])

    def test_linked_worktree_reuses_shared_repository_proof(self) -> None:
        recorded = self.record()
        worktree = self.root / "worktree"
        run("git", "worktree", "add", "-q", "--detach", str(worktree), "HEAD", cwd=self.repo)
        result = run(
            "python3",
            str(GATE_PROOF),
            "lookup",
            "--request-file",
            str(self.request),
            cwd=worktree,
            env=self.env,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("exact_match", payload["reason"])
        self.assertEqual(recorded["proof_key"], payload["proof_key"])

    def test_failed_environment_probe_forces_rerun(self) -> None:
        payload = self.request_payload()
        payload["gate"]["evidence_reuse"]["environment"]["commands"] = [["python3", "-c", "raise SystemExit(7)"]]
        self.write_request(payload)
        result = self.invoke("lookup")
        self.assertEqual("environment_probe_failed", result["reason"])

    def test_non_passing_envelope_is_not_recorded(self) -> None:
        envelope = json.loads(self.gate_log.read_text(encoding="utf-8"))
        envelope["status"] = "fail"
        self.gate_log.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
        result = self.record()
        self.assertEqual("skipped", result["status"])
        self.assertEqual("gate_not_passing", result["reason"])

    def test_mismatched_envelope_is_not_recorded(self) -> None:
        envelope = json.loads(self.gate_log.read_text(encoding="utf-8"))
        envelope["gate"]["command"] = "different command"
        self.gate_log.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
        result = self.record()
        self.assertEqual("envelope_mismatch", result["reason"])

    def test_missing_and_changed_artifacts_force_rerun(self) -> None:
        self.record()
        raw_log = self.gate_log.parent / "raw.log"
        raw_log.unlink()
        missing = self.invoke("lookup")
        self.assertEqual("artifact_missing", missing["reason"])

        raw_log.write_text("ok\n", encoding="utf-8")
        self.record()
        raw_log.write_text("changed\n", encoding="utf-8")
        changed = self.invoke("lookup")
        self.assertEqual("artifact_changed", changed["reason"])

    def test_corrupt_proof_forces_rerun(self) -> None:
        recorded = self.record()
        Path(str(recorded["proof_path"])).write_text("{broken\n", encoding="utf-8")
        result = self.invoke("lookup")
        self.assertEqual("proof_corrupt", result["reason"])

    def test_record_rejects_envelope_outside_the_run_ledger(self) -> None:
        outside = self.root / "outside-envelope.json"
        outside.write_text(self.gate_log.read_text(encoding="utf-8"), encoding="utf-8")
        result = self.invoke(
            "record",
            "--envelope-file",
            str(outside),
            "--run-id",
            "run-1",
        )
        self.assertEqual("skipped", result["status"])
        self.assertEqual("envelope_not_ledger", result["reason"])

    def test_concurrent_records_remain_valid(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: self.record(), range(16)))
        self.assertTrue(all(item["status"] == "recorded" for item in results))
        result = self.invoke("lookup")
        self.assertEqual("reuse", result["decision"])

    def test_cli_dispatch(self) -> None:
        result = run(
            str(REPO_DIR / "bin" / "beislid"),
            "gate-proof",
            "lookup",
            "--request-file",
            str(self.request),
            cwd=self.repo,
            env={**self.env, "BEISLID_HOME": str(REPO_DIR)},
        )
        payload = json.loads(result.stdout)
        self.assertEqual("gate-proof-decision-v1", payload["kind"])


if __name__ == "__main__":
    unittest.main()
