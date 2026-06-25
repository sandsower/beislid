#!/usr/bin/env python3
"""Normalize Beislið typed visual feedback without depending on Lavish.

The helper intentionally accepts only the small portable payload shape documented
in `.beislid/visual-surface-protocol.md`. Unknown or malformed input returns a
`manual_review` event instead of raising or silently approving.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from typing import Any

SCHEMA = "BEISLID_VISUAL_FEEDBACK_V1"
DEFAULT_EXPECTED_WORKFLOW = "spec"
DEFAULT_EXPECTED_ACTION = "approve_or_revise_spec"

# Canonical v1 gate vocabulary. Add workflows here as they get protocol support;
# unknown workflow/action pairs are manual-review events, not approvals.
KNOWN_ACTIONS: dict[str, set[str]] = {
    "spec": {"approve_or_revise_spec"},
    "blueprint": {"approve_revise_or_choose_blueprint"},
    "poke_holes": {"resolve_revise_or_choose_poke_holes"},
}

# Backward-compatible aliases for Phase 1 convention-level payloads and common
# review vocabulary. Aliases normalize before action/decision validation.
ACTION_ALIASES: dict[tuple[str, str], str] = {
    ("spec", "review_spec"): "approve_or_revise_spec",
    ("blueprint", "review_blueprint"): "approve_revise_or_choose_blueprint",
    ("blueprint", "approve_or_revise_blueprint"): "approve_revise_or_choose_blueprint",
    ("blueprint", "choose_blueprint_option"): "approve_revise_or_choose_blueprint",
    ("poke_holes", "review_poke_holes"): "resolve_revise_or_choose_poke_holes",
    ("poke_holes", "stress_test_plan"): "resolve_revise_or_choose_poke_holes",
    ("poke_holes", "choose_poke_holes_branch"): "resolve_revise_or_choose_poke_holes",
}

DECISION_ALIASES: dict[str, str] = {
    "approve": "approve",
    "approved": "approve",
    "revise": "revise",
    "revision": "revise",
    "request_changes": "revise",
    "changes_requested": "revise",
    "request_revision": "revise",
    "needs_revision": "revise",
    "choose": "choose",
    "choice": "choose",
    "select": "choose",
    "selected": "choose",
    "resolved": "resolved",
    "resolve": "resolved",
    "complete": "resolved",
    "done": "resolved",
}

ALLOWED_DECISIONS_BY_ACTION: dict[tuple[str, str], set[str]] = {
    ("spec", "approve_or_revise_spec"): {"approve", "revise"},
    ("blueprint", "approve_revise_or_choose_blueprint"): {"approve", "revise", "choose"},
    ("poke_holes", "resolve_revise_or_choose_poke_holes"): {"resolved", "revise", "choose"},
}

_REQUIRED_FIELDS = ("schema", "workflow", "action", "decision")
_LIST_FIELDS = {"must_change", "nice_to_have"}
_SCALAR_CLEAN = re.compile(r"\s+#.*$")
_FENCE = re.compile(r"^[ \t]*```(?:yaml|yml|json)?\s*\n(.*?)\n^[ \t]*```", re.DOTALL | re.IGNORECASE | re.MULTILINE)
_MALFORMED_TYPED_PAYLOAD = {"__beislid_parse_error__": "malformed_typed_payload"}
_DUPLICATE_JSON_KEY_PAYLOAD = {"__beislid_parse_error__": "duplicate_json_key"}


def normalize_visual_feedback(
    text: str,
    *,
    expected_workflow: str = DEFAULT_EXPECTED_WORKFLOW,
    expected_action: str = DEFAULT_EXPECTED_ACTION,
) -> dict[str, Any]:
    """Return a normalized accepted/manual_review event for visual feedback.

    `text` may be a JSON object, a fenced JSON/YAML block, or a small flat YAML
    mapping. The return value is safe to copy into canonical Markdown/chat state.
    """

    raw = text or ""
    expected_workflow = _normalize_token(expected_workflow)
    expected_action = _normalize_token(expected_action)
    legacy_schema_omitted = False
    schema_count = _schema_field_count(raw)
    if schema_count > 1:
        return _manual("ambiguous_typed_feedback", raw, expected_workflow, expected_action)
    if schema_count == 0:
        parsed, parse_error = _parse_legacy_payload(raw)
        if parse_error:
            return _manual(parse_error, raw, expected_workflow, expected_action)
        if parsed is None:
            return _manual("missing_typed_feedback", raw, expected_workflow, expected_action)
        if "schema" not in parsed:
            workflow = _normalize_token(parsed.get("workflow"))
            if workflow != "spec":
                return _manual(
                    "missing_required_field",
                    raw,
                    expected_workflow,
                    expected_action,
                    payload=parsed,
                    field="schema",
                    workflow=workflow,
                    action=_normalize_token(parsed.get("action")),
                    original_action=_normalize_token(parsed.get("action")),
                    original_decision=_normalize_token(parsed.get("decision")),
                )
            parsed["schema"] = SCHEMA
            legacy_schema_omitted = True
    else:
        if _outside_fences_has_legacy_shape(raw):
            return _manual("ambiguous_typed_feedback", raw, expected_workflow, expected_action)
        parsed, parse_error = _parse_payload(raw)
    if parse_error:
        return _manual(parse_error, raw, expected_workflow, expected_action)
    if parsed is None:
        return _manual("malformed_payload", raw, expected_workflow, expected_action)

    for field in _REQUIRED_FIELDS:
        if not _text(parsed.get(field)):
            return _manual(
                "missing_required_field",
                raw,
                expected_workflow,
                expected_action,
                payload=parsed,
                field=field,
            )

    schema = _text(parsed.get("schema"))
    workflow = _normalize_token(parsed.get("workflow"))
    original_action = _normalize_token(parsed.get("action"))
    original_decision = _normalize_token(parsed.get("decision"))

    if schema != SCHEMA:
        return _manual("unknown_schema", raw, expected_workflow, expected_action, payload=parsed)

    action = ACTION_ALIASES.get((workflow, original_action), original_action)
    decision = DECISION_ALIASES.get(original_decision)

    if workflow != expected_workflow:
        return _manual(
            "workflow_mismatch",
            raw,
            expected_workflow,
            expected_action,
            payload=parsed,
            workflow=workflow,
            action=action,
            original_action=original_action,
            original_decision=original_decision,
        )

    if action != expected_action:
        reason = "unknown_action" if action not in KNOWN_ACTIONS.get(workflow, set()) else "action_mismatch"
        return _manual(
            reason,
            raw,
            expected_workflow,
            expected_action,
            payload=parsed,
            workflow=workflow,
            action=action,
            original_action=original_action,
            original_decision=original_decision,
        )

    if action not in KNOWN_ACTIONS.get(workflow, set()):
        return _manual(
            "unknown_action",
            raw,
            expected_workflow,
            expected_action,
            payload=parsed,
            workflow=workflow,
            action=action,
            original_action=original_action,
            original_decision=original_decision,
        )

    if decision not in ALLOWED_DECISIONS_BY_ACTION.get((workflow, action), set()):
        return _manual(
            "unknown_decision",
            raw,
            expected_workflow,
            expected_action,
            payload=parsed,
            workflow=workflow,
            action=action,
            original_action=original_action,
            original_decision=original_decision,
        )

    selected_option = _text(parsed.get("selected_option"))
    if decision == "choose" and not selected_option:
        return _manual(
            "missing_required_field",
            raw,
            expected_workflow,
            expected_action,
            payload=parsed,
            field="selected_option",
            workflow=workflow,
            action=action,
            original_action=original_action,
            original_decision=original_decision,
        )

    return {
        "schema": SCHEMA,
        "status": "accepted",
        "legacy_schema_omitted": legacy_schema_omitted,
        "reason": None,
        "workflow": workflow,
        "action": action,
        "original_action": original_action,
        "decision": decision,
        "original_decision": original_decision,
        "approval_note": _text(parsed.get("approval_note")),
        "revision_summary": _text(parsed.get("revision_summary")),
        "selected_option": selected_option,
        "must_change": _list(parsed.get("must_change")),
        "nice_to_have": _list(parsed.get("nice_to_have")),
        "canonical_update_required": True,
        "canonical_record_instruction": _canonical_instruction(decision),
        "raw_feedback_excerpt": _excerpt(raw),
    }


def _manual(
    reason: str,
    raw: str,
    expected_workflow: str,
    expected_action: str,
    *,
    payload: dict[str, Any] | None = None,
    field: str | None = None,
    workflow: str | None = None,
    action: str | None = None,
    original_action: str | None = None,
    original_decision: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "manual_review",
        "reason": reason,
        "field": field,
        "workflow": workflow or _normalize_token((payload or {}).get("workflow")) or None,
        "action": action or _normalize_token((payload or {}).get("action")) or None,
        "original_action": original_action or _normalize_token((payload or {}).get("action")) or None,
        "decision": None,
        "original_decision": original_decision or _normalize_token((payload or {}).get("decision")) or None,
        "expected_workflow": expected_workflow,
        "expected_action": expected_action,
        "canonical_update_required": True,
        "canonical_record_instruction": (
            "Record that visual feedback did not produce an accepted typed gate; "
            "continue through the normal Markdown/chat approval or revision gate."
        ),
        "raw_feedback_excerpt": _excerpt(raw),
    }


def _parse_legacy_payload(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    typed_payloads: list[dict[str, Any]] = []

    for candidate in _payload_candidates(raw):
        stripped = candidate.strip()
        if not stripped:
            continue
        try:
            parsed = _json_loads_reject_duplicates(stripped)
        except json.JSONDecodeError:
            parsed = _parse_minimal_yaml(candidate)
        if parsed in (_MALFORMED_TYPED_PAYLOAD, _DUPLICATE_JSON_KEY_PAYLOAD):
            return None, "malformed_payload"
        if isinstance(parsed, dict) and "schema" in parsed:
            if _text(parsed.get("schema")):
                return parsed, None
            return None, "malformed_payload"
        if isinstance(parsed, dict) and _is_legacy_typed_payload(parsed):
            typed_payloads.append(parsed)

    if len(typed_payloads) > 1:
        return None, "ambiguous_typed_feedback"
    if len(typed_payloads) == 1:
        return typed_payloads[0], None
    return None, None


def _parse_payload(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    candidates = _payload_candidates(raw)
    typed_payloads: list[dict[str, Any]] = []
    unknown_schema_payloads: list[dict[str, Any]] = []
    saw_malformed_schema_payload = False

    for candidate in candidates:
        stripped = candidate.strip()
        if not stripped:
            continue
        try:
            parsed = _json_loads_reject_duplicates(stripped)
        except json.JSONDecodeError:
            parsed = _parse_minimal_yaml(candidate)
        if isinstance(parsed, dict) and "schema" in parsed:
            schema = _text(parsed.get("schema"))
            if schema == SCHEMA:
                typed_payloads.append(parsed)
            elif schema:
                unknown_schema_payloads.append(parsed)
            else:
                saw_malformed_schema_payload = True
        elif isinstance(parsed, dict) and _is_legacy_typed_payload(parsed):
            typed_payloads.append(parsed)
        elif parsed in (_MALFORMED_TYPED_PAYLOAD, _DUPLICATE_JSON_KEY_PAYLOAD):
            saw_malformed_schema_payload = True

    schema_payloads = typed_payloads + unknown_schema_payloads
    if len(schema_payloads) > 1:
        return None, "ambiguous_typed_feedback"
    if len(schema_payloads) == 1 and saw_malformed_schema_payload:
        return None, "ambiguous_typed_feedback"
    if len(typed_payloads) == 1:
        return typed_payloads[0], None
    if len(unknown_schema_payloads) == 1:
        return unknown_schema_payloads[0], None
    if saw_malformed_schema_payload:
        return None, "malformed_payload"
    return None, None


def _schema_field_count(raw: str) -> int:
    yaml_fields = re.findall(rf"(?m)^[ \t]*schema[ \t]*:[ \t]*['\"]?{SCHEMA}['\"]?", raw)
    json_fields = re.findall(rf"['\"]schema['\"][ \t]*:[ \t]*['\"]{SCHEMA}['\"]", raw)
    return len(yaml_fields) + len(json_fields)


def _outside_fences_has_legacy_shape(raw: str) -> bool:
    if not _FENCE.search(raw):
        return False
    outside = _FENCE.sub("\n", raw)
    return all(
        re.search(rf"(?m)^[ \t]*{field}[ \t]*:", outside)
        for field in ("workflow", "action", "decision")
    )


def _is_legacy_typed_payload(parsed: dict[str, Any]) -> bool:
    return (
        "schema" not in parsed
        and bool(_text(parsed.get("workflow")))
        and bool(_text(parsed.get("action")))
        and bool(_text(parsed.get("decision")))
    )


def _json_loads_reject_duplicates(text: str) -> Any:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                return _DUPLICATE_JSON_KEY_PAYLOAD
            out[key] = value
        return out

    return json.loads(text, object_pairs_hook=no_duplicates)


def _payload_candidates(raw: str) -> list[str]:
    candidates: list[str] = []
    candidates.extend(match.group(1) for match in _FENCE.finditer(raw))
    stripped = textwrap.dedent(raw).strip()
    candidates.append(stripped)
    if "{" in stripped and "}" in stripped:
        json_candidate = stripped[stripped.find("{") : stripped.rfind("}") + 1]
        if json_candidate != stripped:
            candidates.append(json_candidate)
    return candidates


def _parse_minimal_yaml(text: str) -> dict[str, Any] | None:
    """Parse the tiny flat YAML subset used by visual feedback controls."""

    out: dict[str, Any] = {}
    current_list: str | None = None
    saw_mapping = False

    for raw_line in textwrap.dedent(text).splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if current_list and indent > 0 and line.startswith("-"):
            out.setdefault(current_list, []).append(_strip_scalar(line[1:].strip()))
            continue
        current_list = None

        if indent > 0:
            return _MALFORMED_TYPED_PAYLOAD if _text(out.get("schema")) == SCHEMA else None

        if ":" not in line:
            return None
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            return None
        saw_mapping = True

        if key in out:
            return _MALFORMED_TYPED_PAYLOAD if _text(out.get("schema")) == SCHEMA or key == "schema" else None

        if key in _LIST_FIELDS and value == "":
            out[key] = []
            current_list = key
        elif key in _LIST_FIELDS:
            out[key] = _parse_inline_list(value)
        else:
            out[key] = _strip_scalar(value)

    return out if saw_mapping else None


def _parse_inline_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    text = _text(value)
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_strip_scalar(part.strip()) for part in inner.split(",") if _strip_scalar(part.strip())]
    if text:
        return [text]
    return []


def _strip_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return _SCALAR_CLEAN.sub("", value).strip()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_token(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    return _parse_inline_list(value)


def _canonical_instruction(decision: str) -> str:
    if decision == "approve":
        return (
            "Copy the accepted visual approval into the canonical Markdown/chat record, "
            "including workflow, action, decision, and any approval note, before routing downstream."
        )
    if decision == "choose":
        return (
            "Copy the accepted visual choice into the canonical Markdown/chat record, "
            "including workflow, action, decision, selected_option, and rationale before applying it. "
            "A visual choice is not implementation approval by itself."
        )
    if decision == "resolved":
        return (
            "Copy the accepted visual resolution into the canonical Markdown/chat record, "
            "including workflow, action, decision, and any approval note before marking the planning check complete."
        )
    return (
        "Copy the accepted visual revision request into the canonical Markdown/chat record, "
        "apply must_change items to the canonical artifact, and run another approval gate."
    )


def _excerpt(raw: str, limit: int = 320) -> str:
    compact = " ".join((raw or "").strip().split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-workflow", default=DEFAULT_EXPECTED_WORKFLOW)
    parser.add_argument("--expected-action", default=DEFAULT_EXPECTED_ACTION)
    parser.add_argument("path", nargs="?", help="feedback payload file; stdin when omitted or '-' ")
    args = parser.parse_args(argv)

    if args.path and args.path != "-":
        with open(args.path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    else:
        raw = sys.stdin.read()

    event = normalize_visual_feedback(
        raw,
        expected_workflow=args.expected_workflow,
        expected_action=args.expected_action,
    )
    print(json.dumps(event, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
