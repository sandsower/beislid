#!/usr/bin/env python3
"""Regression tests for Beislið's clean Nopal identity cutover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OLD = "cr" + "ust"


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    paths = [ROOT / raw.decode() for raw in result.stdout.split(b"\0") if raw]
    return [path for path in paths if path.exists() or path.is_symlink()]


class NopalIdentityTests(unittest.TestCase):
    def test_no_active_tracked_path_or_content_uses_retired_identity(self) -> None:
        stale: list[str] = []
        for path in tracked_files():
            relative = path.relative_to(ROOT).as_posix()
            if relative == "CHANGELOG.md":
                continue
            if OLD in relative.lower():
                stale.append(relative)
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if OLD in text.lower():
                stale.append(relative)
        self.assertEqual(stale, [], f"retired identity remains in active tracked files: {stale}")

    def test_canonical_nopal_contract_files_are_committed(self) -> None:
        expected = {
            ".beislid/nopal-seam-protocol.md",
            ".nopal/nopal.jsonc",
            ".nopal/gates.jsonc",
            ".nopal/policy.jsonc",
            ".nopal/workflow.jsonc",
            ".nopal/integrations.jsonc",
            ".nopal/review_policy.jsonc",
        }
        actual = {path.relative_to(ROOT).as_posix() for path in tracked_files()}
        self.assertTrue(expected.issubset(actual), f"missing canonical Nopal files: {sorted(expected - actual)}")

    def test_dogfood_workflow_uses_nopal_seam(self) -> None:
        workflow = (ROOT / ".beislid/workflow.md").read_text(encoding="utf-8")
        self.assertIn("```beislid:nopal_seam", workflow)
        self.assertIn("binary: nopal", workflow)
        self.assertNotIn(f"```beislid:{OLD}_seam", workflow)


if __name__ == "__main__":
    unittest.main()
