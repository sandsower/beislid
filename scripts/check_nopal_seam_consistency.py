#!/usr/bin/env python3
"""Guard the nopal seam protocol from drifting.

The canonical call contract lives in .beislid/nopal-seam-protocol.md. This
check keeps its per-skill symlinks, the required cross-references in the
docs/skills that delegate to it, and the "every documented nopal invocation
carries --json" grammar rule in sync without invoking the nopal binary.
"""

from __future__ import annotations

import pathlib
import re
import sys


CANONICAL = ".beislid/nopal-seam-protocol.md"
AUX_SYMLINKS = [
    "skills/kickoff/nopal-seam-protocol.md",
    "skills/envelope/nopal-seam-protocol.md",
    "skills/ready-for-review/nopal-seam-protocol.md",
    "skills/review-response/nopal-seam-protocol.md",
    "skills/implement/nopal-seam-protocol.md",
    "skills/babysit/nopal-seam-protocol.md",
    "skills/retro/nopal-seam-protocol.md",
    "skills/doctor/nopal-seam-protocol.md",
]

REQUIRED_REFERENCES = {
    CANONICAL: [
        "Probe: nopal_seam",
        "Call contract",
        "Token normalization",
        "supervised_auto",
        "workspace_write",
        "pre_pr",
        "Exit-code semantics",
        "status",
        "rondo",
        "run start",
        "Scratch-file convention",
        "Fallback ladder",
        "Out of scope",
    ],
    ".beislid/action-policy-protocol.md": [
        "nopal_seam",
        "nopal policy decide",
        "nopal-seam-protocol.md",
    ],
    ".beislid/probe-semantics.md": [
        "### binary",
        "nopal_seam validation and probe",
    ],
    ".beislid/workflow-md-format.md": [
        "Nopal seam",
        "nopal_seam",
        "nopal gates select",
    ],
    ".beislid/workflow.md": [
        "beislid:nopal_seam",
    ],
    "skills/doctor/SKILL.md": [
        "nopal_seam",
        "nopal import beislid-workflow",
    ],
    "docs/configuration.md": [
        "## Nopal seam",
        "beislid:nopal_seam",
        "nopal-seam-protocol.md",
    ],
    "skills/ready-for-review/phase-1-detect.md": [
        "nopal gates select",
    ],
    "skills/review-response/phase-3-push.md": [
        "nopal gates select",
    ],
    "skills/kickoff/SKILL.md": [
        "nopal ledger init",
    ],
    "skills/envelope/SKILL.md": [
        "nopal ledger init",
    ],
    "skills/ready-for-review/SKILL.md": [
        "nopal ledger init",
    ],
    "skills/ready-for-review/phase-4-submit.md": [
        "nopal ledger finalize",
    ],
    "skills/implement/SKILL.md": [
        "nopal ledger init",
    ],
}

# Files whose fenced ```bash blocks or inline `nopal ...` spans may contain
# literal nopal invocations that must always carry --json (TOON is the
# binary's default). Every file that references the seam is scanned, plus the
# doctor templates. Inline spans count as invocations only when they carry a
# `--` flag; flagless spans are prose family references. A flagless copyable
# example is still wrong by the protocol invariant, but only flagged forms
# are machine-checkable without a leaf-subcommand registry.
GRAMMAR_CHECKED_FILES = sorted(
    set(REQUIRED_REFERENCES) | {CANONICAL, ".beislid/doctor-templates.md"}
)

FENCE_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)
NOPAL_LINE_RE = re.compile(r"^nopal\s+\S")
INLINE_NOPAL_RE = re.compile(r"`(nopal [^`]+)`")
JSON_EXEMPT_TOKENS = ("--version", "--help")


def _logical_lines(block: str) -> list[str]:
    """Join backslash line-continuations into single logical command lines."""
    lines = block.splitlines()
    logical: list[str] = []
    buf = ""
    for line in lines:
        stripped = line.rstrip()
        if buf:
            buf += " " + stripped.strip()
        else:
            buf = stripped
        if buf.endswith("\\"):
            buf = buf[:-1].rstrip()
            continue
        logical.append(buf)
        buf = ""
    if buf:
        logical.append(buf)
    return logical


def _json_exempt(candidate: str) -> bool:
    tokens = candidate.split()
    if "help" in tokens:
        return True
    return any(exempt in tokens for exempt in JSON_EXEMPT_TOKENS)


def _check_grammar(root: pathlib.Path, rel: str, errors: list[str]) -> None:
    path = root / rel
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for block in FENCE_RE.findall(text):
        for line in _logical_lines(block):
            candidate = line.strip()
            if not candidate or not NOPAL_LINE_RE.match(candidate):
                continue
            if _json_exempt(candidate):
                continue
            if "--json" not in candidate:
                errors.append(
                    f"{rel}: nopal invocation missing --json: `{candidate}`"
                )
    for span in INLINE_NOPAL_RE.findall(text):
        candidate = span.strip()
        if "--" not in candidate or _json_exempt(candidate):
            continue
        if "--json" not in candidate:
            errors.append(
                f"{rel}: inline nopal invocation missing --json: `{candidate}`"
            )


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    errors: list[str] = []

    canonical_path = root / CANONICAL
    canonical_text = ""
    if not canonical_path.is_file():
        errors.append(f"{CANONICAL}: missing required file")
    else:
        canonical_text = canonical_path.read_text(encoding="utf-8")

    for rel in AUX_SYMLINKS:
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: missing nopal-seam-protocol symlink")
            continue
        if not path.is_symlink():
            errors.append(f"{rel}: must be a symlink to ../../.beislid/nopal-seam-protocol.md")
            continue
        if path.readlink().as_posix() != "../../.beislid/nopal-seam-protocol.md":
            errors.append(f"{rel}: unexpected symlink target {path.readlink()}")
            continue
        if canonical_text and path.read_text(encoding="utf-8") != canonical_text:
            errors.append(f"{rel}: symlink content does not match {CANONICAL}")

    for rel, needles in REQUIRED_REFERENCES.items():
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: missing required file")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel}: missing required nopal-seam reference `{needle}`")

    for rel in GRAMMAR_CHECKED_FILES:
        _check_grammar(root, rel, errors)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: nopal seam protocol references consistent ({len(REQUIRED_REFERENCES)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
