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
KNOWN_TIERS = {"light", "standard", "heavy", "frontier"}
ALLOWED_ROUTING_MODES = {"prefer", "require"}


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
        validation = bundle.get("validation") or {}
        if validation.get("rubric_version") != "afk-rubric-v1":
            errors.append(
                f"validation.rubric_version must be afk-rubric-v1, got {validation.get('rubric_version')!r}"
            )
        hints = bundle.get("model_routing_hints")
        if not isinstance(hints, dict):
            errors.append("bundle missing model_routing_hints")
        else:
            for field in ("initial", "steps", "phases"):
                if field not in hints:
                    errors.append(f"model_routing_hints missing {field}")
            initial = hints.get("initial") or {}
            if not isinstance(initial, dict):
                errors.append("model_routing_hints.initial must be an object")
            else:
                if initial.get("tier") not in KNOWN_TIERS:
                    errors.append(
                        f"model_routing_hints.initial.tier must be one of {sorted(KNOWN_TIERS)}, got {initial.get('tier')!r}"
                    )
                if initial.get("tier") == "standard":
                    errors.append("model_routing_hints.initial should outrank the broad default standard tier")
                if initial.get("mode") not in ALLOWED_ROUTING_MODES:
                    errors.append(
                        f"model_routing_hints.initial.mode must be one of {sorted(ALLOWED_ROUTING_MODES)}, got {initial.get('mode')!r}"
                    )
            for field in ("steps", "phases"):
                entries = hints.get(field)
                if not isinstance(entries, list) or not entries:
                    errors.append(f"model_routing_hints.{field} must be a non-empty list")
                    continue
                for idx, entry in enumerate(entries):
                    if not isinstance(entry, dict):
                        errors.append(f"model_routing_hints.{field}[{idx}] must be an object")
                        continue
                    if entry.get("tier") not in KNOWN_TIERS:
                        errors.append(
                            f"model_routing_hints.{field}[{idx}].tier must be one of {sorted(KNOWN_TIERS)}, got {entry.get('tier')!r}"
                        )
                    if entry.get("mode") not in ALLOWED_ROUTING_MODES:
                        errors.append(
                            f"model_routing_hints.{field}[{idx}].mode must be one of {sorted(ALLOWED_ROUTING_MODES)}, got {entry.get('mode')!r}"
                        )
        children = bundle.get("children") or []
        if not children:
            errors.append("bundle has no children")
        if len(children) != 2:
            errors.append(f"batch bundle must have exactly 2 exported children, got {len(children)}")
        by_ticket: dict[str, str] = {}
        for child in children:
            ticket = child.get("source_ticket")
            if not str(ticket or "").strip():
                errors.append(f"child {child.get('id')!r} missing source_ticket")
            else:
                by_ticket[ticket] = child.get("id")
        if set(by_ticket) != {"WID-7", "WID-8"}:
            errors.append(f"children source_tickets must be WID-7 and WID-8, got {sorted(by_ticket)}")
        else:
            producer = by_ticket["WID-7"]
            consumer = by_ticket["WID-8"]
            graph = bundle.get("dependency_graph") or {}
            if producer not in (graph.get(consumer) or []):
                errors.append(
                    f"dependency_graph missing cross-ticket edge: '{consumer}' must depend on '{producer}'"
                )
            if consumer in (graph.get(producer) or []):
                errors.append(
                    f"dependency edge reversed: producer '{producer}' must not depend on consumer '{consumer}'"
                )
            groups = (bundle.get("slice_plan") or {}).get("parallel_groups")
            if not isinstance(groups, list) or not groups:
                errors.append("slice_plan.parallel_groups missing or empty")
            else:
                producer_groups = [
                    idx for idx, group in enumerate(groups) if isinstance(group, list) and producer in group
                ]
                consumer_groups = [
                    idx for idx, group in enumerate(groups) if isinstance(group, list) and consumer in group
                ]
                if len(producer_groups) != 1 or len(consumer_groups) != 1:
                    errors.append("slice_plan.parallel_groups must include producer and consumer exactly once")
                elif producer_groups[0] == consumer_groups[0]:
                    errors.append("dependent slices share a parallel group")
        slices_dir = bundle_dir / "slices"
        if slices_dir.is_dir():
            known = {c.get("id") for c in children if isinstance(c, dict)}
            for slice_file in sorted(slices_dir.iterdir()):
                if slice_file.suffix in (".json", ".md") and slice_file.stem not in known:
                    errors.append(f"demoted/unknown slice leaked into bundle: slices/{slice_file.name}")
                text = slice_file.read_text(encoding="utf-8", errors="replace")
                if "frobnicate" in text:
                    errors.append(
                        f"slices/{slice_file.name} cites the bogus 'frobnicate' gate; the demoted WID-7 Phase 2 "
                        "slice must appear nowhere in slices/"
                    )
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
            if allowed.get("run_mode") != "supervised-auto":
                errors.append(f"{slice_id}: run_mode must be supervised-auto, got {allowed.get('run_mode')!r}")
            provider = manifest.get("process_provider") or {}
            if provider.get("name") != "claude_code":
                errors.append(f"{slice_id}: process_provider.name must be claude_code, got {provider.get('name')!r}")
            routing = (manifest.get("runner_extensions") or {}).get("model_routing") or {}
            if routing.get("tier") != "standard":
                errors.append(
                    f"{slice_id}: runner_extensions.model_routing.tier must be 'standard', got {routing.get('tier')!r}"
                )
            candidates = routing.get("candidates")
            if (
                not isinstance(candidates, list)
                or not candidates
                or not all(isinstance(c, str) and c.strip() for c in candidates)
            ):
                errors.append(
                    f"{slice_id}: runner_extensions.model_routing.candidates must be a non-empty list of strings, got {candidates!r}"
                )

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

    log = subprocess.run(
        ["git", "-C", str(repo), "log", "--pretty=format:%H %s"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout
    export_sha = next((line.split()[0] for line in log.splitlines() if "Export envelope bundle" in line), None)
    if export_sha is None:
        errors.append("no 'Export envelope bundle' commit found")
    else:
        commit_files = [
            f
            for f in subprocess.run(
                ["git", "-C", str(repo), "show", "--name-only", "--pretty=format:", export_sha],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ).stdout.splitlines()
            if f.strip()
        ]
        if f".beislid/exports/{bundle_id}/bundle.json" not in commit_files:
            errors.append("export commit does not contain bundle.json")
        prefix = f".beislid/exports/{bundle_id}/"
        offenders = [f for f in commit_files if not f.startswith(prefix)]
        if offenders:
            errors.append(f"export commit contains files outside the bundle subtree: {offenders}")
    tracked_checkpoints = subprocess.run(
        ["git", "-C", str(repo), "ls-files", ".beislid/checkpoints"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()
    if tracked_checkpoints:
        errors.append(f"checkpoint pointer must stay untracked, found: {tracked_checkpoints}")

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
