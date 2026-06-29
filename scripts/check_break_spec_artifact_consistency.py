#!/usr/bin/env python3
"""Guard break-spec artifact lifecycle docs from drifting."""

from __future__ import annotations

import pathlib
import sys

REQUIRED_REFERENCES = {
    ".beislid/workflow-md-format.md": [
        "break_spec_approved",
        "plans/{feature}-structure.md",
        "Existing targets always prompt",
    ],
    "docs/configuration.md": [
        "break_spec_approved",
        "plans/{feature}-structure.md",
        "no overwrite without approval",
    ],
    "skills/break-spec/SKILL.md": [
        "break_spec_approved",
        "plans/{feature}-structure.md",
        "Existing targets always prompt",
    ],
    "skills/setup/SKILL.md": [
        "break_spec_approved",
        "plans/{feature}-structure.md",
        "Use `structure` for `break_spec_approved`",
    ],
    "skills/doctor/SKILL.md": [
        "break_spec_approved",
    ],
    ".beislid/probe-semantics.md": [
        "lifecycle_actions.break_spec_approved",
    ],
    ".beislid/doctor-templates.md": [
        "lifecycle_actions.break_spec_approved",
    ],
    "docs/workflows.md": [
        "break-spec",
        "approved structures can be written through lifecycle actions",
    ],
    "docs/skills.md": [
        "runs configured structure artifact actions after approval",
    ],
}


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    errors: list[str] = []

    for rel, needles in REQUIRED_REFERENCES.items():
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: missing required file")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel}: missing required break-spec artifact reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: break-spec artifact references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
