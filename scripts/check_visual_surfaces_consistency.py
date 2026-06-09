#!/usr/bin/env python3
"""Guard visual_surfaces workflow config references from drifting.

The Visual surfaces workflow key is intentionally docs/instruction driven in Phase 1b:
workflow grammar is the source of truth, doctor validates it, setup can write it,
and probe semantics describe the validation-only plugin-state behavior. This
static check keeps those surfaces in sync without invoking Lavish.
"""

from __future__ import annotations

import pathlib
import sys


REQUIRED_REFERENCES = {
    ".beislid/workflow-md-format.md": [
        "Visual surfaces",
        "visual_surfaces",
        "lavish-axi",
        "off | suggest | prompt | auto",
    ],
    ".beislid/probe-semantics.md": [
        "visual_surfaces validation",
        "provider",
        "artifact_root",
        "beislid plugin status lavish",
    ],
    "skills/doctor/SKILL.md": [
        "visual_surfaces",
        "provider/mode/artifact_root/workflow",
        "Lavish plugin state",
    ],
    "skills/setup/SKILL.md": [
        "**Visual surfaces** — *Configure optional Lavish visual-surface routing",
        "beislid:visual_surfaces",
        "off / suggest / prompt / auto",
    ],
    "docs/configuration.md": [
        "visual surfaces such as optional Lavish routing",
        "validation-only config such as action policy, model routing, and visual surfaces",
        "Visual surfaces",
        "beislid:visual_surfaces",
        "user-level plugin enablement alone is not enough",
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
                errors.append(f"{rel}: missing required visual_surfaces reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: visual_surfaces references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
