#!/usr/bin/env python3
"""Guard workflow_signals config references from drifting.

Workflow signals are intentionally small and docs/instruction driven in v1:
workflow grammar is the source of truth, doctor validates it, setup can write it,
and the CLI provides the best-effort local sink fan-out. This static check keeps
those surfaces in sync without requiring tmux or tmux-glance in CI.
"""

from __future__ import annotations

import pathlib
import sys


REQUIRED_REFERENCES = {
    ".beislid/workflow-md-format.md": [
        "Workflow signals",
        "workflow_signals",
        "tmux-glance",
        "working | waiting | verify | review | blocked | done | idle | clear",
    ],
    ".beislid/probe-semantics.md": [
        "workflow_signals validation",
        "sinks",
        "tmux-glance",
        "beislid workflow-signal status",
    ],
    "skills/doctor/SKILL.md": [
        "workflow_signals",
        "sinks",
        "tmux-glance",
    ],
    "skills/setup/SKILL.md": [
        "**Workflow signals** — *Configure optional local workflow-state signals",
        "beislid:workflow_signals",
        "tmux-glance",
    ],
    "docs/configuration.md": [
        "workflow signals such as optional tmux-glance tab markers",
        "Workflow signals",
        "beislid:workflow_signals",
        "beislid workflow-signal emit waiting",
    ],
    "skills/ready-for-review/SKILL.md": [
        "workflow-signal",
        "waiting",
        "verify",
    ],
    "skills/poke-holes/SKILL.md": [
        "workflow-signal",
        "waiting",
        "blocked",
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
                errors.append(f"{rel}: missing required workflow_signals reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: workflow_signals references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
