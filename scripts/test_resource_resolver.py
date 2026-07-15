#!/usr/bin/env python3
"""Tests for deterministic Beislið distribution resource resolution."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESOLVER = ROOT / "scripts" / "resource_resolver.py"
CLI = ROOT / "bin" / "beislid"
RESOURCE_NAMES = {
    "action-policy-protocol": ".beislid/action-policy-protocol.md",
    "artifact-templates": ".beislid/artifact-templates.md",
    "nopal-seam-protocol": ".beislid/nopal-seam-protocol.md",
    "doctor-templates": ".beislid/doctor-templates.md",
    "envelope-templates": ".beislid/envelope-templates.md",
    "kickoff-templates": ".beislid/kickoff-templates.md",
    "output-templates": ".beislid/output-templates.md",
    "probe-semantics": ".beislid/probe-semantics.md",
    "ready-for-review-templates": ".beislid/ready-for-review-templates.md",
    "review-response-templates": ".beislid/review-response-templates.md",
    "visual-surface-protocol": ".beislid/visual-surface-protocol.md",
    "workflow-md-format": ".beislid/workflow-md-format.md",
}


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def copy_runtime(target: Path) -> None:
    (target / "bin").mkdir(parents=True)
    (target / "scripts").mkdir()
    (target / "skills").mkdir()
    (target / ".beislid").mkdir()
    shutil.copy2(CLI, target / "bin" / "beislid")
    shutil.copy2(ROOT / "install.sh", target / "install.sh")
    for name in (
        "install_lib.sh",
        "run_ledger.py",
        "gate_proof.py",
        "workspace_placement.py",
        "action_policy.py",
        "validate_export.py",
        "visual_feedback.py",
        "workflow_normalizer.py",
        "resource_resolver.py",
    ):
        shutil.copy2(ROOT / "scripts" / name, target / "scripts" / name)
    for relative in RESOURCE_NAMES.values():
        source = ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


class ResourceResolverTests(unittest.TestCase):
    def test_registered_resources_resolve_to_canonical_absolute_paths(self) -> None:
        for name, relative in RESOURCE_NAMES.items():
            with self.subTest(name=name):
                result = run(sys.executable, str(RESOLVER), "--root", str(ROOT), name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, str((ROOT / relative).resolve()) + "\n")
                self.assertEqual(result.stderr, "")

    def test_cli_dispatches_resource_resolve(self) -> None:
        result = run(str(CLI), "resource", "resolve", "workflow-md-format")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str((ROOT / RESOURCE_NAMES["workflow-md-format"]).resolve()) + "\n")

    def test_unknown_and_path_like_names_are_usage_errors(self) -> None:
        retired_name = "cr" + "ust-seam-protocol"
        for name in (retired_name, "unknown", "../workflow-md-format", ".beislid/workflow-md-format.md", "workflow.md", ""):
            with self.subTest(name=name):
                args = [sys.executable, str(RESOLVER), "--root", str(ROOT)]
                if name:
                    args.append(name)
                result = run(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_registered_missing_resource_fails_as_incomplete_distribution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-resource-missing-") as tmp:
            result = run(sys.executable, str(RESOLVER), "--root", tmp, "workflow-md-format")
            self.assertEqual(result.returncode, 1)
            self.assertIn("registered resource is missing", result.stderr)

    def test_registered_directory_is_not_a_resource(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-resource-directory-") as tmp:
            path = Path(tmp) / RESOURCE_NAMES["workflow-md-format"]
            path.mkdir(parents=True)
            result = run(sys.executable, str(RESOLVER), "--root", tmp, "workflow-md-format")
            self.assertEqual(result.returncode, 1)
            self.assertIn("not a regular file", result.stderr)

    def test_registered_symlink_cannot_escape_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-resource-escape-") as tmp:
            root = Path(tmp) / "runtime"
            outside = Path(tmp) / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            path = root / RESOURCE_NAMES["workflow-md-format"]
            path.parent.mkdir(parents=True)
            path.symlink_to(outside)
            result = run(sys.executable, str(RESOLVER), "--root", str(root), "workflow-md-format")
            self.assertEqual(result.returncode, 1)
            self.assertIn("escapes runtime root", result.stderr)

    def test_copied_runtime_resolves_its_own_resource(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-resource-copy-") as tmp:
            runtime = Path(tmp) / "runtime"
            copy_runtime(runtime)
            result = run(str(runtime / "bin" / "beislid"), "resource", "resolve", "probe-semantics")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, str((runtime / RESOURCE_NAMES["probe-semantics"]).resolve()) + "\n")

    def test_symlinked_cli_resolves_the_source_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-resource-link-") as tmp:
            link = Path(tmp) / "beislid"
            link.symlink_to(CLI)
            result = run(str(link), "resource", "resolve", "artifact-templates")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, str((ROOT / RESOURCE_NAMES["artifact-templates"]).resolve()) + "\n")

    def test_explicit_beislid_home_recovers_an_incomplete_wrapper_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="beislid-resource-home-") as tmp:
            wrapper = Path(tmp) / "bin" / "beislid"
            wrapper.parent.mkdir(parents=True)
            shutil.copy2(CLI, wrapper)
            env = os.environ.copy()
            env["BEISLID_HOME"] = str(ROOT)
            result = run(str(wrapper), "resource", "resolve", "workflow-md-format", env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, str((ROOT / RESOURCE_NAMES["workflow-md-format"]).resolve()) + "\n")


if __name__ == "__main__":
    unittest.main()
