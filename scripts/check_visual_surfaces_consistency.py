#!/usr/bin/env python3
"""Guard visual_surfaces workflow config references from drifting.

The Visual surfaces workflow key is intentionally docs/instruction driven:
workflow grammar is the source of truth, doctor validates it, setup can write it,
probe semantics describe validation-only plugin-state behavior, and the protocol
file defines prompt-envelope semantics. This static check keeps those surfaces in
sync without invoking Lavish.
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
        ".beislid/visual-surface-protocol.md",
        "BEISLID_VISUAL_PROMPT_V1",
    ],
    ".beislid/visual-surface-protocol.md": [
        "BEISLID_VISUAL_PROMPT_V1",
        "BEISLID_VISUAL_FEEDBACK_V1",
        "Freeform annotations/messages",
        "Typed workflow-gate input",
        "Markdown/chat",
        "lavish-axi",
        "Spec review surface loop",
        "review_spec",
        "plan` and `comparison` playbook guidance",
        "approve_or_revise_spec",
        "missing `npx`",
        "failed deep checks",
        "npm/network/cache",
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
    "README.md": [
        "Optional Lavish visual surfaces",
        "beislid plugin enable lavish",
        "beislid plugin status lavish [--check]",
        "Markdown/chat artifacts remain canonical",
        "user plugin does not activate any workflow by itself",
        "pinned or local runtime",
    ],
    "docs/how-to-use.md": [
        "Optional Lavish visual surfaces",
        "Fresh-reader path",
        "beislid plugin enable lavish",
        "beislid plugin status lavish --check",
        "user-level plugin state alone does not activate routing",
        "missing `npx`",
        "failed deep checks",
        "Markdown/chat workflow gate",
    ],
    "docs/configuration.md": [
        "visual surfaces such as optional Lavish routing",
        "validation-only config such as action policy, model routing, and visual surfaces",
        "Visual surfaces",
        "beislid:visual_surfaces",
        "user-level plugin enablement alone is not enough",
        ".beislid/visual-surface-protocol.md",
        "BEISLID_VISUAL_PROMPT_V1",
        "Enable and inspect local Lavish state",
        "Troubleshooting and fallback behavior",
        "Missing or disabled user plugin state",
        "Absent repo config or `mode: off`",
        "Missing `npx`",
        "Failed deep check",
        "Declined prompt in `prompt` mode",
        "Runtime fallback after command/editor/poll failure",
        "Markdown/chat artifacts remain canonical",
    ],
    "skills/spec/SKILL.md": [
        "beislid:visual_surfaces",
        "visual-surface-protocol.md",
        "mirrors canonical `.beislid/visual-surface-protocol.md`",
        "BEISLID_VISUAL_PROMPT_V1",
        "freeform visual annotations",
        "typed workflow-gate response",
        "review_spec",
        "plan/comparison layout guidance",
        "explicit approval of the canonical Markdown/chat spec",
    ],
    "skills/spec/visual-surface-protocol.md": [
        "BEISLID_VISUAL_PROMPT_V1",
        "BEISLID_VISUAL_FEEDBACK_V1",
        "Freeform annotations/messages",
        "Typed workflow-gate input",
        "Spec review surface loop",
        "review_spec",
        "missing `npx`",
        "failed deep checks",
        "npm/network/cache",
    ],
    "docs/skills.md": [
        "Lavish visual surfaces",
        "beislid:visual_surfaces",
        "Markdown/chat artifacts remain canonical",
        "beislid plugin enable lavish",
        "missing `npx`",
        "failed deep checks",
    ],
    "docs/plans/2026-06-24-bei-2-spec-visual-feedback-loop-dry-run.md": [
        "Absent repo config",
        "`suggest`",
        "`prompt`",
        "`auto`",
        "Unavailable provider",
        "Declined provider path",
        "BEISLID_VISUAL_PROMPT_V1",
        "Markdown-primary approval check",
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

    canonical = root / ".beislid/visual-surface-protocol.md"
    spec_aux = root / "skills/spec/visual-surface-protocol.md"
    if canonical.exists() and spec_aux.exists():
        if canonical.read_text(encoding="utf-8") != spec_aux.read_text(encoding="utf-8"):
            errors.append("skills/spec/visual-surface-protocol.md: must mirror canonical .beislid/visual-surface-protocol.md")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: visual_surfaces references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
