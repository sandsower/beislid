#!/usr/bin/env python3
"""Stdlib-only interpreter for a small declarative JSON Schema subset.

This is NOT a general JSON Schema validator. It implements exactly the
keyword subset that `schemas/*.schema.json` use, so `scripts/validate_export.py`
can declare bundle/slice *shape* in data instead of hand-written Python
conditionals, while cross-field and graph-level *semantics* (cycle detection,
parallel-group transitive closure, supersedes/version pairing, slice_id-matches
-filename, the prompt-or-body fallback, non-empty-list checks) stay in code.

Supported keywords: `type`, `required`, `properties`, `enum`, `items`,
`minimum`, `pattern`. Any other JSON Schema keyword is silently ignored -
schema authors must not rely on keywords outside this list; use
`assert_supported()` to catch that mistake.

Design notes on why this is safe to keep minimal:
- `properties` only inspects declared keys that are actually present; it
  never rejects unknown/extra keys (no `additionalProperties` support). A
  field the validator never inspected before this refactor should be
  declared with an empty sub-schema (`{}`) so it can appear in the schema's
  `properties` (for the doc/schema consistency check) without silently
  gaining new enforcement.
- `properties`/`required` are only evaluated when the instance is actually a
  dict, and `items` only when the instance is actually a list. A field whose
  value is present but of the wrong container type simply skips those
  sub-checks rather than crashing - callers that need "wrong container type
  is itself an error" must also declare `type` on that field.
- `pattern` is checked with `re.search` (unanchored), matching JSON Schema's
  own `pattern` semantics. The idiom used throughout these schemas for
  "non-empty string" is `"pattern": "\\S"` (at least one non-whitespace
  character) - equivalent to `str.strip()` being non-empty.
"""

from __future__ import annotations

import re

SUPPORTED_KEYWORDS = frozenset(
    {"type", "required", "properties", "enum", "items", "minimum", "pattern"}
)
# Non-functional metadata keywords allowed anywhere in a schema document.
_META_KEYWORDS = frozenset({"$schema", "$id", "$comment", "title", "description"})

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _typename(value: object) -> str:
    return type(value).__name__


def _loc(root_label: str, path: str) -> str:
    return f"{root_label}: {path}" if path else root_label


def _child(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _child_index(path: str, idx: int) -> str:
    return f"{path}[{idx}]"


def _check(value: object, schema: dict, path: str, root_label: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        return

    if "type" in schema:
        checker = _TYPE_CHECKS.get(schema["type"])
        if checker is not None and not checker(value):
            errors.append(
                f"{_loc(root_label, path)} must be of type '{schema['type']}', "
                f"got {_typename(value)} ({value!r})"
            )
            return  # further keyword checks on a wrong-typed node aren't meaningful

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{_loc(root_label, path)} must be one of {schema['enum']!r}, got {value!r}")

    if "pattern" in schema and isinstance(value, str):
        if re.search(schema["pattern"], value) is None:
            errors.append(
                f"{_loc(root_label, path)} must match pattern {schema['pattern']!r}, got {value!r}"
            )

    if "minimum" in schema and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema["minimum"]:
            errors.append(f"{_loc(root_label, path)} must be >= {schema['minimum']}, got {value!r}")

    if isinstance(value, dict):
        for required_field in schema.get("required", ()):
            if required_field not in value:
                errors.append(f"{_loc(root_label, _child(path, required_field))} is a required field")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, subschema in properties.items():
                if key in value:
                    _check(value[key], subschema, _child(path, key), root_label, errors)

    if isinstance(value, list) and "items" in schema:
        item_schema = schema["items"]
        for idx, item in enumerate(value):
            _check(item, item_schema, _child_index(path, idx), root_label, errors)


def validate(instance: object, schema: dict, *, root_label: str) -> list[str]:
    """Validate `instance` against `schema`; return human-readable error strings.

    Every error is prefixed with `root_label` (e.g. "bundle.json" or a slice
    manifest filename) so messages read like the hand-written validator
    errors they replace.
    """
    errors: list[str] = []
    _check(instance, schema, "", root_label, errors)
    return errors


def declared_fields(schema: dict) -> set[str]:
    """Return the union of a schema's top-level `required` and `properties` keys.

    Used by scripts/check_contract_schema_consistency.py to compare what a
    schema declares against the field lists named in docs/configuration.md.
    """
    required = set(schema.get("required", ()))
    properties = set(schema.get("properties", {}).keys())
    return required | properties


def assert_supported(schema: object, path: str = "") -> list[str]:
    """Recursively check that `schema` only uses keywords this interpreter supports.

    Returns a list of violation strings (empty if the schema is entirely
    within the supported subset). Guards against a schema silently relying on
    a JSON Schema keyword (e.g. `oneOf`, `minLength`, `additionalProperties`)
    that this interpreter would just ignore.
    """
    violations: list[str] = []
    if not isinstance(schema, dict):
        return violations

    for key in schema:
        if key in SUPPORTED_KEYWORDS or key in _META_KEYWORDS:
            continue
        violations.append(f"{path or '<root>'}: unsupported schema keyword '{key}'")

    properties = schema.get("properties")
    if isinstance(properties, dict):
        for key, subschema in properties.items():
            violations.extend(assert_supported(subschema, _child(path, key)))

    items = schema.get("items")
    if isinstance(items, dict):
        violations.extend(assert_supported(items, f"{path}[]" if path else "[]"))

    return violations
