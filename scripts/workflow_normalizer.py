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
DEFAULT_FORMAT_DOC = Path(".beislid/workflow-md-format.md")

TARGET_KEYS = {
    "agent_isolation",
    "gates",
    "gate_sets",
    "lifecycle_actions",
    "review_feedback_profiles",
    "clean_eval",
    "visual_surfaces",
    "model_routing",
}

# The registry is the union of the documented fenced keys in
# `.beislid/workflow-md-format.md` plus the normalizer-owned target keys above.
# Registered-but-not-target keys are parsed for syntax, then discarded.
NORMALIZER_OWNED_KEYS = TARGET_KEYS
DOC_FENCE_KEYS = {
    "action_policy",
    "agent_isolation",
    "babysit",
    "branch_pattern",
    "domain_expert.agent",
    "envelope",
    "explore",
    "fresh_eyes",
    "gate_sets",
    "guided_walkthrough.threshold_files",
    "knowledge_store.path",
    "lifecycle_actions",
    "model_routing",
    "pi_handoff",
    "pr_review_source",
    "pr_review_update",
    "probe_cache",
    "ready_for_review",
    "scopes",
    "split_policy",
    "ticket_source",
    "visual_surfaces",
    "workflow_signals",
}
FENCE_KEY_REGISTRY = DOC_FENCE_KEYS | NORMALIZER_OWNED_KEYS

ALLOWED_GATE_STAGES = {"preflight", "per-edit", "pre-commit", "pre-pr", "post-pr", "continuous", "human-interrupt"}
ALLOWED_GATE_EXECUTIONS = {"computational", "inferential", "human"}
ALLOWED_VISUAL_MODES = {"off", "suggest", "prompt", "auto"}
ALLOWED_CLEAN_EVAL_MODES = {"off", "require"}
ALLOWED_MODEL_MODES = {"prefer", "require"}
ALLOWED_MODEL_TIERS = {"light", "standard", "heavy", "frontier"}
ALLOWED_TIER_MODE = {"prefer", "require"}
ALLOWED_ORCHESTRATOR_PLACEMENTS = {"current", "native", "manual"}
ALLOWED_DELEGATE_PLACEMENTS = {"native", "manual", "sequential"}
ALLOWED_ORCHESTRATOR_FALLBACKS = {"manual-transition-required"}
ALLOWED_DELEGATE_FALLBACKS = {"manual", "sequential"}
RUNTIME_BINDING_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
RUNTIME_PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
EPHEMERAL_MANUAL_ROOTS = tuple(Path(value) for value in ("/tmp", "/private/tmp", "/var/tmp", "/private/var/folders"))

FENCE_OPEN_RE = re.compile(r"^```beislid:([^\s`]+)\s*$")
SIMPLE_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class Token:
    line: int
    indent: int
    content: str


@dataclass(frozen=True)
class FenceBlock:
    key: str
    start_line: int
    body_lines: list[tuple[int, str]]


class WorkflowParseError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:  # pragma: no cover - inherited behavior is trivial
        return str(self.args[0])


def normalize_workflow(workflow_path: str | Path = DEFAULT_WORKFLOW) -> dict[str, Any]:
    """Return a normalized JSON-serializable envelope for workflow.md."""

    path = Path(workflow_path)
    warnings: list[Diagnostic] = []
    errors: list[Diagnostic] = []
    sections = _default_sections()

    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        return _envelope(path, None, None, sections, warnings, [Diagnostic("workflow_not_found", "source.path", str(exc))])

    text = raw_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()
    first_line = lines[0].strip() if lines else ""
    if first_line != VERSION_STAMP:
        errors.append(
            Diagnostic(
                "invalid_version_stamp",
                "source.version_stamp",
                f"expected first line {VERSION_STAMP!r}",
            )
        )

    blocks = _extract_blocks(text, errors)
    seen_keys: set[str] = set()
    for block in blocks:
        if block.key not in FENCE_KEY_REGISTRY:
            warnings.append(
                Diagnostic(
                    "unknown_fence_key",
                    f"sections.{block.key}",
                    f"unknown beislid:{block.key} block at line {block.start_line}",
                )
            )
            continue

        if block.key in seen_keys:
            warnings.append(
                Diagnostic(
                    "duplicate_key",
                    f"sections.{block.key}",
                    f"duplicate beislid:{block.key} block at line {block.start_line}; first occurrence wins",
                )
            )
            continue
        seen_keys.add(block.key)

        try:
            parsed = _parse_workflow_yaml(block.body_lines)
        except WorkflowParseError as exc:
            errors.append(Diagnostic(exc.code, f"sections.{block.key}", str(exc)))
            continue

        if block.key in TARGET_KEYS:
            sections[block.key] = _normalize_section(block.key, parsed, warnings, errors)

    _validate_sections(sections, warnings, errors)
    return _envelope(path, raw_bytes, first_line, sections, warnings, errors)


