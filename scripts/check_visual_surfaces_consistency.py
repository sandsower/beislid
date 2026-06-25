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
        "artifact_retention",
        ".beislid/visual-surface-protocol.md",
        "BEISLID_VISUAL_PROMPT_V1",
        "BEISLID_VISUAL_FEEDBACK_V1",
        "beislid visual-feedback normalize",
        "manual_review",
        "Show Me deck routing",
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
        "manual_review",
        "beislid visual-feedback normalize",
        "scripts/visual_feedback.py",
        "canonical_update_required",
        "request_changes",
        "omitted_schema",
        "Canonical record audit requirements",
        "missing `npx`",
        "failed deep checks",
        "npm/network/cache",
        "Show Me deck routing",
        "inspect_show_me_deck",
        "required_for_decision: false",
        ".lavish/show-me/",
        "artifact_retention",
    ],
    ".beislid/probe-semantics.md": [
        "visual_surfaces validation",
        "provider",
        "artifact_root",
        "artifact_retention",
        "beislid plugin status lavish",
    ],
    "skills/doctor/SKILL.md": [
        "visual_surfaces",
        "provider/command/mode/artifact_root/artifact_retention/workflow",
        "Lavish plugin state",
    ],
    "skills/setup/SKILL.md": [
        "**Visual surfaces** — *Configure optional Lavish visual-surface routing",
        "beislid:visual_surfaces",
        "off / suggest / prompt / auto",
        "artifact_retention",
    ],
    "README.md": [
        "Optional Lavish visual surfaces",
        "beislid plugin enable lavish",
        "beislid plugin status lavish [--check]",
        "Markdown/chat artifacts remain canonical",
        "user plugin does not activate any workflow by itself",
        "pinned or local runtime",
        "BEISLID_VISUAL_FEEDBACK_V1",
        "freeform-only visual feedback",
        "Show Me deck routing",
        "artifact retention",
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
        "BEISLID_VISUAL_FEEDBACK_V1",
        "freeform-only feedback",
        "show-me",
        "artifact_retention",
        ".lavish/show-me/",
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
        "beislid visual-feedback normalize",
        "scripts/visual_feedback.py",
        "unknown action",
        "freeform-only feedback",
        "Show Me deck routing",
        "artifact_retention",
    ],
    "skills/spec/SKILL.md": [
        "beislid:visual_surfaces",
        "visual-surface-protocol.md",
        "mirrors canonical `.beislid/visual-surface-protocol.md`",
        "BEISLID_VISUAL_PROMPT_V1",
        "freeform visual annotations",
        "typed workflow-gate response",
        "review_spec",
        "manual_review",
        "canonical Markdown/chat spec",
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
        "manual_review",
        "beislid visual-feedback normalize",
        "scripts/visual_feedback.py",
        "Canonical record audit requirements",
        "missing `npx`",
        "failed deep checks",
        "npm/network/cache",
        "Show Me deck routing",
        "inspect_show_me_deck",
        "required_for_decision: false",
        ".lavish/show-me/",
        "artifact_retention",
    ],
    "docs/skills.md": [
        "Lavish visual surfaces",
        "beislid:visual_surfaces",
        "Show Me deck directories remain canonical",
        "beislid plugin enable lavish",
        "missing `npx`",
        "failed deep checks",
        "artifact_retention",
    ],
    "docs/show-me.md": [
        "Optional Lavish inspection",
        "beislid:visual_surfaces",
        "artifact_retention",
        ".lavish/show-me/",
        "portable deck",
        "missing `npx`",
        "freeform-only feedback",
    ],
    "skills/show-me/SKILL.md": [
        "Optional Lavish routing",
        "visual-surface-protocol.md",
        "Show Me deck routing",
        "artifact_retention",
        ".lavish/show-me/",
        "Freeform Lavish annotations",
    ],
    "skills/show-me/visual-surface-protocol.md": [
        "BEISLID_VISUAL_PROMPT_V1",
        "BEISLID_VISUAL_FEEDBACK_V1",
        "Show Me deck routing",
        "inspect_show_me_deck",
        "required_for_decision: false",
        "artifact_retention",
        ".lavish/show-me/",
        "npm/network/cache",
    ],
    ".gitignore": [
        ".lavish/",
        ".beislid/show-me/",
    ],
    "scripts/install_lib.sh": [
        ".lavish/",
        ".beislid/show-me/",
        "# BEGIN Beislið project install",
    ],
    "scripts/test_install.sh": [
        "Show Me deck routing",
        ".lavish/",
        ".beislid/show-me/",
    ],
    "bin/beislid": [
        "visual-feedback",
        "normalize",
        "scripts/visual_feedback.py",
    ],
    "scripts/visual_feedback.py": [
        "BEISLID_VISUAL_FEEDBACK_V1",
        "manual_review",
        "approve_or_revise_spec",
        "request_changes",
        "canonical_update_required",
        "legacy_schema_omitted",
        "KNOWN_ACTIONS",
    ],
    "scripts/test_visual_feedback.py": [
        "approve",
        "request_changes",
        "unknown action",
        "malformed payload",
        "freeform-only feedback",
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
    aux_copies = [
        root / "skills/spec/visual-surface-protocol.md",
        root / "skills/show-me/visual-surface-protocol.md",
    ]
    if canonical.exists():
        canonical_text = canonical.read_text(encoding="utf-8")
        for aux in aux_copies:
            if aux.exists() and canonical_text != aux.read_text(encoding="utf-8"):
                rel = aux.relative_to(root)
                errors.append(f"{rel}: must mirror canonical .beislid/visual-surface-protocol.md")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: visual_surfaces references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
