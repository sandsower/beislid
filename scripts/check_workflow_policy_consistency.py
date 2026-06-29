#!/usr/bin/env python3
"""Guard workflow policy level docs from drifting."""

from __future__ import annotations

import pathlib
import sys


REQUIRED_REFERENCES = {
    ".beislid/workflow-md-format.md": [
        "Workflow policy",
        "workflow_policy",
        "advisory",
        "regulated",
    ],
    ".beislid/workflow.md": [
        "```beislid:workflow_policy",
        "level: strict",
    ],
    ".beislid/probe-semantics.md": [
        "workflow_policy validation",
        "standard behavior",
    ],
    ".beislid/doctor-templates.md": [
        "workflow_policy",
        "level: strict",
    ],
    ".beislid/kickoff-templates.md": [
        "Policy: <advisory|standard|strict|regulated>",
        "workflow policy",
    ],
    ".beislid/ready-for-review-templates.md": [
        "policy: <advisory|standard|strict|regulated>",
        "workflow policy",
    ],
    "docs/configuration.md": [
        "Workflow policy levels",
        "workflow_policy",
        "advisory",
        "regulated",
    ],
    "docs/workflow-authoring.md": [
        "beislid:workflow_policy",
        "Workflow policy levels",
    ],
    "docs/setup-templates.md": [
        "workflow_policy",
        "strict review loop",
    ],
    "docs/team-rollout.md": [
        "Workflow policy levels",
        "workflow_policy",
    ],
    "docs/workflows.md": [
        "workflow policy level",
        "ready-for-review",
    ],
    "docs/skills.md": [
        "workflow policy level",
        "doctor",
    ],
    "docs/faq.md": [
        "workflow_policy",
        "policy levels",
    ],
    "skills/doctor/SKILL.md": [
        "workflow_policy",
        "probe_kind: validation",
    ],
    "skills/kickoff/SKILL.md": [
        "workflow_policy",
        "policy",
    ],
    "skills/verify/SKILL.md": [
        "workflow_policy",
        "evidence",
    ],
    "skills/ready-for-review/SKILL.md": [
        "workflow_policy",
        "policy",
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
                errors.append(f"{rel}: missing required workflow-policy reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: workflow policy level references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
