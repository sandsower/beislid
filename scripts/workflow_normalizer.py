#!/usr/bin/env python3
"""Normalize Beislið workflow.md into a deterministic read-only JSON envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "beislid.workflow.normalizer.v1"
VERSION_STAMP = "<!-- beislid-workflow: v1 -->"
DEFAULT_WORKFLOW = Path(".beislid/workflow.md")
TARGET_KEYS = {
    "gates",
    "gate_sets",
    "lifecycle_actions",
    "review_feedback_profiles",
    "clean_eval",
    "visual_surfaces",
    "model_routing",
}
FENCE = re.compile(r"```beislid:([^\s`]+)\s*\n(.*?)\n```", re.DOTALL)
SIMPLE_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")
ALLOWED_GATE_STAGES = {"preflight", "per-edit", "pre-commit", "pre-pr", "post-pr", "continuous", "human-interrupt"}
ALLOWED_GATE_EXECUTIONS = {"computational", "inferential", "human"}
ALLOWED_VISUAL_MODES = {"off", "suggest", "prompt", "auto"}
ALLOWED_CLEAN_EVAL_MODES = {"off", "require"}
ALLOWED_MODEL_MODES = {"prefer", "require"}


@dataclass
class Diagnostic:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class WorkflowParseError(ValueError):
    pass


def normalize_workflow(workflow_path: str | Path = DEFAULT_WORKFLOW) -> dict[str, Any]:
    """Return a normalized JSON-serializable envelope for workflow.md.

    The function is read-only: it does not mutate workflow.md or write generated
    artifacts. Invalid version stamps and malformed target blocks are represented
    in the returned envelope as errors; callers decide exit status from `status`.
    """

    path = Path(workflow_path)
    warnings: list[Diagnostic] = []
    errors: list[Diagnostic] = []
    sections = _default_sections()

    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        return _envelope(path, b"", None, sections, warnings, [Diagnostic("workflow_not_found", "source.path", str(exc))])

    text = raw_bytes.decode("utf-8", errors="replace")
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if first_line != VERSION_STAMP:
        errors.append(
            Diagnostic(
                "invalid_version_stamp",
                "source.version_stamp",
                f"expected first line {VERSION_STAMP!r}",
            )
        )

    blocks = _extract_blocks(text, warnings)
    for key in sorted(TARGET_KEYS):
        if key not in blocks:
            continue
        block_path = f"sections.{key}"
        try:
            parsed = _parse_workflow_yaml(blocks[key])
        except WorkflowParseError as exc:
            errors.append(Diagnostic("malformed_block", block_path, str(exc)))
            continue
        sections[key] = _normalize_section(key, parsed, warnings, errors)

    _validate_sections(sections, warnings, errors)
    return _envelope(path, raw_bytes, first_line, sections, warnings, errors)


def _envelope(
    path: Path,
    raw_bytes: bytes,
    version_stamp: str | None,
    sections: dict[str, Any],
    warnings: list[Diagnostic],
    errors: list[Diagnostic],
) -> dict[str, Any]:
    status = "error" if errors else "warning" if warnings else "ok"
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "path": path.as_posix(),
            "workflow_hash": _git_blob_sha1(raw_bytes) if raw_bytes else None,
            "version_stamp": version_stamp,
        },
        "status": status,
        "sections": sections,
        "warnings": [warning.as_dict() for warning in warnings],
        "errors": [error.as_dict() for error in errors],
    }


def _git_blob_sha1(raw_bytes: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw_bytes)).encode("ascii") + b"\0" + raw_bytes).hexdigest()


def _default_sections() -> dict[str, Any]:
    return {
        "gates": [],
        "gate_sets": {"sets": {}, "selectors": []},
        "lifecycle_actions": {"events": {}},
        "review_feedback_profiles": [],
        "clean_eval": {"mode": "off"},
        "visual_surfaces": {"mode": "off", "workflows": {}},
        "model_routing": {"defaults": None, "overrides": []},
    }


def _extract_blocks(text: str, warnings: list[Diagnostic]) -> dict[str, str]:
    blocks: dict[str, str] = {}
    for match in FENCE.finditer(text):
        key = match.group(1).strip()
        if key not in TARGET_KEYS:
            continue
        if key in blocks:
            line = text.count("\n", 0, match.start()) + 1
            warnings.append(
                Diagnostic(
                    "duplicate_key",
                    f"sections.{key}",
                    f"duplicate beislid:{key} block at line {line}; first occurrence wins",
                )
            )
            continue
        blocks[key] = match.group(2)
    return blocks


def _normalize_section(
    key: str,
    parsed: Any,
    warnings: list[Diagnostic],
    errors: list[Diagnostic],
) -> Any:
    path = f"sections.{key}"
    if key in {"gates", "review_feedback_profiles"}:
        if parsed is None:
            return []
        if not isinstance(parsed, list):
            errors.append(Diagnostic("invalid_section_shape", path, f"{key} must be a list"))
            return []
        return parsed
    if key == "gate_sets":
        if not isinstance(parsed, dict):
            errors.append(Diagnostic("invalid_section_shape", path, "gate_sets must be a mapping"))
            return {"sets": {}, "selectors": []}
        return {"sets": parsed.get("sets") or {}, "selectors": parsed.get("selectors") or []}
    if key == "lifecycle_actions":
        if not isinstance(parsed, dict):
            errors.append(Diagnostic("invalid_section_shape", path, "lifecycle_actions must be a mapping"))
            return {"events": {}}
        return {"events": parsed.get("events") or {}}
    if key == "clean_eval":
        if not isinstance(parsed, dict):
            errors.append(Diagnostic("invalid_section_shape", path, "clean_eval must be a mapping"))
            return {"mode": "off"}
        out = dict(parsed)
        out.setdefault("mode", "off")
        return out
    if key == "visual_surfaces":
        if not isinstance(parsed, dict):
            errors.append(Diagnostic("invalid_section_shape", path, "visual_surfaces must be a mapping"))
            return {"mode": "off", "workflows": {}}
        out = dict(parsed)
        out.setdefault("mode", "suggest")
        out.setdefault("workflows", {})
        return out
    if key == "model_routing":
        if not isinstance(parsed, dict):
            errors.append(Diagnostic("invalid_section_shape", path, "model_routing must be a mapping"))
            return {"defaults": None, "overrides": []}
        out = dict(parsed)
        out.setdefault("defaults", None)
        out.setdefault("overrides", [])
        if isinstance(out.get("defaults"), dict):
            out["defaults"] = _normalize_route(out["defaults"], f"{path}.defaults", warnings)
        if isinstance(out.get("overrides"), list):
            normalized = []
            for index, route in enumerate(out["overrides"]):
                if isinstance(route, dict):
                    normalized.append(_normalize_route(route, f"{path}.overrides[{index}]", warnings))
                else:
                    normalized.append(route)
            out["overrides"] = normalized
        return out
    return parsed


def _normalize_route(route: dict[str, Any], path: str, warnings: list[Diagnostic]) -> dict[str, Any]:
    out = dict(route)
    if "model" in out and "models" not in out:
        out["models"] = [out.pop("model")]
    if "when" in out:
        warnings.append(Diagnostic("reserved_field", f"{path}.when", "model_routing.when is reserved in workflow.md v1"))
    out.setdefault("mode", "prefer")
    return out


def _validate_sections(sections: dict[str, Any], warnings: list[Diagnostic], errors: list[Diagnostic]) -> None:
    _validate_gates(sections.get("gates") or [], "sections.gates", warnings)
    gate_sets = sections.get("gate_sets") or {}
    if isinstance(gate_sets, dict):
        sets = gate_sets.get("sets") or {}
        if isinstance(sets, dict):
            for set_name, gate_set in sets.items():
                if isinstance(gate_set, dict):
                    _validate_gates(gate_set.get("gates") or [], f"sections.gate_sets.sets.{set_name}.gates", warnings)
        selectors = gate_sets.get("selectors") or []
        known_sets = set(sets.keys()) if isinstance(sets, dict) else set()
        if isinstance(selectors, list):
            for index, selector in enumerate(selectors):
                if not isinstance(selector, dict):
                    continue
                for set_name in selector.get("gate_sets") or []:
                    if set_name not in known_sets:
                        errors.append(
                            Diagnostic(
                                "unknown_gate_set",
                                f"sections.gate_sets.selectors[{index}].gate_sets",
                                f"selector references missing gate set {set_name!r}",
                            )
                        )
    clean_eval = sections.get("clean_eval") or {}
    if isinstance(clean_eval, dict) and clean_eval.get("mode") not in ALLOWED_CLEAN_EVAL_MODES:
        errors.append(Diagnostic("invalid_value", "sections.clean_eval.mode", "clean_eval.mode must be off or require"))
    visual = sections.get("visual_surfaces") or {}
    if isinstance(visual, dict):
        if "provider" in visual and visual.get("provider") != "lavish-axi":
            errors.append(Diagnostic("invalid_value", "sections.visual_surfaces.provider", "provider must be lavish-axi"))
        if visual.get("mode") not in ALLOWED_VISUAL_MODES:
            errors.append(Diagnostic("invalid_value", "sections.visual_surfaces.mode", "invalid visual_surfaces mode"))
        workflows = visual.get("workflows") or {}
        if isinstance(workflows, dict):
            for name, mode in workflows.items():
                if mode not in ALLOWED_VISUAL_MODES:
                    errors.append(
                        Diagnostic("invalid_value", f"sections.visual_surfaces.workflows.{name}", "invalid workflow visual mode")
                    )
    model = sections.get("model_routing") or {}
    if isinstance(model, dict):
        routes = []
        if isinstance(model.get("defaults"), dict):
            routes.append(("sections.model_routing.defaults", model["defaults"]))
        if isinstance(model.get("overrides"), list):
            routes.extend((f"sections.model_routing.overrides[{i}]", route) for i, route in enumerate(model["overrides"]) if isinstance(route, dict))
        for path, route in routes:
            if route.get("mode") not in ALLOWED_MODEL_MODES:
                errors.append(Diagnostic("invalid_value", f"{path}.mode", "model_routing mode must be prefer or require"))


def _validate_gates(gates: Any, path: str, warnings: list[Diagnostic]) -> None:
    if not isinstance(gates, list):
        return
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            continue
        if "stage" in gate and gate["stage"] not in ALLOWED_GATE_STAGES:
            warnings.append(Diagnostic("reserved_value", f"{path}[{index}].stage", f"unknown gate stage {gate['stage']!r}"))
        if "execution" in gate and gate["execution"] not in ALLOWED_GATE_EXECUTIONS:
            warnings.append(
                Diagnostic("reserved_value", f"{path}[{index}].execution", f"unknown gate execution {gate['execution']!r}")
            )


def _parse_workflow_yaml(text: str) -> Any:
    lines = _tokenize_yaml_lines(text)
    if not lines:
        return None
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise WorkflowParseError(f"could not parse line {index + 1}")
    return value


def _tokenize_yaml_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise WorkflowParseError(f"tabs are not supported at line {number}")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    return lines


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return None, index
    current_indent, content = lines[index]
    if current_indent < indent:
        return None, index
    if current_indent > indent:
        raise WorkflowParseError(f"unexpected indentation at line {index + 1}")
    if content.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_map(lines, index, indent)


def _parse_map(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise WorkflowParseError(f"unexpected indentation at line {index + 1}")
        if content.startswith("- "):
            break
        key, value_text = _split_key_value(content, index)
        if key in out:
            raise WorkflowParseError(f"duplicate key {key!r} at line {index + 1}")
        index += 1
        if value_text:
            out[key] = _parse_scalar(value_text)
        elif index < len(lines) and lines[index][0] > current_indent:
            child_indent = lines[index][0]
            if child_indent != current_indent + 2:
                raise WorkflowParseError(f"expected child indentation of {current_indent + 2} spaces at line {index + 1}")
            out[key], index = _parse_block(lines, index, child_indent)
        else:
            out[key] = None
    return out, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    out: list[Any] = []
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise WorkflowParseError(f"unexpected indentation at line {index + 1}")
        if not content.startswith("- "):
            break
        item_text = content[2:].strip()
        index += 1
        if not item_text:
            if index < len(lines) and lines[index][0] > current_indent:
                child_indent = lines[index][0]
                if child_indent != current_indent + 2:
                    raise WorkflowParseError(f"expected child indentation of {current_indent + 2} spaces at line {index + 1}")
                item, index = _parse_block(lines, index, child_indent)
            else:
                item = None
        elif _looks_like_inline_map_item(item_text):
            key, value_text = _split_key_value(item_text, index - 1)
            item = {key: _parse_scalar(value_text) if value_text else None}
            if not value_text and index < len(lines) and lines[index][0] > current_indent:
                child_indent = lines[index][0]
                if child_indent != current_indent + 2:
                    raise WorkflowParseError(f"expected child indentation of {current_indent + 2} spaces at line {index + 1}")
                item[key], index = _parse_block(lines, index, child_indent)
            if index < len(lines) and lines[index][0] > current_indent:
                child_indent = lines[index][0]
                if child_indent != current_indent + 2:
                    raise WorkflowParseError(f"expected child indentation of {current_indent + 2} spaces at line {index + 1}")
                continuation, index = _parse_block(lines, index, child_indent)
                if not isinstance(continuation, dict):
                    raise WorkflowParseError(f"list item continuation must be a mapping before line {index + 1}")
                overlap = set(item).intersection(continuation)
                if overlap:
                    raise WorkflowParseError(f"duplicate key {sorted(overlap)[0]!r} in list item")
                item.update(continuation)
        else:
            item = _parse_scalar(item_text)
            if index < len(lines) and lines[index][0] > current_indent:
                raise WorkflowParseError(f"scalar list item has unexpected child at line {index + 1}")
        out.append(item)
    return out, index


def _split_key_value(content: str, index: int) -> tuple[str, str]:
    if ":" not in content:
        raise WorkflowParseError(f"expected key/value mapping at line {index + 1}")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key or not SIMPLE_KEY.match(key):
        raise WorkflowParseError(f"invalid mapping key at line {index + 1}")
    return key, value.strip()


def _looks_like_inline_map_item(text: str) -> bool:
    if ":" not in text:
        return False
    key = text.split(":", 1)[0].strip()
    return bool(SIMPLE_KEY.match(key))


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in _split_inline_list(inner)]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _split_inline_list(inner: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escape = False
    for char in inner:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\" and quote == '"':
            current.append(char)
            escape = True
            continue
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char == ",":
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if quote:
        raise WorkflowParseError("unterminated quote in inline list")
    parts.append("".join(current).strip())
    return [part for part in parts if part]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize Beislið workflow.md to JSON")
    parser.add_argument("--json", action="store_true", required=True, help="emit the normalized JSON envelope")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    envelope = normalize_workflow(args.workflow)
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 1 if envelope["status"] == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
