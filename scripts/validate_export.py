#!/usr/bin/env python3
"""Read-only validator for approved-slice-plan-export-v0 bundles.

Validates `.beislid/exports/<bundle-id>/` directories produced by the
`envelope` skill so external runners (and `doctor`) can trust
`status: approved` without a model in the loop. The validator never
writes; proof that validation ran is its exit code plus the run
ledger / commit that follows a passing run.

Usage: validate_export.py <bundle-dir>
Exit codes: 0 valid, 1 invalid (line-itemized errors on stderr), 2 usage.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

BUNDLE_KIND = "approved-slice-plan-export-v0"
REQUIRED_BUNDLE_FIELDS = (
    "kind",
    "version",
    "status",
    "generated_from",
    "source_work_contract",
    "slice_plan",
    "children",
    "dependency_graph",
    "proof_requirements",
    "guides_and_gates",
    "approval",
    "runner_extensions",
    "validation",
    "ownership",
)
REQUIRED_APPROVAL_FIELDS = ("approved_at", "approved_by")
KNOWN_RUBRIC_VERSIONS = frozenset({"afk-rubric-v0", "afk-rubric-v1"})
ALLOWED_SLICE_SCHEMAS = frozenset({"approved-slice-v1", "rondo-execution-request-v1"})
REQUIRED_REPO_FIELDS = ("url", "base_ref", "base_sha")
SUPERSEDES_PATTERN = re.compile(r"^[0-9a-f]{64}$")
KNOWN_TIERS = frozenset({"light", "standard", "heavy", "frontier"})
ALLOWED_ROUTING_MODES = frozenset({"prefer", "require"})


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_json(path: pathlib.Path, errors: list[str]) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{path.name}: unreadable ({exc})")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name}: invalid JSON ({exc})")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.name}: top level must be a JSON object")
        return None
    return payload


def _validate_graph(graph: object, child_ids: list[str], errors: list[str]) -> None:
    if not isinstance(graph, dict):
        errors.append("dependency_graph: must be an object mapping slice id -> [dependency ids]")
        return

    # Slices absent from the graph implicitly have no dependencies.
    cycle_errors: list[str] = []

    known = set(child_ids)
    for node, deps in graph.items():
        if node not in known:
            errors.append(f"dependency_graph: unknown slice '{node}'")
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            errors.append(f"dependency_graph: dependencies of '{node}' must be a list of slice ids")
            continue
        for dep in deps:
            if dep not in known:
                errors.append(f"dependency_graph: '{node}' depends on unknown slice '{dep}'")

    # Cycle detection via iterative DFS coloring.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    for start in graph:
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        while stack:
            node, idx = stack[-1]
            if color[node] == WHITE:
                color[node] = GRAY
            deps = graph.get(node, [])
            deps = deps if isinstance(deps, list) else []
            advanced = False
            for next_idx in range(idx, len(deps)):
                dep = deps[next_idx]
                if not isinstance(dep, str) or dep not in color:
                    continue
                if color[dep] == GRAY:
                    message = f"dependency_graph: cyclic dependency via edge '{node}' -> '{dep}'"
                    if message not in cycle_errors:
                        cycle_errors.append(message)
                    continue
                if color[dep] == WHITE:
                    stack[-1] = (node, next_idx + 1)
                    stack.append((dep, 0))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()

    errors.extend(cycle_errors)


def _validate_model_routing(name: str, manifest: dict, errors: list[str]) -> None:
    """Validate optional runner_extensions.model_routing tier hints; absent is valid."""
    extensions = manifest.get("runner_extensions")
    if not isinstance(extensions, dict):
        return
    routing = extensions.get("model_routing")
    if routing is None:
        return
    prefix = f"{name}: runner_extensions.model_routing"
    if not isinstance(routing, dict):
        errors.append(f"{prefix} must be an object with tier, mode, candidates")
        return
    tier = routing.get("tier")
    if tier not in KNOWN_TIERS:
        errors.append(f"{prefix}.tier must be one of {sorted(KNOWN_TIERS)}, got {tier!r}")
    mode = routing.get("mode")
    if mode not in ALLOWED_ROUTING_MODES:
        errors.append(f"{prefix}.mode must be one of {sorted(ALLOWED_ROUTING_MODES)}, got {mode!r}")
    candidates = routing.get("candidates")
    if (
        not isinstance(candidates, list)
        or not candidates
        or not all(_nonempty_string(c) for c in candidates)
    ):
        errors.append(f"{prefix}.candidates must be a non-empty list of non-empty strings")


def _validate_slice(path: pathlib.Path, expected_id: str, errors: list[str]) -> None:
    manifest = _load_json(path, errors)
    if manifest is None:
        return

    schema = manifest.get("schema")
    if schema not in ALLOWED_SLICE_SCHEMAS:
        errors.append(f"{path.name}: schema must be one of {sorted(ALLOWED_SLICE_SCHEMAS)}, got {schema!r}")

    slice_id = manifest.get("slice_id")
    if not _nonempty_string(slice_id):
        errors.append(f"{path.name}: slice_id must be a non-empty string")
    elif slice_id != expected_id:
        errors.append(f"{path.name}: slice_id '{slice_id}' does not match filename slice id '{expected_id}'")

    prompt = manifest.get("prompt") or manifest.get("body")
    if not _nonempty_string(prompt):
        errors.append(f"{path.name}: prompt (or body) must be a non-empty string")

    repo = manifest.get("repo")
    if not isinstance(repo, dict):
        errors.append(f"{path.name}: repo must be an object with {', '.join(REQUIRED_REPO_FIELDS)}")
    else:
        for field in REQUIRED_REPO_FIELDS:
            if not _nonempty_string(repo.get(field)):
                errors.append(f"{path.name}: repo.{field} must be a non-empty string")

    _validate_model_routing(path.name, manifest, errors)


def validate_bundle(bundle_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []

    bundle_path = bundle_dir / "bundle.json"
    if not bundle_path.is_file():
        return [f"bundle.json: missing at {bundle_path}"]

    bundle = _load_json(bundle_path, errors)
    if bundle is None:
        return errors

    for field in REQUIRED_BUNDLE_FIELDS:
        if field not in bundle:
            errors.append(f"bundle.json: missing required field '{field}'")
    if errors:
        return errors

    if bundle["kind"] != BUNDLE_KIND:
        errors.append(f"bundle.json: kind must be '{BUNDLE_KIND}', got {bundle['kind']!r}")

    if bundle["status"] != "approved":
        errors.append(
            f"bundle.json: status must be 'approved' for export (fail-closed), got {bundle['status']!r}"
        )

    if not isinstance(bundle["version"], int) or bundle["version"] < 1:
        errors.append("bundle.json: version must be a positive integer")

    if "supersedes" not in bundle:
        errors.append("bundle.json: missing required field 'supersedes' (null for first export)")
    else:
        supersedes = bundle["supersedes"]
        if supersedes is not None and (
            not isinstance(supersedes, str) or not SUPERSEDES_PATTERN.match(supersedes)
        ):
            errors.append("bundle.json: supersedes must be null or a 64-char lowercase sha256 hex digest")

    approval = bundle["approval"]
    if not isinstance(approval, dict):
        errors.append("bundle.json: approval must be an object")
    else:
        for field in REQUIRED_APPROVAL_FIELDS:
            if not _nonempty_string(approval.get(field)):
                errors.append(f"bundle.json: approval.{field} must be a non-empty string")

    validation = bundle["validation"]
    if not isinstance(validation, dict):
        errors.append("bundle.json: validation must be an object")
    else:
        if validation.get("schema_version") != BUNDLE_KIND:
            errors.append(f"bundle.json: validation.schema_version must be '{BUNDLE_KIND}'")
        rubric = validation.get("rubric_version")
        if not _nonempty_string(rubric):
            errors.append("bundle.json: validation.rubric_version must be a non-empty string")
        elif rubric not in KNOWN_RUBRIC_VERSIONS:
            errors.append(
                f"bundle.json: unknown rubric_version {rubric!r}; known: {sorted(KNOWN_RUBRIC_VERSIONS)}"
            )

    children = bundle["children"]
    child_ids: list[str] = []
    if not isinstance(children, list) or not children:
        errors.append("bundle.json: children must be a non-empty list of slice references")
    else:
        for idx, child in enumerate(children):
            child_id = child.get("id") if isinstance(child, dict) else None
            if not _nonempty_string(child_id):
                errors.append(f"bundle.json: children[{idx}] must have a non-empty string 'id'")
                continue
            child_ids.append(child_id)
        duplicates = {cid for cid in child_ids if child_ids.count(cid) > 1}
        for dup in sorted(duplicates):
            errors.append(f"bundle.json: duplicate slice id '{dup}' in children")

    _validate_graph(bundle["dependency_graph"], child_ids, errors)

    slices_dir = bundle_dir / "slices"
    for child_id in child_ids:
        manifest_path = slices_dir / f"{child_id}.json"
        summary_path = slices_dir / f"{child_id}.md"
        if not manifest_path.is_file():
            errors.append(f"slices/{child_id}.json: missing manifest for child slice '{child_id}'")
        else:
            _validate_slice(manifest_path, child_id, errors)
        if not summary_path.is_file():
            errors.append(f"slices/{child_id}.md: missing human-readable summary for '{child_id}'")

    if slices_dir.is_dir():
        known = set(child_ids)
        for manifest_path in sorted(slices_dir.glob("*.json")):
            if manifest_path.stem not in known:
                errors.append(
                    f"slices/{manifest_path.name}: orphan slice manifest with no matching children entry"
                )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    bundle_dir = pathlib.Path(argv[1])
    if not bundle_dir.is_dir():
        print(f"error: bundle directory not found: {bundle_dir}", file=sys.stderr)
        return 1

    errors = validate_bundle(bundle_dir)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"invalid: {len(errors)} error(s) in {bundle_dir}", file=sys.stderr)
        return 1

    print(f"valid: {bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