def _envelope(
    path: Path,
    raw_bytes: bytes | None,
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
            "workflow_hash": _git_blob_sha1(raw_bytes) if raw_bytes is not None else None,
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


def _extract_blocks(text: str, errors: list[Diagnostic]) -> list[FenceBlock]:
    blocks: list[FenceBlock] = []
    current: FenceBlock | None = None

    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.lstrip()
        if current is None:
            if not stripped.startswith("```beislid:"):
                continue
            match = FENCE_OPEN_RE.match(stripped)
            if not match:
                continue
            current = FenceBlock(key=match.group(1).strip(), start_line=line_no, body_lines=[])
            continue

        if stripped.startswith("```") and stripped == "```":
            blocks.append(current)
            current = None
            continue

        current.body_lines.append((line_no, raw))

    if current is not None:
        errors.append(
            Diagnostic(
                "malformed_block",
                f"sections.{current.key}",
                f"unterminated beislid:{current.key} block starting at line {current.start_line}",
            )
        )

    return blocks


def _normalize_section(
    key: str,
    parsed: Any,
    warnings: list[Diagnostic],
    errors: list[Diagnostic],
) -> Any:
    path = f"sections.{key}"
    if key == "agent_isolation":
        defaults = {
            "orchestrator": "current",
            "delegate": "sequential",
            "manual_root": "repo-sibling",
            "fallback": {
                "orchestrator": "manual-transition-required",
                "delegate": "sequential",
            },
        }
        if not isinstance(parsed, dict):
            errors.append(Diagnostic("invalid_section_shape", path, "agent_isolation must be a mapping"))
            return defaults
        out = dict(parsed)
        out.setdefault("orchestrator", defaults["orchestrator"])
        out.setdefault("delegate", defaults["delegate"])
        out.setdefault("manual_root", defaults["manual_root"])
        fallback = out.setdefault("fallback", dict(defaults["fallback"]))
        if not isinstance(fallback, dict):
            errors.append(Diagnostic("invalid_section_shape", f"{path}.fallback", "fallback must be a mapping"))
            out["fallback"] = dict(defaults["fallback"])
        else:
            fallback = dict(fallback)
            fallback.setdefault("orchestrator", defaults["fallback"]["orchestrator"])
            fallback.setdefault("delegate", defaults["fallback"]["delegate"])
            out["fallback"] = fallback
        preparation = out.get("preparation")
        if isinstance(preparation, dict):
            preparation = dict(preparation)
            preparation.setdefault("readiness", [])
            out["preparation"] = preparation
        return out

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
        out = dict(parsed)
        out.setdefault("sets", {})
        out.setdefault("selectors", [])
        return out

    if key == "lifecycle_actions":
        if not isinstance(parsed, dict):
            errors.append(Diagnostic("invalid_section_shape", path, "lifecycle_actions must be a mapping"))
            return {"events": {}}
        out = dict(parsed)
        out.setdefault("events", {})
        return out

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
        out.setdefault("tier_mode", "prefer")
        if isinstance(out.get("defaults"), dict):
            out["defaults"] = _normalize_route(out["defaults"], f"{path}.defaults", warnings, errors)
        if isinstance(out.get("overrides"), list):
            normalized: list[Any] = []
            for index, route in enumerate(out["overrides"]):
                if isinstance(route, dict):
                    normalized.append(_normalize_route(route, f"{path}.overrides[{index}]", warnings, errors))
                else:
                    normalized.append(route)
            out["overrides"] = normalized
        tiers = out.get("tiers")
        if tiers is not None:
            if not isinstance(tiers, dict):
                errors.append(Diagnostic("invalid_section_shape", f"{path}.tiers", "tiers must be a mapping"))
            else:
                for tier_name in tiers:
                    if tier_name not in ALLOWED_MODEL_TIERS:
                        errors.append(
                            Diagnostic(
                                "invalid_value",
                                f"{path}.tiers.{tier_name}",
                                "model_routing.tiers keys must be light, standard, heavy, or frontier",
                            )
                        )
        if out.get("tier_mode") not in ALLOWED_TIER_MODE:
            errors.append(Diagnostic("invalid_value", f"{path}.tier_mode", "model_routing.tier_mode must be prefer or require"))
        return out

    return parsed


def _normalize_route(route: dict[str, Any], path: str, warnings: list[Diagnostic], errors: list[Diagnostic]) -> dict[str, Any]:
    out = dict(route)
    if "model" in out and "models" in out:
        errors.append(Diagnostic("invalid_value", path, "model and models are mutually exclusive on a route"))
    elif "model" in out and "models" not in out:
        out["models"] = [out.pop("model")]
    if "when" in out:
        warnings.append(Diagnostic("reserved_field", f"{path}.when", "model_routing.when is reserved in workflow.md v1"))
    out.setdefault("mode", "prefer")
    return out


def _validate_sections(sections: dict[str, Any], warnings: list[Diagnostic], errors: list[Diagnostic]) -> None:
    isolation = sections.get("agent_isolation")
    if isinstance(isolation, dict):
        if isolation.get("orchestrator") not in ALLOWED_ORCHESTRATOR_PLACEMENTS:
            errors.append(
                Diagnostic(
                    "invalid_value",
                    "sections.agent_isolation.orchestrator",
                    "orchestrator must be current, native, or manual",
                )
            )
        if isolation.get("delegate") not in ALLOWED_DELEGATE_PLACEMENTS:
            errors.append(
                Diagnostic(
                    "invalid_value",
                    "sections.agent_isolation.delegate",
                    "delegate must be native, manual, or sequential",
                )
            )
        manual_root = isolation.get("manual_root")
        manual_root_valid = isinstance(manual_root, str) and (
            manual_root == "repo-sibling" or Path(manual_root).expanduser().is_absolute()
        )
        if not manual_root_valid:
            errors.append(
                Diagnostic(
                    "invalid_value",
                    "sections.agent_isolation.manual_root",
                    "manual_root must be repo-sibling or an absolute path",
                )
            )
        elif manual_root != "repo-sibling":
            resolved_root = Path(manual_root).expanduser().resolve()
            if any(resolved_root == root or root in resolved_root.parents for root in EPHEMERAL_MANUAL_ROOTS):
                errors.append(
                    Diagnostic(
                        "invalid_value",
                        "sections.agent_isolation.manual_root",
                        "manual_root must be durable and cannot be under a temporary system directory",
                    )
                )
        fallback = isolation.get("fallback")
        if isinstance(fallback, dict):
            if fallback.get("orchestrator") not in ALLOWED_ORCHESTRATOR_FALLBACKS:
                errors.append(
                    Diagnostic(
                        "invalid_value",
                        "sections.agent_isolation.fallback.orchestrator",
                        "orchestrator fallback must be manual-transition-required",
                    )
                )
            if fallback.get("delegate") not in ALLOWED_DELEGATE_FALLBACKS:
                errors.append(
                    Diagnostic(
                        "invalid_value",
                        "sections.agent_isolation.fallback.delegate",
                        "delegate fallback must be manual or sequential",
                    )
                )
        preparation = isolation.get("preparation")
        if preparation is not None:
            if not isinstance(preparation, dict):
                errors.append(
                    Diagnostic(
                        "invalid_section_shape",
                        "sections.agent_isolation.preparation",
                        "preparation must be a mapping",
                    )
                )
            else:
                command = preparation.get("command")
                if "command" not in preparation:
                    errors.append(
                        Diagnostic(
                            "missing_required_field",
                            "sections.agent_isolation.preparation.command",
                            "preparation command is required",
                        )
                    )
                elif not isinstance(command, str) or not command.strip():
                    errors.append(
                        Diagnostic(
                            "invalid_value",
                            "sections.agent_isolation.preparation.command",
                            "preparation command must be a non-empty string",
                        )
                    )
                readiness = preparation.get("readiness", [])
                if not isinstance(readiness, list) or any(
                    not isinstance(item, str) or not item.strip() for item in readiness
                ):
                    errors.append(
                        Diagnostic(
                            "invalid_value",
                            "sections.agent_isolation.preparation.readiness",
                            "preparation readiness must be a list of non-empty command strings",
                        )
                    )
        runtime_profiles = isolation.get("runtime_profiles")
        if runtime_profiles is not None:
            if not isinstance(runtime_profiles, dict):
                errors.append(
                    Diagnostic(
                        "invalid_section_shape",
                        "sections.agent_isolation.runtime_profiles",
                        "runtime_profiles must be a mapping",
                    )
                )
            else:
                for profile_name, profile in runtime_profiles.items():
                    profile_path = f"sections.agent_isolation.runtime_profiles.{profile_name}"
                    if not isinstance(profile_name, str) or not RUNTIME_PROFILE_NAME.fullmatch(profile_name):
                        errors.append(
                            Diagnostic(
                                "invalid_value",
                                profile_path,
                                "runtime profile names must be lowercase path-safe segments",
                            )
                        )
                    if not isinstance(profile, dict):
                        errors.append(
                            Diagnostic("invalid_section_shape", profile_path, "runtime profile must be a mapping")
                        )
                        continue
                    bindings = profile.get("required_bindings")
                    bindings_valid = (
                        isinstance(bindings, list)
                        and bool(bindings)
                        and len(bindings) == len(set(str(item) for item in bindings))
                        and all(isinstance(item, str) and RUNTIME_BINDING_NAME.fullmatch(item) for item in bindings)
                    )
                    if not bindings_valid:
                        errors.append(
                            Diagnostic(
                                "invalid_value",
                                f"{profile_path}.required_bindings",
                                "required_bindings must be a non-empty unique list of uppercase environment names",
                            )
                        )
                    provider = profile.get("provider")
                    if not isinstance(provider, dict):
                        errors.append(
                            Diagnostic(
                                "invalid_section_shape",
                                f"{profile_path}.provider",
                                "runtime profile provider must be a mapping",
                            )
                        )
                        continue
                    for action in ("allocate", "verify", "release", "reconcile"):
                        command = provider.get(action)
                        command_path = f"{profile_path}.provider.{action}"
                        if action not in provider:
                            errors.append(
                                Diagnostic(
                                    "missing_required_field",
                                    command_path,
                                    f"runtime provider {action} command is required",
                                )
                            )
                        elif not isinstance(command, str) or not command.strip():
                            errors.append(
                                Diagnostic(
                                    "invalid_value",
                                    command_path,
                                    f"runtime provider {action} must be a non-empty command string",
                                )
                            )

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
        routes: list[tuple[str, dict[str, Any]]] = []
        if isinstance(model.get("defaults"), dict):
            routes.append(("sections.model_routing.defaults", model["defaults"]))
        if isinstance(model.get("overrides"), list):
            routes.extend(
                (f"sections.model_routing.overrides[{i}]", route)
                for i, route in enumerate(model["overrides"])
                if isinstance(route, dict)
            )
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


def _parse_workflow_yaml(body_lines: list[tuple[int, str]]) -> Any:
    tokens = _tokenize_yaml_lines(body_lines)
    if not tokens:
        return None
    value, index = _parse_block(tokens, 0, tokens[0].indent, "sections")
    if index != len(tokens):
        raise WorkflowParseError("malformed_block", f"could not parse line {tokens[index].line}")
    return value


def _tokenize_yaml_lines(body_lines: list[tuple[int, str]]) -> list[Token]:
    tokens: list[Token] = []
    for line_no, raw in body_lines:
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise WorkflowParseError("malformed_block", f"tabs are not supported at line {line_no}")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        tokens.append(Token(line=line_no, indent=indent, content=stripped))
    return tokens


def _parse_block(tokens: list[Token], index: int, indent: int, path: str) -> tuple[Any, int]:
    if index >= len(tokens):
        return None, index
    current = tokens[index]
    if current.indent < indent:
        return None, index
    if current.indent > indent:
        raise WorkflowParseError("malformed_block", f"unexpected indentation at line {current.line}")
    if current.content.startswith("- "):
        return _parse_list(tokens, index, indent, path)
    if ":" in current.content:
        return _parse_map(tokens, index, indent, path)
    if index + 1 < len(tokens) and tokens[index + 1].indent > current.indent:
        raise WorkflowParseError("malformed_block", f"scalar block has unexpected child at line {tokens[index + 1].line}")
    return _parse_scalar(current.content, current.line, path), index + 1


def _parse_map(tokens: list[Token], index: int, indent: int, path: str) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    while index < len(tokens):
        current = tokens[index]
        if current.indent < indent:
            break
        if current.indent > indent:
            raise WorkflowParseError("malformed_block", f"unexpected indentation at line {current.line}")
        if current.content.startswith("- "):
            break
        key, value_text = _split_key_value(current.content, current.line)
        if key in out:
            raise WorkflowParseError("malformed_block", f"duplicate key {key!r} at line {current.line}")
        index += 1
        if value_text:
            out[key] = _parse_scalar(value_text, current.line, f"{path}.{key}")
        elif index < len(tokens) and tokens[index].indent > current.indent:
            child_indent = tokens[index].indent
            if child_indent != current.indent + 2:
                raise WorkflowParseError("malformed_block",
                    f"expected child indentation of {current.indent + 2} spaces at line {tokens[index].line}"
                )
            out[key], index = _parse_block(tokens, index, child_indent, f"{path}.{key}")
        else:
            out[key] = None
    return out, index


def _parse_list(tokens: list[Token], index: int, indent: int, path: str) -> tuple[list[Any], int]:
    out: list[Any] = []
    while index < len(tokens):
        current = tokens[index]
        if current.indent < indent:
            break
        if current.indent > indent:
            raise WorkflowParseError("malformed_block", f"unexpected indentation at line {current.line}")
        if not current.content.startswith("- "):
            break
        item_text = current.content[2:].strip()
        item_path = f"{path}[{len(out)}]"
        index += 1
        if not item_text:
            if index < len(tokens) and tokens[index].indent > current.indent:
                child_indent = tokens[index].indent
                if child_indent != current.indent + 2:
                    raise WorkflowParseError("malformed_block",
                        f"expected child indentation of {current.indent + 2} spaces at line {tokens[index].line}"
                    )
                item, index = _parse_block(tokens, index, child_indent, item_path)
            else:
                item = None
        elif item_text.startswith("{"):
            raise WorkflowParseError("flow_map_unsupported", f"flow_map_unsupported at line {current.line}; use block style")
        elif _looks_like_inline_map_item(item_text):
            key, value_text = _split_key_value(item_text, current.line)
            item = {key: _parse_scalar(value_text, current.line, f"{item_path}.{key}") if value_text else None}
            if not value_text and index < len(tokens) and tokens[index].indent > current.indent:
                child_indent = tokens[index].indent
                if child_indent != current.indent + 2:
                    raise WorkflowParseError("malformed_block",
                        f"expected child indentation of {current.indent + 2} spaces at line {tokens[index].line}"
                    )
                item[key], index = _parse_block(tokens, index, child_indent, f"{item_path}.{key}")
            if index < len(tokens) and tokens[index].indent > current.indent:
                child_indent = tokens[index].indent
                if child_indent != current.indent + 2:
                    raise WorkflowParseError("malformed_block",
                        f"expected child indentation of {current.indent + 2} spaces at line {tokens[index].line}"
                    )
                continuation, index = _parse_block(tokens, index, child_indent, item_path)
                if not isinstance(continuation, dict):
                    raise WorkflowParseError("malformed_block", f"list item continuation must be a mapping before line {tokens[index - 1].line}")
                overlap = set(item).intersection(continuation)
                if overlap:
                    raise WorkflowParseError("malformed_block", f"duplicate key {sorted(overlap)[0]!r} in list item")
                item.update(continuation)
        else:
            item = _parse_scalar(item_text, current.line, item_path)
            if index < len(tokens) and tokens[index].indent > current.indent:
                raise WorkflowParseError("malformed_block", f"scalar list item has unexpected child at line {tokens[index].line}")
        out.append(item)
    return out, index


def _split_key_value(content: str, line_no: int) -> tuple[str, str]:
    if ":" not in content:
        raise WorkflowParseError("malformed_block", f"expected key/value mapping at line {line_no}")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key or not SIMPLE_KEY.match(key):
        raise WorkflowParseError("malformed_block", f"invalid mapping key at line {line_no}")
    return key, value.strip()


def _looks_like_inline_map_item(text: str) -> bool:
    if ":" not in text:
        return False
    key = text.split(":", 1)[0].strip()
    return bool(SIMPLE_KEY.match(key))


def _parse_scalar(value: str, line_no: int, path: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("["):
        return _parse_inline_list(value, line_no, path)
    value, had_comment = _strip_comment(value, line_no)
    if not value:
        return None if had_comment else ""
    if value[0] in {"'", '"'}:
        return _parse_quoted_scalar(value, line_no, path)
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _strip_comment(text: str, line_no: int) -> tuple[str, bool]:
    idx = _find_comment_start(text)
    if idx is None:
        return text.rstrip(), False
    return text[:idx].rstrip(), True


def _find_comment_start(text: str) -> int | None:
    quote: str | None = None
    escape = False
    index = 0
    while index < len(text):
        ch = text[index]
        if quote == '"':
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                quote = None
            index += 1
            continue
        if quote == "'":
            if ch == "'" and index + 1 < len(text) and text[index + 1] == "'":
                index += 2
                continue
            if ch == "'":
                quote = None
                index += 1
                continue
            index += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            index += 1
            continue
        if ch == "#" and (index == 0 or text[index - 1].isspace()):
            return index
        index += 1
    return None


def _parse_quoted_scalar(text: str, line_no: int, path: str) -> str:
    quote = text[0]
    if len(text) < 2 or text[-1] != quote:
        raise WorkflowParseError("unterminated_quote", f"unterminated_quote at line {line_no}")
    inner = text[1:-1]
    if quote == "'":
        out: list[str] = []
        index = 0
        while index < len(inner):
            ch = inner[index]
            if ch == "'":
                if index + 1 < len(inner) and inner[index + 1] == "'":
                    out.append("'")
                    index += 2
                    continue
                raise WorkflowParseError("unterminated_quote", f"unterminated_quote at line {line_no}")
            out.append(ch)
            index += 1
        return "".join(out)

    out = []
    index = 0
    while index < len(inner):
        ch = inner[index]
        if ch == '"':
            raise WorkflowParseError("unterminated_quote", f"unterminated_quote at line {line_no}")
        if ch != "\\":
            out.append(ch)
            index += 1
            continue
        if index + 1 >= len(inner):
            raise WorkflowParseError("unterminated_quote", f"unterminated_quote at line {line_no}")
        esc = inner[index + 1]
        if esc == "n":
            out.append("\n")
        elif esc == "t":
            out.append("\t")
        elif esc == "\\":
            out.append("\\")
        elif esc == '"':
            out.append('"')
        else:
            raise WorkflowParseError("unknown_escape", f"unknown_escape at line {line_no}")
        index += 2
    return "".join(out)


def _parse_inline_list(text: str, line_no: int, path: str) -> list[Any]:
    if not text.startswith("["):
        raise WorkflowParseError("nested_inline_list", f"nested_inline_list at line {line_no}; use block style")
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escape = False
    saw_comment = False
    index = 1
    while index < len(text):
        ch = text[index]
        if quote == '"':
            current.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                quote = None
            index += 1
            continue
        if quote == "'":
            current.append(ch)
            if ch == "'" and index + 1 < len(text) and text[index + 1] == "'":
                current.append("'")
                index += 2
                continue
            if ch == "'":
                quote = None
            index += 1
            continue
        if ch == "#" and (index == 0 or text[index - 1].isspace()):
            saw_comment = True
            break
        if ch in {"'", '"'}:
            quote = ch
            current.append(ch)
            index += 1
            continue
        if ch == "[":
            raise WorkflowParseError("nested_inline_list", f"nested_inline_list at line {line_no}; use block style")
        if ch == ",":
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            index += 1
            continue
        if ch == "]":
            part = "".join(current).strip()
            if part:
                parts.append(part)
            trailing = text[index + 1 :].strip()
            if trailing and not trailing.startswith("#"):
                raise WorkflowParseError("malformed_block", f"unexpected trailing content at line {line_no}")
            return [_parse_scalar(part, line_no, f"{path}[{item_index}]") for item_index, part in enumerate(parts)]
        current.append(ch)
        index += 1
    if quote is not None:
        raise WorkflowParseError("unterminated_quote", f"unterminated_quote at line {line_no}")
    if saw_comment:
        part = "".join(current).strip()
        if part:
            parts.append(part)
        return [_parse_scalar(part, line_no, f"{path}[{item_index}]") for item_index, part in enumerate(parts)]
    raise WorkflowParseError("malformed_block", f"unterminated inline list at line {line_no}")


# The registry is derived from the canonical format doc when available, but the
# normalizer-owned keys stay recognized even if the doc is absent in a packaged
# install.

def _registry_keys() -> set[str]:
    keys = set(FENCE_KEY_REGISTRY)
    try:
        doc = DEFAULT_FORMAT_DOC.read_text(encoding="utf-8")
    except OSError:
        return keys
    for match in re.finditer(r"```beislid:([^\s`]+)", doc):
        key = match.group(1).strip()
        if key and key != "<key>":
            keys.add(key)
    return keys


FENCE_KEY_REGISTRY = _registry_keys()


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
