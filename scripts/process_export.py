#!/usr/bin/env python3
"""Render Beislið process config into a committed ProcessProvider artifact.

`export` reads `.beislid/workflow.md` gates plus the action policy
(`.beislid/action-policy.json`, falling back to the inline
`beislid:action_policy` block) and writes a `beislid-process-artifact-v1`
JSON to `.beislid/exports/process.json`. The output is byte-stable: no
timestamps, sorted keys. Committing the artifact is the approval act.

`check` is the freshness gate: it recomputes source hashes, re-renders the
artifact in memory, and fails red when the committed artifact is stale or
hand-edited.

The fenced-block parser accepts only the restricted YAML subset documented
for workflow.md (flat scalar values, nested maps, lists of flat maps). It
fails closed on anything else rather than guessing; rondo's ProcessProvider
validates the artifact fail-closed on its side too.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from action_policy import normalize_policy  # noqa: E402

ARTIFACT_SCHEMA = "beislid-process-artifact-v1"
WORKFLOW_HEADER = "<!-- beislid-workflow: v1 -->"
WORKFLOW_REL = ".beislid/workflow.md"
POLICY_REL = ".beislid/action-policy.json"
ARTIFACT_REL = ".beislid/exports/process.json"

# Gate fields that are part of the rondo artifact contract. Everything else
# (cost, mutates, parallel_safe, ...) is workflow.md-side metadata and is
# intentionally dropped from the export.
GATE_PASSTHROUGH = ("action_id", "reason")

FENCE_RE = re.compile(r"^```beislid:(?P<key>[a-z_]+)\s*$")
UNSUPPORTED_VALUE_PREFIXES = ("|", ">", "{", "[", "&", "*", "?")


class ExportError(SystemExit):
    def __init__(self, message: str):
        super().__init__(f"process export: {message}")


def extract_block(text: str, key: str) -> list[str] | None:
    lines = text.splitlines()
    block: list[str] | None = None
    i = 0
    while i < len(lines):
        match = FENCE_RE.match(lines[i])
        if match and match.group("key") == key:
            if block is not None:
                raise ExportError(f"duplicate beislid:{key} block in {WORKFLOW_REL}")
            block = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                block.append(lines[i])
                i += 1
            if i >= len(lines):
                raise ExportError(f"unterminated beislid:{key} block in {WORKFLOW_REL}")
        i += 1
    return block


def tokenize(block_lines: list[str], context: str) -> list[tuple[int, str]]:
    tokens: list[tuple[int, str]] = []
    for raw in block_lines:
        if "\t" in raw:
            raise ExportError(f"{context}: tabs are not supported in the YAML subset")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        tokens.append((indent, stripped))
    return tokens


def parse_scalar(value: str, context: str) -> Any:
    value = value.strip()
    if value.startswith(UNSUPPORTED_VALUE_PREFIXES):
        raise ExportError(
            f"{context}: unsupported YAML construct in value {value!r}; "
            "only plain scalars, nested maps, and lists of flat maps are allowed"
        )
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def split_key(content: str, context: str) -> tuple[str, str]:
    if ": " in content:
        key, value = content.split(": ", 1)
    elif content.endswith(":"):
        key, value = content[:-1], ""
    else:
        raise ExportError(f"{context}: expected 'key: value' or 'key:' line, got {content!r}")
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.\-/]+", key):
        raise ExportError(f"{context}: unsupported map key {key!r}")
    return key, value.strip()


def parse_nodes(tokens: list[tuple[int, str]], context: str) -> Any:
    if not tokens:
        return None
    if tokens[0][1].startswith("- "):
        return parse_list(tokens, context)
    return parse_map(tokens, context)


def parse_list(tokens: list[tuple[int, str]], context: str) -> list[Any]:
    indent = tokens[0][0]
    items: list[Any] = []
    i = 0
    while i < len(tokens):
        tok_indent, content = tokens[i]
        if tok_indent != indent or not content.startswith("- "):
            raise ExportError(f"{context}: inconsistent list structure at {content!r}")
        rest = content[2:].strip()
        sub: list[tuple[int, str]] = []
        i += 1
        while i < len(tokens) and tokens[i][0] > indent:
            sub.append(tokens[i])
            i += 1
        if ":" in rest:
            items.append(parse_map([(indent + 2, rest)] + sub, context))
        elif sub:
            raise ExportError(f"{context}: scalar list item {rest!r} cannot have nested lines")
        else:
            items.append(parse_scalar(rest, context))
    return items


def parse_map(tokens: list[tuple[int, str]], context: str) -> dict[str, Any]:
    indent = tokens[0][0]
    result: dict[str, Any] = {}
    i = 0
    while i < len(tokens):
        tok_indent, content = tokens[i]
        if tok_indent != indent:
            raise ExportError(f"{context}: inconsistent indentation at {content!r}")
        if content.startswith("- "):
            raise ExportError(f"{context}: unexpected list item {content!r} inside a map")
        key, value = split_key(content, context)
        if key in result:
            raise ExportError(f"{context}: duplicate key {key!r}")
        sub: list[tuple[int, str]] = []
        i += 1
        while i < len(tokens) and tokens[i][0] > indent:
            sub.append(tokens[i])
            i += 1
        if value:
            scalar = parse_scalar(value, context)
            if sub:
                raise ExportError(f"{context}: key {key!r} has both a value and nested lines")
            result[key] = scalar
        elif sub:
            result[key] = parse_nodes(sub, context)
        else:
            raise ExportError(f"{context}: key {key!r} has no value")
    return result


def repo_id(repo: Path) -> str:
    """Checkout-independent repo identity for the artifact `id`.

    `check` re-renders the artifact and byte-compares, so the id must not
    depend on the local directory name (worktrees and clones vary it).
    """
    origin = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if origin.returncode == 0 and origin.stdout.strip():
        name = origin.stdout.strip().rstrip("/").rsplit("/", 1)[-1]
        name = name.removesuffix(".git")
        if name:
            return name
    root_commit = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if root_commit.returncode == 0 and root_commit.stdout.strip():
        return sorted(root_commit.stdout.split())[0][:12]
    return repo.resolve().name


def git_hash_object(path: Path) -> str:
    proc = subprocess.run(
        ["git", "hash-object", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ExportError(f"git hash-object failed for {path}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def load_workflow(repo: Path) -> str:
    workflow_path = repo / WORKFLOW_REL
    if not workflow_path.is_file():
        raise ExportError(f"no {WORKFLOW_REL} found under {repo}")
    text = workflow_path.read_text(encoding="utf-8")
    first_line = text.splitlines()[0] if text else ""
    if first_line.strip() != WORKFLOW_HEADER:
        raise ExportError(f"{WORKFLOW_REL} line 1 must be exactly '{WORKFLOW_HEADER}'")
    return text


def render_gates(workflow_text: str) -> list[dict[str, Any]]:
    block = extract_block(workflow_text, "gates")
    if block is None:
        return []
    parsed = parse_nodes(tokenize(block, "beislid:gates"), "beislid:gates")
    if parsed is None:
        return []
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ExportError("beislid:gates must be a list of gate maps")
    gates: list[dict[str, Any]] = []
    for item in parsed:
        name = item.get("name")
        command = item.get("command")
        if not isinstance(name, str) or not name.strip():
            raise ExportError(f"gate is missing a non-empty name: {item!r}")
        if not isinstance(command, str) or not command.strip():
            raise ExportError(f"gate {name!r} is missing a non-empty command")
        gate: dict[str, Any] = {"name": name.strip(), "command": command.strip()}
        timeout_seconds = item.get("timeout_seconds")
        if timeout_seconds is not None:
            if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
                raise ExportError(f"gate {name!r} timeout_seconds must be a positive integer")
            gate["timeout_ms"] = timeout_seconds * 1000
        action_classes = item.get("action_classes")
        if action_classes is not None:
            if not isinstance(action_classes, list) or not all(
                isinstance(cls, str) and cls.strip() for cls in action_classes
            ):
                raise ExportError(f"gate {name!r} action_classes must be a list of non-empty strings")
            gate["action_classes"] = action_classes
        for field in GATE_PASSTHROUGH:
            value = item.get(field)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ExportError(f"gate {name!r} {field} must be a non-empty string")
                gate[field] = value.strip()
        gates.append(gate)
    return gates


def load_policy(repo: Path, workflow_text: str) -> tuple[dict[str, Any], str]:
    """Return (policy modes payload, policy_source)."""
    policy_path = repo / POLICY_REL
    if policy_path.is_file():
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ExportError(f"{POLICY_REL} is not valid JSON: {error}") from error
        if not isinstance(policy, dict):
            raise ExportError(f"{POLICY_REL} must contain a JSON object")
        normalize_policy(policy)
        return policy, "action-policy.json"
    block = extract_block(workflow_text, "action_policy")
    if block is not None:
        parsed = parse_nodes(tokenize(block, "beislid:action_policy"), "beislid:action_policy")
        if not isinstance(parsed, dict):
            raise ExportError("beislid:action_policy must be a map")
        normalize_policy(parsed)
        return parsed, "inline-block"
    return {}, "none"


def render_artifact(repo: Path) -> tuple[dict[str, Any], str]:
    workflow_text = load_workflow(repo)
    gates = render_gates(workflow_text)
    policy, policy_source = load_policy(repo, workflow_text)

    source_hashes: dict[str, dict[str, str]] = {
        "workflow": {"path": WORKFLOW_REL, "hash": git_hash_object(repo / WORKFLOW_REL)},
    }
    if policy_source == "action-policy.json":
        source_hashes["action_policy"] = {
            "path": POLICY_REL,
            "hash": git_hash_object(repo / POLICY_REL),
        }

    if policy:
        # Rondo's validator requires a top-level fixture `decision`; "ask" is
        # the conservative blanket answer. The full policy rides alongside —
        # real per-action evaluation flows through the evaluator + policy_file.
        action_policy: dict[str, Any] = {"decision": "ask", "policy_file": POLICY_REL}
        action_policy.update(policy)
    else:
        action_policy = {}

    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "id": f"beislid:{repo_id(repo)}",
        "status": "approved",
        "gates": gates,
        "action_policy": action_policy,
        "metadata": {
            "generator": "beislid process export",
            "workflow_format": "v1",
            "policy_source": policy_source,
            "source_hashes": source_hashes,
        },
    }
    return artifact, policy_source


def artifact_bytes(artifact: dict[str, Any]) -> str:
    return json.dumps(artifact, indent=2, sort_keys=True) + "\n"


def cmd_export(repo: Path) -> int:
    artifact, policy_source = render_artifact(repo)
    artifact_path = repo / ARTIFACT_REL
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(artifact_bytes(artifact), encoding="utf-8")
    print(f"wrote {ARTIFACT_REL} ({len(artifact['gates'])} gates, policy source: {policy_source})")
    if policy_source == "inline-block":
        print(
            f"note: policy was rendered from the inline beislid:action_policy block; "
            f"the evaluator reads {POLICY_REL}. Materialize it so runtime and artifact agree:\n"
            f"  beislid action-policy validate  # then write the modes to {POLICY_REL}"
        )
    elif policy_source == "none":
        print(
            "warning: no action policy found (neither "
            f"{POLICY_REL} nor an inline beislid:action_policy block); "
            "artifact carries an empty action_policy"
        )
    print("commit the artifact to approve it")
    return 0


def cmd_check(repo: Path) -> int:
    artifact_path = repo / ARTIFACT_REL
    workflow_path = repo / WORKFLOW_REL
    if not artifact_path.is_file():
        if workflow_path.is_file():
            print(
                f"STALE: {ARTIFACT_REL} is missing but {WORKFLOW_REL} exists.\n"
                "remediation: run `beislid process export` and commit the result",
                file=sys.stderr,
            )
            return 1
        print(f"ok: no {WORKFLOW_REL}; nothing to check")
        return 0

    try:
        committed = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(
            f"STALE: {ARTIFACT_REL} is not valid JSON: {error}\n"
            "remediation: run `beislid process export` and commit the result",
            file=sys.stderr,
        )
        return 1

    expected, _ = render_artifact(repo)

    stale_sources: list[str] = []
    committed_hashes = (
        committed.get("metadata", {}).get("source_hashes", {})
        if isinstance(committed.get("metadata"), dict)
        else {}
    )
    expected_hashes = expected["metadata"]["source_hashes"]
    for entry_name, entry in expected_hashes.items():
        committed_entry = committed_hashes.get(entry_name) if isinstance(committed_hashes, dict) else None
        committed_hash = committed_entry.get("hash") if isinstance(committed_entry, dict) else None
        if committed_hash != entry["hash"]:
            stale_sources.append(entry["path"])

    if stale_sources:
        print(
            f"STALE: {ARTIFACT_REL} no longer matches its sources: {', '.join(stale_sources)}\n"
            "remediation: run `beislid process export` and commit the result",
            file=sys.stderr,
        )
        return 1

    if artifact_bytes(committed if isinstance(committed, dict) else {}) != artifact_bytes(expected):
        print(
            f"STALE: {ARTIFACT_REL} does not match a fresh render of its sources "
            "(hand-edited or produced by an older exporter).\n"
            "remediation: run `beislid process export` and commit the result",
            file=sys.stderr,
        )
        return 1

    print(f"ok: {ARTIFACT_REL} is fresh ({len(expected['gates'])} gates)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Beislið process config into a ProcessProvider artifact")
    subparsers = parser.add_subparsers(dest="subcommand")
    for name, help_text in (
        ("export", f"render {WORKFLOW_REL} gates + action policy into {ARTIFACT_REL}"),
        ("check", "fail when the committed artifact is stale against its sources"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--repo", default=".", help="repo root (default: current directory)")

    args = parser.parse_args(argv)
    if args.subcommand not in ("export", "check"):
        parser.print_help(sys.stderr)
        return 2
    repo = Path(args.repo).resolve()
    if args.subcommand == "export":
        return cmd_export(repo)
    return cmd_check(repo)


if __name__ == "__main__":
    raise SystemExit(main())
