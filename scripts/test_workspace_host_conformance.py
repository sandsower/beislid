#!/usr/bin/env python3
"""Failure-path conformance tests for workspace host adapters."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts" / "workspace_placement.py"
LEDGER = ROOT / "scripts" / "run_ledger.py"
CODEX_CONTEXT = ROOT / "skills" / "implement" / "codex-delegate-context.md"
IMPLEMENT_SKILL = ROOT / "skills" / "implement" / "SKILL.md"
OTHER_HOST_ADAPTERS = (
    ROOT / "skills" / "implement" / "workspace-placement-claude.md",
    ROOT / "skills" / "implement" / "workspace-placement-pi.md",
    ROOT / "skills" / "implement" / "workspace-placement-generic.md",
)
ADAPTER_BUILD = "workspace-placement-v1"
PROOFS = (
    "placement_verified",
    "sha_verified",
    "preparation_verified",
    "runtime_isolation_verified",
    "handoff_verified",
    "integration_verified",
    "cleanup_verified",
)


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
    def test_codex_delegate_context_contract_is_complete(self) -> None:
        self.assertTrue(CODEX_CONTEXT.is_file(), f"missing Codex context protocol: {CODEX_CONTEXT}")
        text = CODEX_CONTEXT.read_text(encoding="utf-8")
        for marker in (
            "# Codex delegate context v1",
            "approved artifact",
            "workspace receipt",
            "exact SHA",
            "authorized scope",
            "success criteria",
            "required gates",
            "handoff contract",
            'fork_turns: "none"',
            "smallest bounded recent context",
            "Full-history",
            "BEISLID_STATE_DIR",
            "git check-ignore",
            "Never edit `.gitignore`",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_codex_transport_rules_do_not_leak_into_other_host_adapters(self) -> None:
        for path in OTHER_HOST_ADAPTERS:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("fork_turns", text)
                self.assertNotIn("BEISLID_STATE_DIR", text)
                self.assertNotIn("codex-delegate-context", text)

    def test_implement_defaults_to_verified_logical_batch_commits(self) -> None:
        text = IMPLEMENT_SKILL.read_text(encoding="utf-8")
        self.assertIn("Commit verified logical batches by default", text)
        self.assertIn("Task-level commits are exceptions", text)
        self.assertIn("codex-delegate-context.md", text)

    @staticmethod
    def complete_evidence(**overrides: object) -> dict[str, object]:
        evidence: dict[str, object] = {
            "kind": "host-placement-evidence-v1",
            "placement_verified": True,
            "sha_verified": True,
            "preparation_verified": True,
            "runtime_isolation_verified": True,
            "handoff_verified": True,
            "integration_verified": True,
            "cleanup_verified": True,
            "_bind_provenance": True,
        }
        evidence.update(overrides)
        return evidence

    def probe(
        self,
        host: str,
        operation: str,
        evidence: dict[str, object],
        *,
        tamper: str | None = None,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            repo = tmp / "repo"
            repo.mkdir()
            self.assertEqual(run("git", "init", "-q", cwd=repo).returncode, 0)
            bound = dict(evidence)
            if bound.pop("_bind_provenance", False):
                generated_at = datetime.now(timezone.utc)
                artifacts: dict[str, object] = {}
                for proof in PROOFS:
                    artifact = {
                        "kind": "host-placement-proof-v1",
                        "proof": proof,
                        "host": host,
                        "operation": operation,
                        "adapter_build": ADAPTER_BUILD,
                        "repository": str(repo.resolve()),
                        "passed": True,
                    }
                    artifact_path = tmp / f"{proof}.json"
                    content = (json.dumps(artifact, sort_keys=True) + "\n").encode()
                    artifact_path.write_bytes(content)
                    artifacts[proof] = {
                        "path": str(artifact_path),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                bound.update(
                    {
                        "host": host,
                        "operation": operation,
                        "adapter_build": ADAPTER_BUILD,
                        "repository": str(repo.resolve()),
                        "generated_at": generated_at.isoformat(),
                        "expires_at": (generated_at + timedelta(hours=1)).isoformat(),
                        "proof_artifacts": artifacts,
                    }
                )
                if tamper == "host":
                    bound["host"] = "another-host"
                elif tamper == "operation":
                    bound["operation"] = "orchestrator" if operation == "delegate" else "delegate"
                elif tamper == "adapter":
                    bound["adapter_build"] = "older-adapter"
                elif tamper == "repository":
                    bound["repository"] = str(tmp / "another-repo")
                elif tamper == "digest":
                    artifacts[PROOFS[0]]["sha256"] = "0" * 64
                elif tamper == "expired":
                    bound["expires_at"] = (generated_at - timedelta(seconds=1)).isoformat()
            evidence_file = tmp / "evidence.json"
            evidence_file.write_text(json.dumps(bound) + "\n", encoding="utf-8")
            result = run(
                sys.executable,
                str(HELPER),
                "probe",
                "--host",
                host,
                "--operation",
                operation,
                "--repo",
                str(repo),
                "--evidence-file",
                str(evidence_file),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_codex_unresolved_fork_requires_manual_transition(self) -> None:
        result = self.probe(
            "codex",
            "orchestrator",
            self.complete_evidence(
                native_conformance_passed=True,
                fork_resolved=False,
                destination_acknowledged=False,
            ),
        )

        self.assertEqual(result["capability"], "unavailable")
        self.assertEqual(result["disposition"], "manual-transition-required")
        self.assertEqual(result["reason_code"], "codex_fork_unresolved")

    def test_pi_orchestrator_requires_relaunch_acknowledgment(self) -> None:
        result = self.probe(
            "pi",
            "orchestrator",
            self.complete_evidence(
                manual_conformance_passed=True,
                cwd_enforced=True,
                relaunch_acknowledged=False,
            ),
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

    def test_synthetic_claude_native_proof_stays_unavailable_without_a_runner(self) -> None:
        result = self.probe(
            "claude",
            "delegate",
            self.complete_evidence(
                native_conformance_passed=True,
                destination_acknowledged=True,
            ),
        )

        self.assertEqual(result["capability"], "unavailable")
        self.assertEqual(result["disposition"], "sequential")
        self.assertEqual(result["reason_code"], "conformance_harness_unavailable")

    def test_partial_evidence_cannot_claim_verified_native(self) -> None:
        result = self.probe(
            "claude",
            "delegate",
            {
                "kind": "host-placement-evidence-v1",
                "native_conformance_passed": True,
                "destination_acknowledged": True,
                "runtime_isolation_verified": True,
                "_bind_provenance": True,
            },
        )

        self.assertEqual(result["capability"], "unavailable")
        self.assertEqual(result["disposition"], "sequential")
        self.assertEqual(result["reason_code"], "conformance_evidence_incomplete")

    def test_unbound_boolean_claim_cannot_claim_verified_native(self) -> None:
        result = self.probe(
            "claude",
            "delegate",
            {
                "kind": "host-placement-evidence-v1",
                **{proof: True for proof in PROOFS},
                "native_conformance_passed": True,
                "destination_acknowledged": True,
            },
        )

        self.assertEqual(result["capability"], "unavailable")
        self.assertEqual(result["reason_code"], "conformance_evidence_incomplete")

    def test_bound_evidence_cannot_be_reused_outside_its_provenance(self) -> None:
        for tamper in ("host", "operation", "adapter", "repository", "digest", "expired"):
            with self.subTest(tamper=tamper):
                result = self.probe(
                    "claude",
                    "delegate",
                    self.complete_evidence(
                        native_conformance_passed=True,
                        destination_acknowledged=True,
                    ),
                    tamper=tamper,
                )
                self.assertEqual(result["capability"], "unavailable")
                self.assertEqual(result["reason_code"], "conformance_evidence_incomplete")

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
            sha = run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
            receipt = tmp / "receipt.json"
            receipt.write_text(
                json.dumps(
                    {
                        "kind": "workspace-placement-receipt-v1",
                        "placement_id": "host-owned",
                        "operation": "ensure_orchestrator_workspace",
                        "capability": "unavailable",
                        "placement_status": "verified",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "concurrency_group": None,
                        "repository": {
                            "source": str(repo.resolve()),
                            "expected_sha": sha,
                            "actual_sha": sha,
                        },
                        "scope": {"write": ["README.md"]},
                        "workspace": {
                            "path": str(workspace),
                            "branch": "host/owned",
                            "clean": True,
                            "cleanup_owner": "host",
                            "created_by": "host",
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
