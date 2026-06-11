#!/usr/bin/env python3
"""Verify a host-agent envelope smoke run."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_STAMPS = [
    "✓ envelope/step-1-intake v1 loaded",
    "✓ envelope/step-2-author v1 loaded",
    "✓ envelope/step-3-approve v1 loaded",
    "✓ envelope/step-4-export v1 loaded",
]

PROMPT_SECTIONS = ["## Objective", "## Design summary", "## File scope", "## Constraints", "## Verification"]


def load_metadata(run_dir: Path) -> dict:
    path = run_dir / "metadata.json"
    if not path.exists():
        raise SystemExit(f"missing metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_json(path: Path, errors: list[str], label: str) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: unreadable or invalid JSON ({exc})")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label}: top level must be a JSON object")
        return None
    return payload


def agent_output_text(run_dir: Path) -> str:
    chunks: list[str] = []
    for path in sorted(run_dir.glob("*.log")):
        chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    metadata = load_metadata(run_dir)
    repo = Path(metadata["repo"])
    bundle_id = metadata["bundle_id"]
    beislid_root = Path(metadata["beislid_root"])
    errors: list[str] = []

    bundle_dir = repo / ".beislid" / "exports" / bundle_id
    bundle_json = bundle_dir / "bundle.json"
    if not bundle_json.is_file():
        errors.append(f"missing export bundle: {bundle_json}")
    else:
        validator = subprocess.run(
            [sys.executable, str(beislid_root / "scripts" / "validate_export.py"), str(bundle_dir)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if validator.returncode != 0:
            errors.append(f"validator failed (exit {validator.returncode}):\n{validator.stdout}")

        bundle = load_json(bundle_json, errors, "bundle.json") or {}
        if bundle and bundle.get("status") != "approved":
            errors.append(f"bundle status must be approved, got {bundle.get('status')!r}")
        children = bundle.get("children") or []
        if not children:
            errors.append("bundle has no children")
        for child in children:
            slice_id = child.get("id")
            manifest_path = bundle_dir / "slices" / f"{slice_id}.json"
            summary_path = bundle_dir / "slices" / f"{slice_id}.md"
            if not manifest_path.is_file():
                errors.append(f"missing slice manifest: {manifest_path}")
                continue
            if not summary_path.is_file():
                errors.append(f"missing slice summary: {summary_path}")
            manifest = load_json(manifest_path, errors, f"slices/{slice_id}.json")
            if manifest is None:
                continue
            if manifest.get("schema") != "approved-slice-v1":
                errors.append(f"{slice_id}: schema must be approved-slice-v1")
            prompt = manifest.get("prompt") or ""
            for section in PROMPT_SECTIONS:
                if section.lower() not in prompt.lower():
                    errors.append(f"{slice_id}: prompt missing section {section!r}")
            repo_pin = manifest.get("repo") or {}
            for field in ("url", "base_ref", "base_sha"):
                if not str(repo_pin.get(field) or "").strip():
                    errors.append(f"{slice_id}: repo.{field} missing")
            allowed = manifest.get("allowed_actions") or {}
            for field in ("run_mode", "allow", "ask", "deny"):
                if field not in allowed:
                    errors.append(f"{slice_id}: allowed_actions.{field} missing")

    checkpoint_path = repo / ".beislid" / "checkpoints" / "latest.json"
    if not checkpoint_path.is_file():
        errors.append(f"missing checkpoint pointer: {checkpoint_path}")
    else:
        pointer = load_json(checkpoint_path, errors, "checkpoints/latest.json")
        if pointer is not None:
            latest = pointer.get("latest") or {}
            if "envelope_exported" not in latest:
                errors.append("latest.json has no envelope_exported entry")
            elif latest["envelope_exported"].get("source_skill") != "envelope":
                errors.append("envelope_exported pointer source_skill must be 'envelope'")

    committed = subprocess.run(
        ["git", "-C", str(repo), "log", "--name-only", "--pretty=format:%s"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout
    if f".beislid/exports/{bundle_id}/bundle.json" not in committed:
        errors.append("bundle.json was not committed")

    output = agent_output_text(run_dir)
    for stamp in REQUIRED_STAMPS:
        if stamp not in output:
            errors.append(f"missing aux load stamp: {stamp!r}")
    if re.search(r"src/widget_export\.py", output) is None:
        errors.append("agent output never references the fixture widget module")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("envelope smoke verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
