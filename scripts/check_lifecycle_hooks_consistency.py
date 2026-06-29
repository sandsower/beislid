#!/usr/bin/env python3
"""Guard lifecycle hook docs and skill references from drifting."""

from __future__ import annotations

import pathlib
import sys


REQUIRED_REFERENCES = {
    ".beislid/workflow-md-format.md": ["Lifecycle hooks", "lifecycle_hooks", "fresh_eyes", "ready_for_review", "review_response"],
    "docs/configuration.md": ["Lifecycle hooks", "beislid:lifecycle_hooks", "paths: ['docs/**', 'skills/**']"],
    "docs/workflow-authoring.md": ["Lifecycle hooks", "beislid:lifecycle_hooks", "branch_pattern"],
    "skills/lifecycle-hooks.md": ["Lifecycle hooks protocol v1", "beislid:lifecycle_hooks", "before and after"],
    "skills/setup/SKILL.md": ["lifecycle_hooks", "Configure custom phase-boundary hooks"],
    "skills/doctor/SKILL.md": ["lifecycle_hooks", "phase-boundary hook shape"],
    "skills/spec/SKILL.md": ["lifecycle-hooks.md"],
    "skills/blueprint/SKILL.md": ["lifecycle-hooks.md"],
    "skills/implement/SKILL.md": ["lifecycle-hooks.md"],
    "skills/verify/SKILL.md": ["lifecycle-hooks.md"],
    "skills/review/SKILL.md": ["lifecycle-hooks.md"],
    "skills/fresh-eyes/SKILL.md": ["lifecycle-hooks.md"],
    "skills/ready-for-review/SKILL.md": ["lifecycle-hooks.md"],
    "skills/review-response/SKILL.md": ["lifecycle-hooks.md"],
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
                errors.append(f"{rel}: missing required lifecycle-hooks reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: lifecycle-hooks references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
