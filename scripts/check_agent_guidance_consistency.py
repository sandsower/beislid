#!/usr/bin/env python3
"""Guard agent_guidance and skill_guidance references from drifting.

Guidance routing is docs/instruction driven in v1: workflow grammar is the
source of truth, setup configures pointers, doctor validates them, retro routes
learnings, and consuming skills load configured overlays. This static check keeps
those surfaces in sync.
"""

from __future__ import annotations

import pathlib
import sys


CONSUMING_SKILLS = {
    "babysit",
    "blueprint",
    "break-spec",
    "debug",
    "envelope",
    "fresh-eyes",
    "handoff",
    "implement",
    "kickoff",
    "poke-holes",
    "pr-patrol",
    "ready-for-review",
    "retro",
    "review",
    "review-response",
    "rinse",
    "show-me",
    "spec",
    "verify",
    "walk-the-diff",
}

NON_CONSUMING_SKILLS = {"setup", "doctor"}

REQUIRED_REFERENCES = {
    ".beislid/workflow-md-format.md": [
        "Agent guidance",
        "Skill guidance",
        "agent_guidance",
        "skill_guidance",
        "read-if-present",
        "must-read",
    ],
    ".beislid/probe-semantics.md": [
        "agent_guidance validation",
        "skill_guidance validation",
        "must-read",
        "read-if-present",
    ],
    "skills/setup/SKILL.md": [
        "**Agent guidance**",
        "beislid:agent_guidance",
        "**Skill guidance**",
        "beislid:skill_guidance",
        "must-read",
    ],
    "skills/doctor/SKILL.md": [
        "agent_guidance",
        "skill_guidance",
        "must-read",
        "read-if-present",
    ],
    "skills/retro/SKILL.md": [
        "agent_guidance",
        "skill_guidance",
        "host-native startup guidance",
        "Project guidance preflight",
    ],
    "docs/configuration.md": [
        "Agent and skill guidance",
        "beislid:agent_guidance",
        "beislid:skill_guidance",
        "must-read",
    ],
    "docs/skills.md": [
        "Project guidance overlays",
        "beislid:skill_guidance",
        "must-read",
    ],
}

PREFLIGHT_NEEDLES = [
    "## Project guidance preflight",
    "beislid:skill_guidance",
    "load `all`",
    "must-read",
    "report loaded/missing",
]


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
                errors.append(f"{rel}: missing required guidance reference `{needle}`")

    skill_dirs = {p.parent.name for p in (root / "skills").glob("*/SKILL.md")}
    expected = CONSUMING_SKILLS | NON_CONSUMING_SKILLS
    missing_known = expected - skill_dirs
    if missing_known:
        errors.append(f"skills: missing expected skill dirs {sorted(missing_known)}")

    unexpected = skill_dirs - expected
    if unexpected:
        errors.append(
            "skills: new skill dirs must be classified as consuming or non-consuming "
            f"for guidance preflight: {sorted(unexpected)}"
        )

    for skill in sorted(CONSUMING_SKILLS & skill_dirs):
        rel = f"skills/{skill}/SKILL.md"
        text = (root / rel).read_text(encoding="utf-8")
        for needle in PREFLIGHT_NEEDLES:
            if needle not in text:
                errors.append(f"{rel}: missing project guidance preflight reference `{needle}`")

    for skill in sorted(NON_CONSUMING_SKILLS & skill_dirs):
        rel = f"skills/{skill}/SKILL.md"
        text = (root / rel).read_text(encoding="utf-8")
        if "## Project guidance preflight" in text:
            errors.append(f"{rel}: setup/doctor configure or validate guidance; they must not consume overlays")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(
        "ok: agent_guidance/skill_guidance references consistent "
        f"({len(CONSUMING_SKILLS)} consuming skills)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
