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
CLI = ROOT / "bin" / "beislid"


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
        return self.helper(
            "create",
            "--repo",
            str(self.repo),
            "--expected-sha",
            expected_sha,
            "--manual-root",
            "repo-sibling",
            "--label",
            "worker",
        )

    def helper(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        command = list(args)
        common = ["--run-id", self.run_id, "--flow", "implement"]
        if "--" in command:
            separator = command.index("--")
            command[separator:separator] = common
        else:
            command.extend(common)
        return run(
            sys.executable,
            str(HELPER),
            *command,
            cwd=self.repo,
            env=env or self.env,
        )

    def write_runtime_fixture(self) -> tuple[Path, Path]:
        provider = Path(self.tmp.name) / "runtime_provider.py"
        provider.write_text(
            """import json
import os
from pathlib import Path

action = os.environ["BEISLID_RUNTIME_ACTION"]
with Path(os.environ["PROVIDER_ACTIONS"]).open("a", encoding="utf-8") as log:
    log.write(action + "\\n")
lease_file = Path(os.environ["BEISLID_RUNTIME_LEASE_FILE"])
mode = os.environ.get("PROVIDER_MODE", "ok")
if action == "allocate":
    bindings = {
        "PRIMARY_DATABASE_URL": "postgres://primary-secret",
        "SHADOW_DATABASE_URL": "postgres://shadow-secret",
        "REDIS_URL": "redis://cache-secret",
    }
    if mode == "missing-binding":
        bindings.pop("SHADOW_DATABASE_URL")
    lease_file.write_text(json.dumps({
        "kind": "runtime-lease-v1",
        "lease_id": "lease-worker-1",
        "expires_at": "2030-01-01T00:00:00+00:00",
        "bindings": bindings,
    }) + "\\n", encoding="utf-8")
elif action == "verify" and mode == "verify-fail":
    raise SystemExit(7)
""",
            encoding="utf-8",
        )
        actions = Path(self.tmp.name) / "provider-actions.log"
        profile = Path(self.tmp.name) / "runtime-profile.json"
        command = f"{sys.executable} {provider}"
        profile.write_text(
            json.dumps(
                {
                    "kind": "runtime-profile-v1",
                    "name": "integration",
                    "required_bindings": [
                        "PRIMARY_DATABASE_URL",
                        "SHADOW_DATABASE_URL",
                        "REDIS_URL",
                    ],
                    "provider": {
                        "allocate": command,
                        "verify": command,
                        "release": command,
                        "reconcile": command,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return profile, actions

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

    def test_runtime_profile_lease_exec_reconcile_and_idempotent_release(self) -> None:
        created = self.create(self.sha)
        self.assertEqual(created.returncode, 0, created.stderr)
        placement_id = json.loads(created.stdout)["placement_id"]
        profile, actions = self.write_runtime_fixture()
        env = dict(self.env)
        env["PROVIDER_ACTIONS"] = str(actions)

        leased = self.helper(
            "lease",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--profile-file",
            str(profile),
            env=env,
        )
        self.assertEqual(leased.returncode, 0, leased.stderr)
        lease = json.loads(leased.stdout)
        self.assertEqual(lease["profile"], "integration")
        self.assertEqual(lease["lease_id"], "lease-worker-1")
        self.assertEqual(
            lease["binding_names"],
            ["PRIMARY_DATABASE_URL", "REDIS_URL", "SHADOW_DATABASE_URL"],
        )
        self.assertEqual(sorted(lease["fingerprints"]), lease["binding_names"])
        self.assertNotIn("primary-secret", leased.stdout)
        self.assertNotIn("shadow-secret", leased.stdout)
        self.assertNotIn("cache-secret", leased.stdout)

        secret_files = list((Path(self.env["BEISLID_STATE_DIR"]) / "secrets").rglob("lease.json"))
        self.assertEqual(len(secret_files), 1)
        self.assertEqual(secret_files[0].stat().st_mode & 0o777, 0o600)

        cli_env = dict(env)
        cli_env["BEISLID_HOME"] = str(ROOT)
        delivered = run(
            str(CLI),
            "workspace",
            "exec",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--profile",
            "integration",
            "--run-id",
            self.run_id,
            "--flow",
            "implement",
            "--",
            sys.executable,
            "-c",
            "import os; print('|'.join([os.environ['PRIMARY_DATABASE_URL'], os.environ['SHADOW_DATABASE_URL'], os.environ['REDIS_URL']]))",
            cwd=self.repo,
            env=cli_env,
        )
        self.assertEqual(delivered.returncode, 0, delivered.stderr)
        self.assertEqual(
            delivered.stdout.strip(),
            "postgres://primary-secret|postgres://shadow-secret|redis://cache-secret",
        )

        reconciled = self.helper(
            "reconcile",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--profile",
            "integration",
            env=env,
        )
        self.assertEqual(reconciled.returncode, 0, reconciled.stderr)

        released = self.helper(
            "release",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--profile",
            "integration",
            env=env,
        )
        self.assertEqual(released.returncode, 0, released.stderr)
        released_again = self.helper(
            "release",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--profile",
            "integration",
            env=env,
        )
        self.assertEqual(released_again.returncode, 0, released_again.stderr)
        self.assertTrue(json.loads(released_again.stdout)["already_released"])
        self.assertEqual(actions.read_text(encoding="utf-8").splitlines().count("release"), 1)

        run_dir = Path(json.loads((Path(self.env["BEISLID_STATE_DIR"]) / "runs" / "implement" / self.repo_hash() / self.run_id / "run.json").read_text(encoding="utf-8"))["paths"]["run_dir"])
        evidence = (run_dir / "artifacts" / "workspaces" / placement_id / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"type": "runtime_leased"', evidence)
        self.assertIn('"type": "runtime_reconciled"', evidence)
        self.assertIn('"type": "runtime_released"', evidence)
        self.assertNotIn("primary-secret", evidence)
        self.assertNotIn("shadow-secret", evidence)
        self.assertNotIn("cache-secret", evidence)

    def repo_hash(self) -> str:
        return self.git("rev-list", "--max-parents=0", "HEAD").stdout.strip()[:12]

    def test_runtime_profile_missing_binding_rolls_back_partial_lease(self) -> None:
        created = self.create(self.sha)
        self.assertEqual(created.returncode, 0, created.stderr)
        placement_id = json.loads(created.stdout)["placement_id"]
        profile, actions = self.write_runtime_fixture()
        env = dict(self.env)
        env["PROVIDER_ACTIONS"] = str(actions)
        env["PROVIDER_MODE"] = "missing-binding"

        leased = self.helper(
            "lease",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--profile-file",
            str(profile),
            env=env,
        )

        self.assertEqual(leased.returncode, 2)
        self.assertIn("missing required runtime bindings: SHADOW_DATABASE_URL", leased.stderr)
        self.assertEqual(actions.read_text(encoding="utf-8").splitlines(), ["allocate", "release"])
        self.assertEqual(list((Path(self.env["BEISLID_STATE_DIR"]) / "secrets").rglob("lease.json")), [])

        run_json = Path(self.env["BEISLID_STATE_DIR"]) / "runs" / "implement" / self.repo_hash() / self.run_id / "run.json"
        run_dir = Path(json.loads(run_json.read_text(encoding="utf-8"))["paths"]["run_dir"])
        evidence = (run_dir / "artifacts" / "workspaces" / placement_id / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"type": "runtime_lease_failed"', evidence)
        self.assertNotIn("primary-secret", evidence)

    def test_preflight_runs_preparation_and_readiness_without_tracked_changes(self) -> None:
        created = self.create(self.sha)
        self.assertEqual(created.returncode, 0, created.stderr)
        receipt = json.loads(created.stdout)
        placement_id = receipt["placement_id"]
        workspace = Path(receipt["workspace"]["path"])
        prepare = Path(self.tmp.name) / "prepare.py"
        prepare.write_text("from pathlib import Path\nPath('.prepared').write_text('ok\\n', encoding='utf-8')\n", encoding="utf-8")
        readiness = Path(self.tmp.name) / "ready.py"
        readiness.write_text("from pathlib import Path\nraise SystemExit(0 if Path('.prepared').is_file() else 1)\n", encoding="utf-8")
        preparation = Path(self.tmp.name) / "preparation.json"
        preparation.write_text(
            json.dumps(
                {
                    "command": f"{sys.executable} {prepare}",
                    "readiness": [f"{sys.executable} {readiness}"],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        checked = self.helper(
            "preflight",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--preparation-file",
            str(preparation),
        )

        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertTrue((workspace / ".prepared").is_file())
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=no", cwd=workspace).stdout, "")
        self.assertEqual(json.loads(checked.stdout)["readiness_checks"], 1)

    def test_preflight_rejects_preparation_that_changes_tracked_files(self) -> None:
        created = self.create(self.sha)
        self.assertEqual(created.returncode, 0, created.stderr)
        receipt = json.loads(created.stdout)
        placement_id = receipt["placement_id"]
        workspace = Path(receipt["workspace"]["path"])
        prepare = Path(self.tmp.name) / "dirty_prepare.py"
        prepare.write_text("from pathlib import Path\nPath('README.md').write_text('changed\\n', encoding='utf-8')\n", encoding="utf-8")
        preparation = Path(self.tmp.name) / "dirty-preparation.json"
        preparation.write_text(
            json.dumps({"command": f"{sys.executable} {prepare}", "readiness": []}) + "\n",
            encoding="utf-8",
        )

        checked = self.helper(
            "preflight",
            "--repo",
            str(self.repo),
            "--placement-id",
            placement_id,
            "--preparation-file",
            str(preparation),
        )

        self.assertEqual(checked.returncode, 2)
        self.assertIn("preparation changed tracked files", checked.stderr)
        self.assertNotEqual(self.git("status", "--porcelain", "--untracked-files=no", cwd=workspace).stdout, "")
        run_json = Path(self.env["BEISLID_STATE_DIR"]) / "runs" / "implement" / self.repo_hash() / self.run_id / "run.json"
        run_dir = Path(json.loads(run_json.read_text(encoding="utf-8"))["paths"]["run_dir"])
        evidence = (run_dir / "artifacts" / "workspaces" / placement_id / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"type": "preflight_failed"', evidence)


if __name__ == "__main__":
    unittest.main()
