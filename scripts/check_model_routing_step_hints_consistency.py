#!/usr/bin/env python3
"""Guard Rondo step-aware model-routing hints from drifting.

This check is intentionally static: it validates the repo's checked-in Rondo
profile (`WORKFLOW.md`) and the docs/skill prose that describe it without
invoking any model-router runtime.
"""

from __future__ import annotations

import pathlib
import re
import sys

ALLOWED_TIERS = {"light", "standard", "heavy", "frontier"}

REQUIRED_REFERENCES = {
    "WORKFLOW.md": [
        "step_hints:",
        "initial:",
        "steps:",
        "phases:",
        "stage: kickoff",
        "skill: kickoff",
        "phase: context-discovery",
        "tier: frontier",
        "tier: heavy",
        "tier: standard",
        "tier: light",
        "stage: implement",
        "stage: ready-for-review",
        "phase: gates",
        "phase: review",
        "step: fresh-eyes",
    ],
    "docs/configuration.md": [
        "step_hints",
        "context-discovery",
        "fresh-eyes",
        "ready-for-review",
        "review-response",
        "defaults apply",
    ],
    ".beislid/probe-semantics.md": [
        "step_hints",
        "model_routing validation",
        "WORKFLOW.md",
    ],
    "skills/doctor/SKILL.md": [
        "step_hints",
        "WORKFLOW.md",
        "validation-only",
    ],
    "skills/setup/SKILL.md": [
        "step_hints",
        "WORKFLOW.md",
        "frontier",
        "fresh-eyes",
    ],
}


def load_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"{path}: unreadable ({exc})") from exc


def block(text: str, start: str, end: str | None = None) -> str:
    start_idx = text.find(start)
    if start_idx < 0:
        return ""
    remainder = text[start_idx:]
    if end is None:
        return remainder
    end_idx = remainder.find(end)
    if end_idx < 0:
        return remainder
    return remainder[:end_idx]


def validate_profile(text: str, errors: list[str]) -> None:
    routing = block(text, "model_routing:", "action_policy:")
    if not routing:
        errors.append("WORKFLOW.md: missing model_routing block")
        return

    if "defaults:" not in routing or "tier: standard" not in routing or "mode: prefer" not in routing:
        errors.append("WORKFLOW.md: defaults must keep the broad standard fallback route")

    if "step_hints:" not in routing:
        return

    hints = block(routing, "step_hints:", None)
    if not hints:
        errors.append("WORKFLOW.md: step_hints block is malformed")
        return

    required_snippets = [
        "initial:",
        "steps:",
        "phases:",
        "stage: kickoff",
        "skill: kickoff",
        "phase: context-discovery",
        "tier: frontier",
        "stage: implement",
        "tier: standard",
        "stage: ready-for-review",
        "phase: gates",
        "tier: light",
        "phase: review",
        "step: fresh-eyes",
        "tier: heavy",
    ]
    for snippet in required_snippets:
        if snippet not in hints:
            errors.append(f"WORKFLOW.md: step_hints is missing required hint `{snippet}`")

    # Quick structural guardrails: every explicit tier in the step-hints block must be known.
    for match in re.finditer(r"^\s*tier:\s*([A-Za-z0-9_.:-]+)\s*$", hints, flags=re.MULTILINE):
        tier = match.group(1)
        if tier not in ALLOWED_TIERS:
            errors.append(f"WORKFLOW.md: step_hints tier `{tier}` is not one of {sorted(ALLOWED_TIERS)}")

    # The kickoff initial hint must outrank the broad default.
    initial_block = block(hints, "initial:", "steps:")
    if initial_block and not any(tier in initial_block for tier in ("tier: frontier", "tier: heavy")):
        errors.append("WORKFLOW.md: initial step_hints route must use heavy or frontier")


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    profile = root / (argv[1] if len(argv) > 1 else "WORKFLOW.md")
    if not profile.is_file():
        print(f"error: profile not found: {profile}", file=sys.stderr)
        return 1

    text = load_text(profile)
    errors: list[str] = []

    validate_profile(text, errors)

    for rel, needles in REQUIRED_REFERENCES.items():
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: missing required file")
            continue
        contents = load_text(path)
        for needle in needles:
            if needle not in contents:
                errors.append(f"{rel}: missing required step-hints reference `{needle}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    if "step_hints:" in text:
        print(f"ok: step_hints validated in {profile}")
    else:
        print(f"ok: no step_hints in {profile}; broad defaults apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
