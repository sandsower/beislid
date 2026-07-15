#!/usr/bin/env python3
"""Failure-path conformance tests for workspace host adapters."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "workspace_placement.py"
LEDGER = ROOT / "scripts" / "run_ledger.py"


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class WorkspaceHostConformanceTests(unittest.TestCase):
    def probe(self, host: str, operation: str, evidence: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp_name:
            evidence_file = Path(tmp_name) / "evidence.json"
            evidence_file.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            result = run(
                sys.executable,
                str(HELPER),
                "probe",
                "--host",
                host,
                "--operation",
                operation,
                "--evidence-file",
                str(evidence_file),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_codex_unresolved_fork_requires_manual_transition(self) -> None:
        result = self.probe(
            "codex",
            "orchestrator",
            {
                "kind": "host-placement-evidence-v1",
                "native_conformance_passed": True,
                "fork_resolved": False,
                "destination_acknowledged": False,
            },
        )

        self.assertEqual(result["capability"], "unavailable")
        self.assertEqual(result["disposition"], "manual-transition-required")
        self.assertEqual(result["reason_code"], "codex_fork_unresolved")

    def test_pi_orchestrator_requires_relaunch_acknowledgment(self) -> None:
        result = self.probe(
            "pi",
            "orchestrator",
            {
                "kind": "host-placement-evidence-v1",
                "manual_conformance_passed": True,
                "cwd_enforced": True,
                "relaunch_acknowledged": False,
            },
        )

        self.assertEqual(result["capability"], "unavailable")
        self.assertEqual(result["disposition"], "manual-transition-required")
        self.assertEqual(result["reason_code"], "pi_relaunch_required")

    def test_unknown_host_delegate_falls_back_to_sequential(self) -> None:
        result = self.probe(
            "future-host",
            "delegate",
            {"kind": "host-placement-evidence-v1"},
        )

        self.assertEqual(result["host_adapter"], "generic")
        self.assertEqual(result["capability"], "unavailable")
        self.assertEqual(result["disposition"], "sequential")
        self.assertEqual(result["reason_code"], "manual_path_unverified")

    def test_verified_claude_native_path_is_ready(self) -> None:
        result = self.probe(
            "claude",
            "delegate",
            {
                "kind": "host-placement-evidence-v1",
                "native_conformance_passed": True,
                "destination_acknowledged": True,
                "runtime_isolation_verified": True,
            },
        )

        self.assertEqual(result["capability"], "verified-native")
        self.assertEqual(result["disposition"], "ready")

    def test_host_owned_cleanup_never_removes_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            repo = tmp / "repo"
            repo.mkdir()
            self.assertEqual(run("git", "init", "-q", cwd=repo).returncode, 0)
            self.assertEqual(run("git", "config", "user.name", "Test", cwd=repo).returncode, 0)
            self.assertEqual(run("git", "config", "user.email", "test@example.invalid", cwd=repo).returncode, 0)
            (repo / "README.md").write_text("fixture\n", encoding="utf-8")
            self.assertEqual(run("git", "add", "README.md", cwd=repo).returncode, 0)
            self.assertEqual(run("git", "commit", "-q", "-m", "fixture", cwd=repo).returncode, 0)
            env = os.environ.copy()
            env["BEISLID_STATE_DIR"] = str(tmp / "state")
            initialized = run(
                sys.executable,
                str(LEDGER),
                "init",
                "--skill",
                "implement",
                "--flow",
                "implement",
                "--run-id",
                "host-cleanup",
                cwd=repo,
                env=env,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            workspace = tmp / "host-workspace"
            workspace.mkdir()
            sentinel = workspace / "owned-by-host"
            sentinel.write_text("keep\n", encoding="utf-8")
            receipt = tmp / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "kind": "workspace-placement-receipt-v1",
                        "placement_id": "host-owned",
                        "workspace": {
                            "path": str(workspace),
                            "branch": "host/owned",
                            "cleanup_owner": "host",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            recorded = run(
                sys.executable,
                str(LEDGER),
                "workspace-receipt",
                "--run-id",
                "host-cleanup",
                "--flow",
                "implement",
                "--json-file",
                str(receipt),
                cwd=repo,
                env=env,
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr)

            cleaned = run(
                sys.executable,
                str(HELPER),
                "cleanup",
                "--repo",
                str(repo),
                "--placement-id",
                "host-owned",
                "--run-id",
                "host-cleanup",
                "--flow",
                "implement",
                cwd=repo,
                env=env,
            )

            self.assertEqual(cleaned.returncode, 0, cleaned.stderr)
            payload = json.loads(cleaned.stdout)
            self.assertEqual(payload["disposition"], "host-cleanup-required")
            self.assertTrue(sentinel.is_file())


if __name__ == "__main__":
    unittest.main()
