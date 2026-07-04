#!/usr/bin/env python3
"""Run the workflow normalizer golden conformance corpus."""

from __future__ import annotations

import difflib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import workflow_normalizer  # noqa: E402

CASES_DIR = ROOT / "tests" / "conformance" / "cases"
MASKED_PATH = "<masked>"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _mask_source_path(envelope: dict[str, Any]) -> dict[str, Any]:
    masked = deepcopy(envelope)
    source = masked.get("source")
    if isinstance(source, dict):
        source["path"] = MASKED_PATH
    return masked


def _format_json(value: Any) -> list[str]:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).splitlines()


def _compare_case(case_dir: Path) -> tuple[bool, str | None]:
    workflow_path = case_dir / "workflow.md"
    expected_path = case_dir / "expected.json"
    actual = workflow_normalizer.normalize_workflow(workflow_path)
    expected = _load_json(expected_path)

    actual_masked = _mask_source_path(actual)
    expected_masked = _mask_source_path(expected)
    if actual_masked == expected_masked:
        return True, None

    diff = difflib.unified_diff(
        _format_json(expected_masked),
        _format_json(actual_masked),
        fromfile=f"{case_dir.name}/expected.json",
        tofile=f"{case_dir.name}/actual.json",
        lineterm="",
    )
    return False, "\n".join(diff)


def main(argv: list[str] | None = None) -> int:
    del argv
    if not CASES_DIR.is_dir():
        print(f"error: conformance cases directory not found: {CASES_DIR}", file=sys.stderr)
        return 1

    case_dirs = sorted(path for path in CASES_DIR.iterdir() if path.is_dir())
    print(f"cases: {len(case_dirs)}")
    if not case_dirs:
        print("error: no conformance cases found", file=sys.stderr)
        return 1

    failures: list[str] = []
    for case_dir in case_dirs:
        ok, diff = _compare_case(case_dir)
        if ok:
            continue
        failures.append(f"=== {case_dir.name} ===\n{diff}")

    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        return 1

    print("conformance: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
