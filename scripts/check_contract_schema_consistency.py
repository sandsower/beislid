#!/usr/bin/env python3
"""Guard the envelope contract's schema files from drifting off docs/configuration.md.

BEI-134: the envelope contract used to live twice - prose in
docs/configuration.md and hand-written Python constants in
scripts/validate_export.py - with nothing forcing them to agree. The contract
now also lives as declarative JSON Schema documents
(schemas/approved-slice-plan-export-v0.schema.json and
schemas/execution-envelope-v0.schema.json); this check keeps those schemas'
`required`/`properties` field names, and their `enum` vocabularies, in sync
with the field lists and vocabularies named in docs/configuration.md.

This is a static text/data check, not a schema validator - it does not
execute schema_check.py against any bundle.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import schema_check  # noqa: E402

BUNDLE_SCHEMA_PATH = ROOT / "schemas" / "approved-slice-plan-export-v0.schema.json"
SLICE_SCHEMA_PATH = ROOT / "schemas" / "execution-envelope-v0.schema.json"
CONFIG_DOC = ROOT / "docs" / "configuration.md"

# Field names docs/configuration.md names for bundle.json, in the "`bundle.json`
# carries the BEI-17 required fields..." sentence (~L644).
DOC_BUNDLE_FIELDS = {
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
    "supersedes",
}

# Field names docs/configuration.md names for a per-slice manifest, in the
# "Per-slice manifests use the runner-intake convention..." sentence (~L646).
DOC_SLICE_FIELDS = {
    "schema",
    "slice_id",
    "prompt",
    "boundaries",
    "dependencies",
    "proof_requirements",
    "command_proofs",
    "output_expectations",
    "parent_contract",
    "repo",
    "allowed_actions",
    "process_provider",
    "runner_extensions",
}

# Schema fields that exist for validator-supported behavior but are not named
# in docs/configuration.md's per-slice field-list sentence. `body` is a
# legacy prompt alias the validator has always accepted (test_body_alias_accepted
# in scripts/test_validate_export.sh predates this ticket) but docs/configuration.md
# never documents it - flagged in the BEI-134 report as a standing doc gap,
# not "obviously doc-lag" from this change, so it is allow-listed here rather
# than silently forcing either side to change.
SLICE_SCHEMA_UNDOCUMENTED_EXTRAS = {"body"}

# Enum vocabularies docs/configuration.md names explicitly; checked as
# substrings so a renamed/added/removed value in either place fails loudly.
# rubric_version is deliberately excluded: KNOWN_RUBRIC_VERSIONS-derived enum
# includes "afk-rubric-v0", which docs/configuration.md never mentions (only
# "afk-rubric-v1", the current default, is documented) - a pre-existing doc
# gap, not something this ticket introduces. See the BEI-134 report.
DOC_ENUM_NEEDLES = {
    "tier": ["light", "standard", "heavy", "frontier"],
    "mode": ["prefer", "require"],
    "boundary": ["planning", "implementation", "review_fix", "gate_repair"],
}


def _load_schema(path: pathlib.Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"{path.relative_to(ROOT)}: missing schema file")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON ({exc})")
        return None


def _check_field_parity(
    label: str,
    schema: dict,
    doc_fields: set[str],
    errors: list[str],
    *,
    allowed_extras: set[str] = frozenset(),
) -> None:
    declared = schema_check.declared_fields(schema)

    missing_from_schema = doc_fields - declared
    for field in sorted(missing_from_schema):
        errors.append(
            f"{label}: docs/configuration.md names field '{field}' that the schema does not "
            "declare in `required` or `properties`"
        )

    undeclared_in_docs = declared - doc_fields - allowed_extras
    for field in sorted(undeclared_in_docs):
        errors.append(
            f"{label}: schema declares field '{field}' that docs/configuration.md's field-list "
            "sentence does not name"
        )


def _check_enum_needles(label: str, schema: dict, doc_text: str, errors: list[str]) -> None:
    for keyword, values in DOC_ENUM_NEEDLES.items():
        if keyword not in json.dumps(schema):
            continue
        for value in values:
            if value not in doc_text:
                errors.append(
                    f"{label}: schema uses '{keyword}' value '{value}' not found anywhere in "
                    "docs/configuration.md"
                )


def main() -> int:
    errors: list[str] = []

    bundle_schema = _load_schema(BUNDLE_SCHEMA_PATH, errors)
    slice_schema = _load_schema(SLICE_SCHEMA_PATH, errors)

    if not CONFIG_DOC.is_file():
        errors.append("docs/configuration.md: missing")
        doc_text = ""
    else:
        doc_text = CONFIG_DOC.read_text(encoding="utf-8")

    for schema, label in ((bundle_schema, "approved-slice-plan-export-v0.schema.json"),
                          (slice_schema, "execution-envelope-v0.schema.json")):
        if schema is None:
            continue
        violations = schema_check.assert_supported(schema)
        for violation in violations:
            errors.append(f"{label}: {violation}")

    if bundle_schema is not None:
        _check_field_parity(
            "approved-slice-plan-export-v0.schema.json",
            bundle_schema,
            DOC_BUNDLE_FIELDS,
            errors,
        )
        if doc_text:
            _check_enum_needles("approved-slice-plan-export-v0.schema.json", bundle_schema, doc_text, errors)

    if slice_schema is not None:
        _check_field_parity(
            "execution-envelope-v0.schema.json",
            slice_schema,
            DOC_SLICE_FIELDS,
            errors,
            allowed_extras=SLICE_SCHEMA_UNDOCUMENTED_EXTRAS,
        )
        if doc_text:
            _check_enum_needles("execution-envelope-v0.schema.json", slice_schema, doc_text, errors)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("ok: envelope contract schemas match docs/configuration.md field lists and vocabularies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
