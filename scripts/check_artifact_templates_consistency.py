#!/usr/bin/env python3
"""Guard lifecycle artifact template references from drifting.

The canonical artifact shapes live in .beislid/artifact-templates.md. This check
keeps the skills and user-facing docs that consume those shapes in sync without
running any workflow side effects.
"""

from __future__ import annotations

import pathlib
import sys


CANONICAL = ".beislid/artifact-templates.md"
AUX_SYMLINKS = [
    "skills/spec/artifact-templates.md",
    "skills/blueprint/artifact-templates.md",
    "skills/implement/artifact-templates.md",
    "skills/verify/artifact-templates.md",
    "skills/review/artifact-templates.md",
    "skills/fresh-eyes/artifact-templates.md",
    "skills/ready-for-review/artifact-templates.md",
    "skills/review-response/artifact-templates.md",
]

REQUIRED_REFERENCES = {
    CANONICAL: [
        "Lifecycle artifact templates v1",
        "Spec artifact",
        "Blueprint artifact",
        "Implementation plan artifact",
        "Verification report",
        "Review report",
        "Fresh-eyes report",
        "Ship summary",
        "Feedback response log",
        "Defaults: local vs posted",
        "Ticket/PR default",
        "local/chat",
        "Never include hidden chain-of-thought",
    ],
    "README.md": [
        "Lifecycle artifact templates are standardized",
        ".beislid/artifact-templates.md",
        "ticket/PR surfaces get concise summaries",
    ],
    "docs/how-to-use.md": [
        "Lifecycle artifact templates",
        "local/chat records are the default",
        "terse ticket/PR summaries",
    ],
    "docs/workflows.md": [
        "Lifecycle artifacts and reports",
        "spec, blueprint, implementation plan, verification report, review report, fresh-eyes report, ship summary, and feedback response log",
        "public ticket/PR surfaces get terse summaries",
    ],
    "docs/skills.md": [
        "Lifecycle artifact templates are standardized",
        "public ticket/PR summaries only when a workflow or orchestrator owns posting",
    ],
    "docs/skill-authoring.md": [
        "lifecycle artifact templates",
        "artifact-templates.md → ../../.beislid/artifact-templates.md",
    ],
    "skills/spec/SKILL.md": [
        "Spec artifact shape from `artifact-templates.md`",
    ],
    "skills/blueprint/SKILL.md": [
        "Blueprint artifact shape from `artifact-templates.md`",
    ],
    "skills/implement/SKILL.md": [
        "Implementation plan artifact shape from `artifact-templates.md`",
    ],
    "skills/verify/SKILL.md": [
        "Verification report shape from `artifact-templates.md`",
    ],
    "skills/review/SKILL.md": [
        "Review report shape from `artifact-templates.md`",
    ],
    "skills/fresh-eyes/SKILL.md": [
        "Fresh-eyes report shape from `artifact-templates.md`",
    ],
    "skills/ready-for-review/phase-4-submit.md": [
        "Ship summary shape from `artifact-templates.md`",
    ],
    "skills/review-response/phase-3-push.md": [
        "feedback response log using the `artifact-templates.md` shape",
    ],
}


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    errors: list[str] = []

    canonical_path = root / CANONICAL
    if not canonical_path.is_file():
        errors.append(f"{CANONICAL}: missing required file")
    else:
        canonical_text = canonical_path.read_text(encoding="utf-8")

    for rel in AUX_SYMLINKS:
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: missing artifact template symlink")
            continue
        if not path.is_symlink():
            errors.append(f"{rel}: must be a symlink to ../../.beislid/artifact-templates.md")
            continue
        if path.readlink().as_posix() != "../../.beislid/artifact-templates.md":
            errors.append(f"{rel}: unexpected symlink target {path.readlink()}")
            continue
        if canonical_path.exists() and path.read_text(encoding="utf-8") != canonical_text:
            errors.append(f"{rel}: symlink content does not match {CANONICAL}")

    for rel, needles in REQUIRED_REFERENCES.items():
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: missing required file")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel}: missing required artifact-template reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: lifecycle artifact template references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
