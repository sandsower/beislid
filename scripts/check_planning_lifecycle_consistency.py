#!/usr/bin/env python3
"""Guard approved-planning lifecycle docs from drifting."""

from __future__ import annotations

import pathlib
import sys

REQUIRED_REFERENCES = {
    ".beislid/workflow-md-format.md": [
        "break_spec_approved",
        "spec_approved",
        "blueprint_approved",
        "P0 supports `type: artifact` and `type: cli`",
        "{artifact_path}",
        "lifecycle.<event>.<name>",
        "type: tracker",
    ],
    "docs/configuration.md": [
        "break_spec_approved",
        "spec_approved",
        "blueprint_approved",
        "type: artifact` to write local planning files",
        "type: cli` to run a configured side effect",
        "{artifact_path}",
        "lifecycle.<event>.<name>",
        "type: tracker",
    ],
    "skills/break-spec/SKILL.md": [
        "break_spec_approved",
        "plans/{feature}-structure.md",
        "Execute `type: artifact` and `type: cli`",
        "{artifact_path}",
        "lifecycle.break_spec_approved.<name>",
    ],
    "skills/spec/SKILL.md": [
        "spec_approved",
        "plans/{feature}-spec.md",
        "Execute `type: artifact`, `type: tracker`, and `type: cli`",
        "{artifact_path}",
        "lifecycle.spec_approved.<name>",
        "ticket.update",
    ],
    "skills/blueprint/SKILL.md": [
        "blueprint_approved",
        "plans/{feature}-design.md",
        "Execute `type: artifact` and `type: cli`",
        "{artifact_path}",
        "lifecycle.blueprint_approved.<name>",
    ],
    "skills/setup/sections/lifecycle-actions.md": [
        "break_spec_approved",
        "spec_approved",
        "blueprint_approved",
        "planning-event CLI side effects",
        "{artifact_path}",
    ],
    "skills/doctor/SKILL.md": [
        "break_spec_approved",
        "spec_approved",
        "blueprint_approved",
        "optional `classes[]`",
        "{artifact_path}",
    ],
    ".beislid/probe-semantics.md": [
        "lifecycle_actions.break_spec_approved",
        "lifecycle_actions.spec_approved",
        "lifecycle_actions.blueprint_approved",
        "Planning approval events",
        "{artifact_path}",
    ],
    ".beislid/doctor-templates.md": [
        "lifecycle_actions.break_spec_approved",
        "lifecycle_actions.spec_approved",
        "lifecycle_actions.blueprint_approved",
    ],
    "docs/workflows.md": [
        "approved-planning lifecycle actions after approval",
        "CLI actions run configured side effects",
    ],
    "docs/skills.md": [
        "spec lifecycle actions after approval",
        "structure lifecycle actions after approval",
        "design lifecycle actions after approval",
    ],
    "skills/kickoff/step-8-ticket-update.md": [
        "planning lifecycle results",
        "checkpoint artifact paths/status",
        "design lifecycle status/artifact path",
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
                errors.append(f"{rel}: missing required approved-planning lifecycle reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: approved-planning lifecycle references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
