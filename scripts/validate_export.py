#!/usr/bin/env python3
"""Read-only validator for approved-slice-plan-export-v0 bundles.

Validates `.beislid/exports/<bundle-id>/` directories produced by the
`envelope` skill so external runners (and `doctor`) can trust
`status: approved` without a model in the loop. The validator never
writes; proof that validation ran is its exit code plus the run
ledger / commit that follows a passing run.

Shape (required fields, types, enums) is declared in
schemas/approved-slice-plan-export-v0.schema.json and
schemas/execution-envelope-v0.schema.json, and enforced here by the
stdlib-only interpreter in schema_check.py (BEI-134). Semantics the
declarative subset cannot express - cycle detection, parallel-group
transitive closure, supersedes/version pairing, slice_id-matches-filename,
the prompt-or-body fallback, non-empty-list checks, and child/slice-file
cross-referencing - stay here as code. See each schema's `$comment` header
for the exact boundary.

Usage: validate_export.py <bundle-dir>
Exit codes: 0 valid, 1 invalid (line-itemized errors on stderr), 2 usage.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

import schema_check

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUNDLE_SCHEMA_PATH = ROOT / "schemas" / "approved-slice-plan-export-v0.schema.json"
SLICE_SCHEMA_PATH = ROOT / "schemas" / "execution-envelope-v0.schema.json"

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
SUPERSEDES_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _load_schema(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


BUNDLE_SCHEMA = _load_schema(BUNDLE_SCHEMA_PATH)
SLICE_SCHEMA = _load_schema(SLICE_SCHEMA_PATH)


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


def _transitive_deps(graph: object) -> dict[str, set[str]]:
    """Map each graph node to the set of slices it transitively depends on."""
    deps_of: dict[str, list[str]] = {}
    if isinstance(graph, dict):
        for node, deps in graph.items():
            if isinstance(deps, list):
                deps_of[node] = [d for d in deps if isinstance(d, str)]

    closure: dict[str, set[str]] = {}
    for start in deps_of:
        reached: set[str] = set()
        stack = list(deps_of.get(start, []))
        while stack:
            node = stack.pop()
            if node in reached:
                continue
            reached.add(node)
            stack.extend(deps_of.get(node, []))
        closure[start] = reached
    return closure


def _validate_parallel_groups(
    slice_plan: object, graph: object, child_ids: list[str], errors: list[str]
) -> None:
    if not isinstance(slice_plan, dict) or "parallel_groups" not in slice_plan:
        return

    groups = slice_plan["parallel_groups"]
    if not isinstance(groups, list) or not all(isinstance(g, list) for g in groups):
        errors.append("slice_plan.parallel_groups: must be a list of lists of slice ids")
        return

    known = set(child_ids)
    seen: set[str] = set()
    for idx, group in enumerate(groups):
        for slice_id in group:
            if not isinstance(slice_id, str) or slice_id not in known:
                errors.append(f"slice_plan.parallel_groups[{idx}]: unknown slice {slice_id!r}")
                continue
            if slice_id in seen:
                errors.append(
                    f"slice_plan.parallel_groups: slice '{slice_id}' appears in more than one group entry"
                )
            seen.add(slice_id)

    closure = _transitive_deps(graph)
    for idx, group in enumerate(groups):
        members = [s for s in group if isinstance(s, str) and s in known]
        for slice_id in members:
            for other in members:
                if other != slice_id and other in closure.get(slice_id, set()):
                    errors.append(
                        f"slice_plan.parallel_groups[{idx}]: '{slice_id}' depends (transitively) on "
                        f"'{other}'; dependent slices cannot share a parallel group"
                    )


def _validate_model_routing_list_semantics(name: str, manifest: dict, errors: list[str]) -> None:
    """Non-empty-list checks the schema subset can't express (no minItems).

    Everything else about runner_extensions.model_routing shape (required
    keys, enums, item shape) is enforced by SLICE_SCHEMA.
    """
    extensions = manifest.get("runner_extensions")
    if not isinstance(extensions, dict):
        return
    routing = extensions.get("model_routing")
    if not isinstance(routing, dict):
        return

    candidates = routing.get("candidates")
    if isinstance(candidates, list) and not candidates:
        errors.append(
            f"{name}: runner_extensions.model_routing.candidates must be a non-empty list of non-empty strings"
        )

    boundary_rules = routing.get("routing")
    if isinstance(boundary_rules, list) and not boundary_rules:
        errors.append(
            f"{name}: runner_extensions.model_routing.routing must be a non-empty list of boundary rules"
        )


def _validate_slice(path: pathlib.Path, expected_id: str, errors: list[str]) -> None:
    manifest = _load_json(path, errors)
    if manifest is None:
        return

    errors.extend(schema_check.validate(manifest, SLICE_SCHEMA, root_label=path.name))

    # Semantics the declarative schema subset cannot express:
    slice_id = manifest.get("slice_id")
    if _nonempty_string(slice_id) and slice_id != expected_id:
        errors.append(f"{path.name}: slice_id '{slice_id}' does not match filename slice id '{expected_id}'")

    prompt = manifest.get("prompt") or manifest.get("body")
    if not _nonempty_string(prompt):
        errors.append(f"{path.name}: prompt (or body) must be a non-empty string")

    _validate_model_routing_list_semantics(path.name, manifest, errors)


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

    errors.extend(schema_check.validate(bundle, BUNDLE_SCHEMA, root_label="bundle.json"))

    # version, re-derived (not re-reported) purely to gate the supersedes
    # pairing check below; any type/range problem was already reported by
    # the schema check above.
    version = bundle["version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        version = None

    # supersedes: presence + null-vs-sha256 + version pairing is a cross-field
    # conditional outside the schema subset (see schema $comment) - stays here.
    if "supersedes" not in bundle:
        errors.append("bundle.json: missing required field 'supersedes' (null for first export)")
    else:
        supersedes = bundle["supersedes"]
        if supersedes is not None and (
            not isinstance(supersedes, str) or not SUPERSEDES_PATTERN.match(supersedes)
        ):
            errors.append("bundle.json: supersedes must be null or a 64-char lowercase sha256 hex digest")
        elif version == 1 and supersedes is not None:
            errors.append(
                "bundle.json: supersedes must be null for version 1 (first export supersedes nothing)"
            )
        elif version is not None and version >= 2 and supersedes is None:
            errors.append(
                "bundle.json: supersedes must be the prior bundle.json sha256 for version >= 2 (revision)"
            )

    children = bundle["children"]
    child_ids: list[str] = []
    if not isinstance(children, list) or not children:
        errors.append("bundle.json: children must be a non-empty list of slice references")
    else:
        for child in children:
            if isinstance(child, dict):
                cid = child.get("id")
                if isinstance(cid, str) and cid.strip():
                    child_ids.append(cid)
        duplicates = {cid for cid in child_ids if child_ids.count(cid) > 1}
        for dup in sorted(duplicates):
            errors.append(f"bundle.json: duplicate slice id '{dup}' in children")

    _validate_graph(bundle["dependency_graph"], child_ids, errors)
    _validate_parallel_groups(bundle["slice_plan"], bundle["dependency_graph"], child_ids, errors)

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
