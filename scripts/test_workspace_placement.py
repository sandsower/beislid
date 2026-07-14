#!/usr/bin/env python3
"""End-to-end tests for deterministic workspace placement."""

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


def run(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class WorkspacePlacementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "fixture"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Beislid Test")
        self.git("config", "user.email", "beislid@example.test")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-q", "-m", "Initial fixture")
        self.sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.env = os.environ.copy()
        self.env["BEISLID_STATE_DIR"] = str(Path(self.tmp.name) / "state")
        initialized = run(
            sys.executable,
            str(LEDGER),
            "init",
            "--skill",
            "implement",
            "--flow",
            "implement",
            "--run-id",
            "placement-test",
            cwd=self.repo,
            env=self.env,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.run_id = json.loads(initialized.stdout)["run_id"]

    def git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        result = run("git", *args, cwd=cwd or self.repo)
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)} failed:\n{result.stderr}")
        return result

    def create(self, expected_sha: str) -> subprocess.CompletedProcess[str]:
        return run(
            sys.executable,
            str(HELPER),
            "create",
            "--repo",
            str(self.repo),
            "--expected-sha",
            expected_sha,
            "--manual-root",
            "repo-sibling",
            "--label",
            "worker",
            "--run-id",
            self.run_id,
            "--flow",
            "implement",
            cwd=self.repo,
            env=self.env,
        )

    def test_manual_create_proves_fresh_exact_sha_worktree_and_receipt(self) -> None:
        first = self.create(self.sha)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.create(self.sha)
        self.assertEqual(second.returncode, 0, second.stderr)

        receipts = [json.loads(first.stdout), json.loads(second.stdout)]
        self.assertNotEqual(receipts[0]["placement_id"], receipts[1]["placement_id"])
        self.assertNotEqual(receipts[0]["workspace"]["path"], receipts[1]["workspace"]["path"])
        self.assertNotEqual(receipts[0]["workspace"]["branch"], receipts[1]["workspace"]["branch"])

        expected_root = (self.repo.parent / f"{self.repo.name}-worktrees").resolve()
        worktree_listing = self.git("worktree", "list", "--porcelain").stdout
        for receipt in receipts:
            self.assertEqual(receipt["kind"], "workspace-placement-receipt-v1")
            self.assertEqual(receipt["operation"], "place_mutating_delegate")
            self.assertEqual(receipt["capability"], "verified-manual")
            self.assertEqual(receipt["repository"]["source"], str(self.repo.resolve()))
            self.assertEqual(receipt["repository"]["expected_sha"], self.sha)
            self.assertEqual(receipt["repository"]["actual_sha"], self.sha)
            self.assertEqual(receipt["workspace"]["cleanup_owner"], "beislid")
            self.assertEqual(receipt["workspace"]["created_by"], "beislid")
            self.assertTrue(receipt["workspace"]["clean"])
            self.assertEqual(receipt["ledger"]["run_id"], self.run_id)
            self.assertEqual(receipt["ledger"]["flow"], "implement")

            receipt_path = Path(receipt["ledger"]["receipt_path"])
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(json.loads(receipt_path.read_text(encoding="utf-8")), receipt)

            path = Path(receipt["workspace"]["path"])
            self.assertEqual(path.parent, expected_root)
            self.assertTrue(path.is_dir())
            self.assertEqual(self.git("rev-parse", "HEAD", cwd=path).stdout.strip(), self.sha)
            self.assertEqual(self.git("branch", "--show-current", cwd=path).stdout.strip(), receipt["workspace"]["branch"])
            self.assertEqual(self.git("status", "--porcelain", cwd=path).stdout, "")
            self.assertIn(f"worktree {path}", worktree_listing)
            self.assertIn(f"branch refs/heads/{receipt['workspace']['branch']}", worktree_listing)

        before = sorted(expected_root.iterdir())
        rejected = self.create("0" * 40)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("expected SHA", rejected.stderr)
        self.assertEqual(sorted(expected_root.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
